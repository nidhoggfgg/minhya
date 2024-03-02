from PIL import Image
import numpy as np

PIC_XZ = "" # put the 1st picture path here
PIC_YZ = "" # put the 2nd picture path here
THRESHOLD = 180 # set the threshold here, normally 180 is good
CUT = True # cut the internal dots or not
BLOCK = "minecraft:white_wool" # the block in minecraft


def main():
    pass


def make_datapack(obj, path, namespace, name, undo):
    obj = np.array(obj)
    obj[:, [1, 2]] = obj[:, [2, 1]] # y->z, z->y

    # batches, because there is a limit of commands per function
    batch_size = 10000
    batch_num = 1 + (len(obj) - 1) // batch_size
    batches = np.array_split(obj, batch_num)

    # write both the draw and undo functions
    for i, batch in enumerate(batches):
        with open(f"{path}/{name}{i}.mcfunction", "w") as f1, open(
            f"{path}/{undo}{i}.mcfunction", "w"
        ) as f2:
            for point in batch:
                x, y, z = point[0], point[1], point[2]
                block_command = f"setblock {x} {y} {z} {BLOCK}\n"
                undo_command = f"setblock {x} {y} {z} minecraft:air\n"
                f1.write(block_command)
                f2.write(undo_command)
    
    # write the main function
    with open(f"{path}/{name}.mcfunction", "w") as f1, open(
        f"{path}/{undo}.mcfunction", "w"
    ) as f2:
        for i in range(len(batches)):
            f1.write(f"function {namespace}:{name}{i}\n")
            f2.write(f"function {namespace}:{undo}{i}\n")
     

# this function isn't used, we use obj[:, [1, 2]] = obj[:, [2, 1]] instead
# but if you really want to rotate rather than change the axis, use this
def rotate_90(point):
    theta = np.pi / 2
    rotation_matrix = np.array(
        [
            [1, 0, 0],
            [0, np.cos(theta), -np.sin(theta)],
            [0, np.sin(theta), np.cos(theta)],
        ]
    )

    rotated_point = np.dot(rotation_matrix, point)
    return rotated_point


def scale(img, f):
    return img.resize((int(img.width * f), int(img.height * f)))


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
    """
    make the object
    return [(x, y, z), ...]
    """
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
                    obj.append((ix, iy, -iz + height))
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

