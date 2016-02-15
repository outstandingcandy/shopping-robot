import cv2
import numpy
import os

def scale_image(img, target_width = 270):
    height, width = img.shape[:2]
    if width >= height:
        max_dim = width
    else:
        max_dim = height
    scale = float(target_width) / max_dim
    if width >= height:
        width = target_width
        x = 0
        height = int(height * scale)
        y = (target_width - height) / 2;
    else:
        y = 0
        height = target_width
        width = int(width * scale)
        x = (target_width - width) / 2
    res = cv2.resize(img, dsize=(width, height))
    return res

def fill_square_image(img, target_width = 270):
    height, width = img.shape[:2]
    if width >= height:
        x = 0
        y = (target_width - height) / 2;
    else:
        x = (target_width - width) / 2
        y = 0
    square_img = numpy.zeros((target_width, target_width, 3), numpy.uint8)
    square_img.fill(255)
    for i in range(height):
        for j in range(width):
            square_img[i + y][j + x] = img[i][j]
    return square_img

def process(input_image_path, output_image_path):
    target_width = 270
    img = cv2.imread(input_image_path)
    scaled_img = scale_image(img, target_width)
    square_img = fill_square_image(scaled_img, target_width)
    cv2.imwrite(output_image_path, square_img)

if __name__ == '__main__':
    raw_img_dir = "/root/mmh/image/full/"
    square_img_dir = "/root/mmh/bbzdm_web/static/img/square/"
    for img_file_name in os.listdir(raw_img_dir):
        img_path = raw_img_dir + img_file_name
        square_img_path = square_img_dir + img_file_name
        process(img_path, square_img_path)
