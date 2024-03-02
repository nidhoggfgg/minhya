from PIL import Image
import numpy as np
import bpy
import bmesh
from mathutils import Vector

PIC_XZ = "pictures/bird.png"
PIC_YZ = "pictures/pig.jpg"
THRESHOLD = 180
CUT = True


def main():
    img1 = pre_resize(PIC_XZ, THRESHOLD)
    img2 = pre_resize(PIC_YZ, THRESHOLD)
    img1, img2 = auto_resize(img1, img2)
    obj = build_unchecked(img1, img2)
    if CUT:
        obj = cut(obj)
    create_dots(obj)


def create_dots(cube):
    mesh = bpy.data.meshes.new(name="PointMesh")
    obj = bpy.data.objects.new("PointObject", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.primitive_cube_add(size=0.02, location=(0, 0, 0))
    bpy.ops.object.mode_set(mode="OBJECT")
    bm = bmesh.new()
    for xyz in cube:
        bm.verts.new(Vector(xyz))

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


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
