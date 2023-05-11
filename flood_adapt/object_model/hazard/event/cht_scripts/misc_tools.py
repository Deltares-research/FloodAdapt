# -*- coding: utf-8 -*-
"""
Created on Wed Apr 28 16:28:15 2021

@author: ormondt
"""

import json

import numpy as np
import yaml
from scipy.interpolate import RegularGridInterpolator


def interp2(x0, y0, z0, x1, y1, method="linear"):
    f = RegularGridInterpolator(
        (y0, x0), z0, bounds_error=False, fill_value=np.nan, method=method
    )
    # reshape x1 and y1
    if x1.ndim > 1:
        sz = x1.shape
        x1 = x1.reshape(sz[0] * sz[1])
        y1 = y1.reshape(sz[0] * sz[1])
        # interpolate
        z1 = f((y1, x1)).reshape(sz)
    else:
        z1 = f((y1, x1))

    return z1


def findreplace(file_name, str1, str2):
    # read input file
    fin = open(file_name, "rt")
    # read file contents to string
    data = fin.read()
    # replace all occurrences of the required string
    data = data.replace(str1, str2)
    # close the input file
    fin.close()
    # open the input file in write mode
    fin = open(file_name, "wt")
    # overrite the input file with the resulting data
    fin.write(data)
    # close the file
    fin.close()


def read_json_js(file_name):
    # Read json javascript file (skipping the first line), and return json object
    fid = open(file_name, "r")
    lines = fid.readlines()
    fid.close()
    lines = lines[1:]
    jsn_string = ""
    for line in lines:
        # Strips the newline character
        jsn_string += line.strip()
    jsn = json.loads(jsn_string)
    return jsn


def write_json_js(file_name, jsn, first_line):
    # Writes json javascript file
    if type(jsn) == list:
        f = open(file_name, "w")
        f.write(first_line + "\n")
        f.write("[\n")
        for ix, x in enumerate(jsn):
            json_string = json.dumps(x)
            if ix < len(jsn) - 1:
                f.write(json_string + ",")
            else:
                f.write(json_string)
            f.write("\n")
        f.write("]\n")
        f.close()
    else:
        f = open(file_name, "w")
        f.write(first_line + "\n")
        json_string = json.dumps(jsn)
        f.write(json_string + "\n")
        f.close()


def write_csv_js(file_name, csv_string, first_line):
    # Writes json javascript file
    csv_string = csv_string.replace(chr(13), "")
    f = open(file_name, "w")
    f.write(first_line + "\n")
    f.write(csv_string)
    f.write("`;")
    f.close()


def rgb2hex(rgb):
    return "%02x%02x%02x" % rgb


def dict2yaml(file_name, dct, sort_keys=False):
    yaml_string = yaml.dump(dct, sort_keys=sort_keys)
    file = open(file_name, "w")
    file.write(yaml_string)
    file.close()


def yaml2dict(file_name):
    file = open(file_name, "r")
    dct = yaml.load(file, Loader=yaml.FullLoader)
    return dct
