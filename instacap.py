#!/usr/bin/env python3

import os
import sys
import math
import numpy
import colorsys
import random
import argparse
import PIL.Image, PIL.ImageStat

from matplotlib import pyplot

def color_distance2(color1, color2):
    return sum([ (color1[i] - color2[i])**2 for i in range(3) ])
color_distance = color_distance2

def color_difference(color1, color2):
    return tuple([ color1[i] - color2[i] for i in range(3) ])

def color_quant_error(color, quant_error, quant_factor):
    r, g, b = color
    r += quant_error[0] * quant_factor
    g += quant_error[1] * quant_factor
    b += quant_error[2] * quant_factor
    return (int(r), int(g), int(b))

class ColorSubpalette:
    def __init__(self, position, palette_colors):
        super(ColorSubpalette, self).__init__()

        self.position = position
        self.initialized = False
        self.palette_colors = palette_colors
        self.colors = []
    
    def set_colors(self, palette_colors):
        self.initialized = False
        self.palette_colors = self.palette_colors
        self.colors = []

    def initialize(self):
        self.initialized = True

        center = (
            (self.position[0] * 256 + 128) // ColorPalette.BINS,
            (self.position[1] * 256 + 128) // ColorPalette.BINS,
            (self.position[2] * 256 + 128) // ColorPalette.BINS,
        )

        nearest = 256 * 256 * 4
        for index, color in self.palette_colors:
            distance = color_distance2(color, center)
            nearest = min(nearest, distance)
            if nearest == 0:
                break

        nearest_dist = (math.sqrt(nearest) + 2 * math.sqrt(2) * (128 / ColorPalette.BINS)) ** 2 + 1
        for index, color in self.palette_colors:
            if color_distance2(color, center) <= nearest_dist:
                self.colors.append((index, color))

        #print("Initialize subpalette %s: %d/%d colors" % (self.position, len(self.colors), len(self.palette_colors)))

    def find_color(self, color, except_color=-1):
        if not self.initialized:
            self.initialize()
        
        nearest_index = -1
        nearest_dist = 256 * 256 * 4
        for index, other_color in self.colors:
            dist = color_distance2(color, other_color)
            if dist < nearest_dist and index != except_color:
                nearest_index = index
                nearest_dist = dist
                if nearest_dist == 0:
                    return nearest_index
        return nearest_index

class ColorPalette:
    
    SPLITS = 3
    BINS = 1 << SPLITS
    BIN_FOR_COLOR = lambda c, splits=SPLITS: c >> (8 - splits)

    def __init__(self):
        super(ColorPalette, self).__init__()

        self._subpalettes = [None] * ColorPalette.BINS**3
        self._colors = []

        for r in range(ColorPalette.BINS):
            for g in range(ColorPalette.BINS):
                for b in range(ColorPalette.BINS):
                    self._subpalettes[r + g * ColorPalette.BINS + b * ColorPalette.BINS**2] = ColorSubpalette((r, g, b), self._colors)

    def _subpalette(self, color):
        r = ColorPalette.BIN_FOR_COLOR(color[0])
        g = ColorPalette.BIN_FOR_COLOR(color[1])
        b = ColorPalette.BIN_FOR_COLOR(color[2])
        return self._subpalettes[r + g * ColorPalette.BINS + b * ColorPalette.BINS**2]

    def add_color(self, index, color):
        self._colors.append((index, color))
        self._subpalette(color).set_colors(self._colors)

    def clear_colors(self):
        self._colors = []
        for subpalette in self._subpalettes:
            subpalette.set_colors(self._colors)

    def find_color(self, color, except_color=-1):
        return self._subpalette(color).find_color(color, except_color)

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
    def __init__(self, cap_size):
        super(CapPalette, self).__init__()

        self._cap_size = cap_size
        self._caps = []
        self._palette = ColorPalette()

    def add_cap(self, cap):
        self._caps.append(cap)
        self._palette.add_color(len(self._caps) - 1, cap.color)

    def add_file(self, filename):
        im = None
        try:
            im = PIL.Image.open(filename)
        except OSError as e:
            print(e)
            return
        self.add_cap(Cap(im, self._cap_size))

    def add_directory(self, directory, prob=1):
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            if not path.endswith((".jpg", ".jpeg", ".png")):
                continue
            if random.random() <= prob:
                self.add_file(path)
 
    def find_color(self, color, except_index=-1):
        index = self._palette.find_color(color, except_index)
        return index, self._caps[index].color

        #best_distance = 255*255*255
        #best_cap = -1
        #best_color = (0, 0, 0)
        #for index, cap in enumerate(self._caps):
        #    dist = color_distance(color, cap.color)
        #    if (dist < best_distance and not index in except_index):
        #        best_distance = dist
        #        best_cap = index
        #        best_color = cap.color
        #return best_cap, best_color
    
    def optimize(self, threshold):
        palette = CapPalette(self._cap_size)

        for i in range(len(self._caps)):
            cap = self._caps[i]
            index, color = self.find_color(cap.color, i)
            distance = math.sqrt(color_distance(cap.color, color))
            if index == -1 or distance > threshold:
                palette.add_cap(cap)

        return palette

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
    def cap_size(self):
        return self._cap_size

    @property
    def caps(self):
        return self._caps

def floyd_steinberg(image, palette, verbose=False):
    width, height = image.size
    data = [0] * (width * height)
    for y in range(height):
        if verbose:
            print("Row %d of %d processed." % (y+1, height))
        for x in range(width):
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
    caps_w, caps_h = palette.cap_size
    caps_x, caps_y = size
    image = PIL.Image.new("RGB", (caps_x * caps_w, caps_y * caps_h))
    for x in range(caps_x):
        for y in range(caps_y):
            index = data[y * caps_x + x]
            cap = palette.caps[index].image
            image.paste(cap, (x * caps_w, y * caps_h))
    return image

def size_tuple(string):
    try:
        x, y = map(int, string.split(","))
        return x, y
    except:
        raise argparse.ArgumentTypeError("Size tuple must be 'x,y'!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cheers!")
    parser.add_argument("--verbose", "-v", metavar="", action="store_const", const=True, default=False,
            help="displays additional progress information")
    parser.add_argument("--palette-probability", "-p", metavar="prob".upper(), type=float, default=1.0,
            help="don't use every picture of the caps directory: use pictures only with a specific probability (from 0.0 to 1.0)")
    parser.add_argument("--palette-optimize", "-o", metavar="num_colors".upper(), type=int,
            help="optimize the calculated color palette to use a maximum of NUM_COLORS colors (= caps)")
    parser.add_argument("--cap-size", "-s", metavar="size".upper(), type=size_tuple, default=(30, 30),
            help="size of the cap images to use the output image, must be in the format 'width,height', default is '30,30'")
    parser.add_argument("--width", type=int,
            help="width of the output image (in caps, not pixels), you have to specify at least one of with and height")
    parser.add_argument("--height", type=int,
            help="height of the output image (in caps, not pixels), you have to specify at least one of width and height")
    parser.add_argument("caps",
            help="directory with the images of available caps")
    parser.add_argument("input",
            help="filename of the input image to be processed")
    parser.add_argument("output",
            help="filename of the generated cap mosaic image")
    args = vars(parser.parse_args())

    output_width = args["width"]
    output_height = args["height"]

    image = PIL.Image.open(args["input"])
    if output_width is not None and output_height is None:
        output_height = int(output_width / image.size[0] * image.size[1])
    elif output_width is None and output_height is not None:
        output_width = int(output_height / image.size[1] * image.size[0])
    elif (output_width, output_height) == (None, None):
        print("You have to specify output with or height!")
        print()
        parser.print_usage()
        sys.exit(1)
    image = image.resize((output_width, output_height))

    if args["verbose"]:
        print("Loading caps...")
    palette = CapPalette(args["cap_size"])
    palette.add_directory(args["caps"], args["palette_probability"])
    if args["verbose"]:
        print("Loaded %d caps." % len(palette.caps))
    if args["palette_optimize"] is not None:
        optimized = palette.optimize(args["palette_optimize"])
        #if args["verbose"]:
        #    print("Optimized palette: %d colors" % len(optimized.caps))
        #palette.create_palette_image().save("palette1.png")
        #optimized.create_palette_image().save("palette2.png")
        palette = optimized

    quantized = PIL.Image.new("RGB", image.size)
    data = floyd_steinberg(image, palette, args["verbose"])
    for x in range(output_width):
        for y in range(output_height):
            index = data[y * image.size[0] + x]
            quantized.putpixel((x, y), palette.caps[index].color)
    create_cap_image((output_width, output_height), data, palette).save(args["output"])

    if args["verbose"]:
        print("Have fun drinking %d beers!" % (output_width * output_height))

