from PIL import Image
import numpy as np
import argparse
import os


def main():
    parser = argparse.ArgumentParser(
        description="Make a datapack to put 3D object build from 2 image for Minecraft"
    )
    parser.add_argument(
        "img1", metavar="img1", type=str, help="the path of the 1st image"
    )
    parser.add_argument(
        "img2", metavar="img2", type=str, help="the path of the 2nd image"
    )
    parser.add_argument(
        "-v",
        "--version",
        type=int,
        default=7,
        help="the version of the datapack default is 7",
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default="minhya",
        help='the path of the datapack default is "minhya"',
    )
    parser.add_argument(
        "-n",
        "--namespace",
        type=str,
        default="minhya",
        help='the namespace of the datapack default is "minhya"',
    )
    parser.add_argument(
        "-b",
        "--block",
        type=str,
        default="minecraft:white_wool",
        help='the block in minecraft default is "minecraft:white_wool"',
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        default=180,
        help="the threshold of the image (0-255) default is 180",
    )
    parser.add_argument(
        "-c", "--cut", action="store_true", help="cut the internal dots"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="use batch to avoid command limit and support BE",
    )
    args = parser.parse_args()
    obj = make_obj(args.img1, args.img2, args.threshold, args.cut)
    make_datapack(
        obj,
        args.block,
        args.path,
        args.namespace,
        args.version,
        args.batch,
    )


def make_datapack(obj, block, path, namespace, version, batch):
    os.makedirs(f"{path}/data/{namespace}/functions", exist_ok=True)
    write_pack_mcmeta(path, version)
    write_functions(obj, path, namespace, block, batch)


def write_pack_mcmeta(path, version):
    with open(f"{path}/pack.mcmeta", "w") as f:
        f.write(
            f"""{{
  "pack": {{
    "pack_format": {version},
    "description": "3D object made from 2 images"
  }}
}}"""
        )


def write_functions(obj, path, namespace, block, batch):
    draw, undo = "draw", "undo"
    obj = np.array(obj)

    if batch:
        # batches, because there is a limit of commands per function
        batch_size = 10000
        batch_num = 1 + (len(obj) - 1) // batch_size
        batches = np.array_split(obj, batch_num)

        # write both the draw and undo sub-functions
        for i, batch in enumerate(batches):
            with open(
                f"{path}/data/{namespace}/functions/{draw}{i}.mcfunction", "w"
            ) as f1, open(
                f"{path}/data/{namespace}/functions/{undo}{i}.mcfunction", "w"
            ) as f2:
                for point in batch:
                    x, y, z = point[0], point[1], point[2]
                    block_command = f"setblock {x} {y} {z} {block}\n"
                    undo_command = f"setblock {x} {y} {z} minecraft:air\n"
                    f1.write(block_command)
                    f2.write(undo_command)

        # write the main function
        with open(
            f"{path}/data/{namespace}/functions/{draw}.mcfunction", "w"
        ) as f1, open(
            f"{path}/data/{namespace}/functions/{undo}.mcfunction", "w"
        ) as f2:
            f1.write(f"gamerule maxCommandChainLength 1000000\n")
            f2.write(f"gamerule maxCommandChainLength 1000000\n")
            for i in range(len(batches)):
                f1.write(f"function {namespace}:{draw}{i}\n")
                f2.write(f"function {namespace}:{undo}{i}\n")
    else:
        with open(
            f"{path}/data/{namespace}/functions/{draw}.mcfunction", "w"
        ) as f1, open(
            f"{path}/data/{namespace}/functions/{undo}.mcfunction", "w"
        ) as f2:
            f1.write(f"gamerule commandModificationBlockLimit 1000000\n")
            f2.write(f"gamerule commandModificationBlockLimit 1000000\n")
            for point in obj:
                x, y, z = point[0], point[1], point[2]
                block_command = f"setblock {x} {y} {z} {block}\n"
                undo_command = f"setblock {x} {y} {z} minecraft:air\n"
                f1.write(block_command)
                f2.write(undo_command)


def make_obj(img1, img2, threshold, cut):
    img1 = pre_resize(img1, threshold)
    img2 = pre_resize(img2, threshold)
    img1, img2 = auto_resize(img1, img2)
    if img1.height > 255:
        img1 = scale(img1)
        img2 = scale(img2)
    obj = build_unchecked(img1, img2)
    if cut:
        obj = cut(obj)
    return obj


def scale(img):
    f = 255 / img.height
    return img.resize((int(img.width * f), 255))


def pre_resize(pic, threshold):
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


def auto_resize(img1, img2):
    """
    this function will auto-resize img1 and img2 to the same height
    """
    # make sure img1's height is smaller than img2's height
    t = False
    if img1.height > img2.height:
        img1, img2 = img2, img1
        t = True

    # scale img2 to the same height as img1
    f = img1.height / img2.height  # <= 1
    img2 = img2.resize((int(img2.width * f), img1.height))

    if t:
        img1, img2 = img2, img1
    return img1, img2


def build_unchecked(img1, img2):
    assert img1.height == img2.height
    height = img1.height
    img_xz = np.array(img1)
    img_yz = np.array(img2)
    obj = []

    # iterate the z axis then x axis then y axis
    for iz, x_row in enumerate(img_xz):
        for ix, x in enumerate(x_row):
            # pure white, invisible, skip
            if x == 255:
                continue

            # black, visible
            for iy, y in enumerate(img_yz[iz]):
                if y != 255:
                    # z-axis in the image is facing down,
                    # so change the z-axis so that it is facing up
                    obj.append((ix, -iz + height, iy))
    return obj


def cut(obj):
    """
    remove internal dots and keep only the surface dots
    """
    new_obj = []

    # first, group by z
    grouped_by_z = {}
    for x, y, z in obj:
        grouped_by_z.setdefault(z, []).append((x, y))

    for z, points in grouped_by_z.items():
        max_x = max(points, key=lambda p: p[0])[0]
        max_y = max(points, key=lambda p: p[1])[1]
        # left + 1, right + 2, so it's + 3
        # it's for make sure x-1 > 0 and x+1 not out of range
        # so (x, y) = (x+1, y+1)
        mask = np.zeros((max_x + 3, max_y + 3), dtype=int)
        for x, y in points:
            mask[x + 1, y + 1] = 1
        for x, y in points:
            x, y = x + 1, y + 1
            p = [mask[x - 1, y], mask[x + 1, y], mask[x, y - 1], mask[x, y + 1]]
            # there is a blank around the point, so it's surface point
            if any(v == 0 for v in p):
                new_obj.append((x, y, z))
    return new_obj


if __name__ == "__main__":
    main()
