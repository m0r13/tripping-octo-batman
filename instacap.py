#!/usr/bin/env python3

import os
import sys
import math
import numpy
import colorsys
import random
import PIL.Image, PIL.ImageStat

from matplotlib import pyplot

def color_distance(color1, color2):
    return sum([ (color1[i] - color2[i])**2 for i in range(3) ])

def color_difference(color1, color2):
    return tuple([ color1[i] - color2[i] for i in range(3) ])

def color_quant_error(color, quant_error, quant_factor):
    r, g, b = color
    r += quant_error[0] * quant_factor
    g += quant_error[1] * quant_factor
    b += quant_error[2] * quant_factor
    return (int(r), int(g), int(b))

class Cap:
    def __init__(self, image, size):
        super(Cap, self).__init__()

        self.image = image.resize(size)
        self.orig_image = image
        self.color = self._calc_color(self.image)
        self.size = size

    def _calc_color(self, image):
        r, g, b = 0, 0, 0
        if False:
            stats = PIL.ImageStat.Stat(image)
            r = int(stats.sum[0] / stats.count[0]) 
            g = int(stats.sum[1] / stats.count[1])
            b = int(stats.sum[2] / stats.count[2])
        else:
            cx, cy = image.size[0] / 2, image.size[1] / 2
            radius = image.size[0] / 2

            count = 0
            for x in range(image.size[0]):
                for y in range(image.size[1]):
                    if (cx - x)**2 + (cy - y)**2 <= radius**2:
                        pixel = image.getpixel((x, y))
                        r += pixel[0]
                        g += pixel[1]
                        b += pixel[2]
                        count += 1
            r //= count
            g //= count
            b //= count
        return (r, g, b)

class CapPalette:
    def __init__(self, directory=None, prob=1, image_size=None):
        super(CapPalette, self).__init__()

        self._image_size = image_size
        self._caps = []
        if directory is not None:
            self._caps = self._scan_files(directory, prob, image_size)

    def _scan_files(self, directory, prob, size):
        caps = []
        for filename in os.listdir(directory):
            path = os.path.join(sys.argv[1], filename)
            if not path.endswith((".jpg", ".jpeg", ".png")):
                continue
            
            im = None
            try:
                im = PIL.Image.open(path)
            except OSError as e:
                print(e)
                continue

            if random.random() > prob:
                continue

            caps.append(Cap(im, size))
        return caps

    def optimize(self, threshold=3.0):
        palette = CapPalette()
        palette._image_size = self._image_size

        for i in range(len(self._caps)):
            cap = self._caps[i]
            index, color = self.find_color(cap.color, [i])
            distance = math.sqrt(color_distance(cap.color, color))
            if index == -1 or distance > threshold:
                palette.caps.append(cap)

        return palette

    def find_color(self, color, except_index=[]):
        best_distance = 255*255*255
        best_cap = -1
        best_color = (0, 0, 0)
        for index, cap in enumerate(self._caps):
            dist = color_distance(color, cap.color)
            if (dist < best_distance and not index in except_index):
                #print("found: %d %d" % (index, dist))
                best_distance = dist
                best_cap = index
                best_color = cap.color
        #print("best: %d %s" % (best_cap, best_color))
        return best_cap, best_color
    
    def create_palette_image(self):
        size = math.ceil(math.sqrt(len(self._caps)))
        image = PIL.Image.new("RGB", (size, size))
        caps = list(self._caps)
        caps.sort(key = lambda cap: colorsys.rgb_to_hsv(*map(lambda c: c / 255, cap.color))[0])
        for i in range(len(caps)):
            color = caps[i].color
            image.putpixel((i % size, i // size), color)
        return image
    
    @property
    def image_size(self):
        return self._image_size

    @property
    def caps(self):
        return self._caps

def floyd_steinberg(image, palette):
    width, height = image.size
    data = [0] * (width * height)
    for x in range(width):
        print(x)
        for y in range(height):
            old = image.getpixel((x, y))
            new_index, new = palette.find_color(old)
            image.putpixel((x, y), new)
            data[y * width + x] = new_index
            quant_error = color_difference(old, new)

            if x < width - 1:
                image.putpixel((x+1, y), color_quant_error(image.getpixel((x+1, y)), quant_error, 7/16))
            if x > 0 and y < height - 1:
                image.putpixel((x-1, y+1), color_quant_error(image.getpixel((x-1, y+1)), quant_error, 3/16))
            if y < height - 1:
                image.putpixel((x, y+1), color_quant_error(image.getpixel((x, y+1)), quant_error, 5/16))
            if x < width - 1 and y < height - 1:
                image.putpixel((x+1, y+1), color_quant_error(image.getpixel((x+1, y+1)), quant_error, 1/16))
    return data

def create_cap_image(size, data, palette):
    caps_w, caps_h = palette.image_size
    caps_x, caps_y = size
    image = PIL.Image.new("RGB", (caps_x * caps_w, caps_y * caps_h))
    for x in range(caps_x):
        for y in range(caps_y):
            index = data[y * caps_x + x]
            cap = palette.caps[index].image
            image.paste(cap, (x * caps_w, y * caps_h))
    return image

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: {} directory".format(sys.argv[0]))
        sys.exit(1)

    prob = 1
    cap_dimensions = (30, 30)
    input_dimensions = (30*2, 40*2)

    print("Loading caps...")
    palette = CapPalette(sys.argv[1], prob, cap_dimensions)
    print("Loaded %d caps." % len(palette.caps))
    optimized = palette.optimize(5.0)
    print("Optimized: %d" % len(optimized.caps))
    palette.create_palette_image().save("palette1.png")
    optimized.create_palette_image().save("palette2.png")
    palette = optimized

    caps = palette.caps
    size = math.ceil(math.sqrt(len(caps)))
    image = PIL.Image.new("RGB", (size, size))
    for i in range(len(caps)):
        color = caps[i].color
        image.putpixel((i % size, i // size), color)
    image.save("palette.png")

    minion = PIL.Image.open("input2.jpg").resize(input_dimensions)
    width, height = minion.size
    quantized = PIL.Image.new("RGB", (width, height))

    data = floyd_steinberg(minion, palette)
    for x in range(width):
        for y in range(height):
            index = data[y * width + x]
            quantized.putpixel((x, y), palette.caps[index].color)
    quantized.save("test1.jpg")
    create_cap_image(input_dimensions, data, palette).save("test2.jpg")
   
