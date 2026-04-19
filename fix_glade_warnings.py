#!/usr/bin/env python

import os
import re

"""Removes the swapped="no" attribute from glade files"""


def fix_glade_file(filepath):
    print("Fixing:", filepath)
    filepath_out = filepath + "_tmp"
    infile = open(filepath, 'r')
    outfile = open(filepath_out, 'w')

    for line in infile.readlines():
        line = re.sub(r' swapped="no"', r'', line)
        outfile.write(line)
    infile.close()
    outfile.close()
    os.rename(filepath_out, filepath)


if __name__ == '__main__':
    path = "yarss2/data/"

    dir_list = os.listdir(path)
    for fname in dir_list:
        if fname.endswith(".glade") or fname.endswith(".ui"):
            fix_glade_file(os.path.join(path, fname))
