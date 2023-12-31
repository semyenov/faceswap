from ctypes import ArgumentError
import logging
import os
import sys
import time
import cv2
import dlib
import numpy
import argparse
import concurrent.futures

PREDICTOR_PATH = os.path.join(
    os.path.dirname(__file__), "shape_predictor_68_face_landmarks.dat"
)

SCALE_FACTOR = 1
FEATHER_AMOUNT = 15

FACE_POINTS = list(range(17, 68))
MOUTH_POINTS = list(range(48, 61))
RIGHT_BROW_POINTS = list(range(17, 22))
LEFT_BROW_POINTS = list(range(22, 27))
RIGHT_EYE_POINTS = list(range(36, 42))
LEFT_EYE_POINTS = list(range(42, 48))
NOSE_POINTS = list(range(27, 35))
JAW_POINTS = list(range(0, 17))

# Points used to line up the images.
ALIGN_POINTS = (
    LEFT_BROW_POINTS
    + RIGHT_EYE_POINTS
    + LEFT_EYE_POINTS
    + RIGHT_BROW_POINTS
    + NOSE_POINTS
    + MOUTH_POINTS
)

# Points from the second image to overlay on the first. The convex hull of each
# element will be overlaid.
OVERLAY_POINTS = [
    LEFT_EYE_POINTS + RIGHT_EYE_POINTS + LEFT_BROW_POINTS + RIGHT_BROW_POINTS,
    NOSE_POINTS + MOUTH_POINTS,
]

# Amount of blur to use during colour correction, as a fraction of the
# pupillary distance.
COLOUR_CORRECT_BLUR_FRAC = 0.8

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(PREDICTOR_PATH)


class TooManyFaces(Exception):
    pass


class NoFaces(Exception):
    pass


def get_landmarks(im):
    """
    Detects and returns the landmarks of a face in an image.

    Args:
        im: A numpy array representing the input image.

    Raises:
        TooManyFaces: If more than one face is detected in the image.
        NoFaces: If no faces are detected in the image.

    Returns:
        A numpy matrix representing the coordinates of the facial landmarks.
    """
    rects = detector(im, 1)

    if len(rects) == 0:
        raise NoFaces

    # take just the first face
    return numpy.matrix([[p.x, p.y] for p in predictor(im, rects[0]).parts()])


def annotate_landmarks(im, landmarks):
    """
    Annotate landmarks on an image.

    Parameters:
        - im: The input image to annotate.
        - landmarks: A list of landmarks.

    Returns:
        - The annotated image.
    """
    im = im.copy()
    for idx, point in enumerate(landmarks):
        pos = (point[0, 0], point[0, 1])
        cv2.putText(
            im,
            str(idx),
            pos,
            fontFace=cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
            fontScale=0.4,
            color=(0, 0, 255),
        )
        cv2.circle(im, pos, 3, color=(0, 255, 255))
    return im


def draw_convex_hull(im, points, color):
    """
    Draws the convex hull of a set of points on an image.

    Args:
        im (Image): The image on which to draw the convex hull.
        points (List[List[int]]): The points to calculate the convex hull from.
        color (Tuple[int, int, int]): The color to fill the convex hull with.

    Returns:
        None
    """
    points = cv2.convexHull(points)
    cv2.fillConvexPoly(im, points, color=color)


def get_face_mask(im, landmarks):
    """
    Generate a face mask based on the input image and facial landmarks.

    Parameters:
    - im: An array representing the input image.
    - landmarks: A dictionary containing the facial landmarks.

    Returns:
    - im: An array representing the generated face mask.
    """
    im = numpy.zeros(im.shape[:2], dtype=numpy.float64)

    for group in OVERLAY_POINTS:
        draw_convex_hull(im, landmarks[group], color=1)

    im = numpy.array([im, im, im]).transpose((1, 2, 0))

    im = (cv2.GaussianBlur(im, (FEATHER_AMOUNT, FEATHER_AMOUNT), 0) > 0) * 1.0
    im = cv2.GaussianBlur(im, (FEATHER_AMOUNT, FEATHER_AMOUNT), 0)

    return im


def transformation_from_points(points1, points2):
    """
    Calculate the transformation matrix from two sets of points.

    Args:
        points1 (ndarray): The first set of points.
        points2 (ndarray): The second set of points.

    Returns:
        ndarray: The transformation matrix.
    """
    points1 = points1.astype(numpy.float64)
    points2 = points2.astype(numpy.float64)

    c1 = numpy.mean(points1, axis=0)
    c2 = numpy.mean(points2, axis=0)
    points1 -= c1
    points2 -= c2

    s1 = numpy.std(points1)
    s2 = numpy.std(points2)
    points1 /= s1
    points2 /= s2

    U, _, Vt = numpy.linalg.svd(points1.T * points2)

    R = (U * Vt).T

    return numpy.vstack(
        [
            numpy.hstack(((s2 / s1) * R, c2.T - (s2 / s1) * R * c1.T)),
            numpy.matrix([0.0, 0.0, 1.0]),
        ]
    )


def read_im_and_landmarks(fname):
    """
    Reads an image from a file and extracts facial landmarks.

    Parameters:
        fname (str): The path to the image file.

    Returns:
        tuple: A tuple containing the resized image and the facial landmarks.
    """
    im = cv2.imread(fname, cv2.IMREAD_COLOR)
    im = cv2.resize(im, (im.shape[1] * SCALE_FACTOR, im.shape[0] * SCALE_FACTOR))
    s = get_landmarks(im)

    return im, s


def warp_im(im, M, dshape):
    """
    Applies an affine transformation to the input image.

    Parameters:
        im (ndarray): The input image.
        M (ndarray): The 2x3 transformation matrix.
        dshape (tuple): The shape of the output image.

    Returns:
        ndarray: The transformed output image.
    """
    output_im = numpy.zeros(dshape, dtype=im.dtype)
    cv2.warpAffine(
        im,
        M[:2],
        (dshape[1], dshape[0]),
        dst=output_im,
        borderMode=cv2.BORDER_TRANSPARENT,
        flags=cv2.WARP_INVERSE_MAP,
    )
    return output_im


def correct_colours(im1, im2, landmarks1):
    """
    Corrects the colors of two images using landmarks.

    Args:
        im1 (numpy.ndarray): The first image.
        im2 (numpy.ndarray): The second image.
        landmarks1 (numpy.ndarray): The landmarks of the first image.

    Returns:
        numpy.ndarray: The color-corrected image.

    """
    blur_amount = COLOUR_CORRECT_BLUR_FRAC * numpy.linalg.norm(
        numpy.mean(landmarks1[LEFT_EYE_POINTS], axis=0)
        - numpy.mean(landmarks1[RIGHT_EYE_POINTS], axis=0)
    )
    blur_amount = int(blur_amount)
    if blur_amount % 2 == 0:
        blur_amount += 1
    im1_blur = cv2.GaussianBlur(im1, (blur_amount, blur_amount), 0)
    im2_blur = cv2.GaussianBlur(im2, (blur_amount, blur_amount), 0)

    # Avoid divide-by-zero errors.
    im2_blur += (128 * (im2_blur <= 1.0)).astype(im2_blur.dtype)

    return (
        im2.astype(numpy.float64)
        * im1_blur.astype(numpy.float64)
        / im2_blur.astype(numpy.float64)
    )


def swap(
    source_im, source_landmarks, source_mask, input_file, output_file, debug=False
):
    """
    This function swaps the face in the input image with the face in the source image.

    Parameters:
        source_im (numpy.ndarray): The source image containing the face to be swapped.
        source_landmarks (numpy.ndarray): The landmarks of the face in the source image.
        source_mask (numpy.ndarray): The mask of the face in the source image.
        input_file (str): The path to the input image file.
        output_file (str): The path to save the output image.
        debug (bool, optional): If True, the function will output annotated landmarks on the image.
            Defaults to False.

    Returns:
        None
    """
    start_time = time.time()
    
    try:
        input_im, input_landmarks = read_im_and_landmarks(input_file)
    except NoFaces:
        logger.error("\nNo faces detected: input file is invalid")
        return

    M = transformation_from_points(
        input_landmarks[ALIGN_POINTS], source_landmarks[ALIGN_POINTS]
    )

    warped_mask = warp_im(source_mask, M, input_im.shape)
    combined_mask = numpy.max(
        [get_face_mask(input_im, input_landmarks), warped_mask], axis=0
    )

    warped_im2 = warp_im(source_im, M, input_im.shape)
    warped_corrected_im2 = correct_colours(input_im, warped_im2, input_landmarks)

    if debug:
        output_im = annotate_landmarks(
            input_im * (1.0 - combined_mask) + warped_corrected_im2 * combined_mask,
            input_landmarks,
        )
    else:
        output_im = (
            input_im * (1.0 - combined_mask) + warped_corrected_im2 * combined_mask
        )

    cv2.imwrite(output_file, output_im)

    end_time = time.time()
    logger.info(f"Input File: {input_file}")
    logger.info(f"Output File: {output_file}")
    logger.info(f"Processing time: {end_time - start_time} seconds\n")

    return


def main():
    """
    Parse command line arguments, read source image and landmarks, get face mask, and process images in parallel using a thread pool executor.

    :param None
    :return None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("source_file", help="Path to source image")
    parser.add_argument("input_dir", help="Input directory")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
        default=False,
    )
    args = parser.parse_args()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        try:
            source_im, source_landmarks = read_im_and_landmarks(
                os.path.abspath(args.source_file)
            )
            source_mask = get_face_mask(source_im, source_landmarks)

            list(executor.map(
                lambda input_im: swap(
                    source_im,
                    source_landmarks,
                    source_mask,
                    input_file=os.path.abspath(os.path.join(args.input_dir, input_im)),
                    output_file=os.path.abspath(
                        os.path.join(args.output_dir, os.path.basename(input_im))
                    ),
                    debug=args.debug,
                ),
                os.listdir(args.input_dir),
            ))

        except NoFaces:
            logger.error("\nNo faces detected: source file is invalid")
            return
        
        except ArgumentError:
            if args.debug:
                logger.error("\nUnexpected error:", sys.exc_info()[0])
            else:
                logger.error("\nUnexpected error: source file is invalid")
            return

if __name__ == "__main__":
    main()
