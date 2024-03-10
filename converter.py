from PIL import Image
import numpy as np
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="cut the blank part of the image and convert to black and white"
    )
    parser.add_argument(
        "input", metavar="input", type=str, help="the path of the image"
    )
    parser.add_argument(
        "output",
        metavar="output",
        type=str,
        help="the path of the output image",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        default=180,
        help="the threshold of the image",
    )
    args = parser.parse_args()
    img = convert(args.input, args.threshold)
    img.save(args.output)

def convert(pic, threshold):
    img = Image.open(pic)

    # convert to gray img and arrays for easy processing
    gray_img = img.convert("L")
    img_array = np.array(gray_img)

    if 0 <= threshold <= 255 if threshold is not None else False:
        img_array[img_array > threshold] = 255
        img_array[img_array <= threshold] = 0

    # delete the blank part
    delete1 = np.all(img_array == 255, axis=1)
    delete2 = np.all(img_array == 255, axis=0)
    img_array = img_array[~delete1]
    img_array = img_array[:, ~delete2]
    output = Image.fromarray(img_array.astype(np.uint8))
    return output

if __name__ == "__main__":
    main()