# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import re

from lib.numrangeregex import numrangeregex


def pattern_to_regex(pattern):
    """Convert named pattern to named regex"""

    patterns = [(r'%m(?P<restrict>\((?P<start>\d{1,2})?(?P<to>-)?(?P<end>\d{1,2})\))?', '(?P<m>%s)', r"\d{1,2}"),
                (r'%d(?P<restrict>\((?P<start>\d{1,2})?(?P<to>-)?(?P<end>\d{1,2})\))?', '(?P<d>%s)', r"\d{1,2}"),
                (r'%s(?P<restrict>\((?P<start>\d{1,2})?(?P<to>-)?(?P<end>\d{1,2})\))?', '(?P<s>%s)', r"\d{1,2}"),
                (r'%Y(?P<restrict>\((?P<start>\d{4})?(?P<to>-)?(?P<end>\d{4})\))?', '(?P<Y>%s)', r"\d{4}"),
                (r'%y(?P<restrict>\((?P<start>\d{2})?(?P<to>-)?(?P<end>\d{2})\))?', '(?P<y>%s)', r"\d{2}"),
                (r'%E(?P<restrict>\((?P<start>\d{2})?(?P<to>-)?(?P<end>\d{2})\))?', '(?P<e>%s)', r"\d{2}"),
                (r'%S(?P<restrict>\((?P<start>\d{1})?(?P<to>-)?(?P<end>\d{1})\))?', '(?P<s>%s)', r"\d+{1}"),
                (r'%e(?P<restrict>\((?P<start>\d+)?(?P<to>-)?(?P<end>\d+)\))?', '(?P<e>%s)', r"\d+"),
                ]

#    patterns = [('%Y', '(?P<Y>[0-9]{4})'),
#                ('%y', '(?P<y>[0-9]{2})'),
#                ('%m', '(?P<m>[0-9]{1,2})'),
#                ('%d', '(?P<d>[0-9]{1,2})'),
#                ('%s', '(?P<s>[0-9]+)'),
#                ('%S', '(?P<s>[0-9]+){1}'),
#                ('%e', '(?P<e>[0-9]+)'),
#                ('%E', '(?P<e>[0-9]{2})')]
    out = pattern
    for p in patterns:
        # exp = re.compile(p[0], re.IGNORECASE)
        exp = re.compile(p[0])
        match = exp.search(pattern)
        if match:
            # print("replace: '%s'" % match.group(0))
            groupdict = match.groupdict()
            # print("groupdict:", groupdict)
            # No restrictions
            if "restrict" not in groupdict or groupdict["restrict"] is None:
                out = out.replace(match.group(0), p[1] % p[2])
            else:
                # Pattern has destrictions
                start = None if "start" not in groupdict else groupdict["start"]
                to = None if "to" not in groupdict else True
                end = None if "end" not in groupdict else groupdict["end"]

                if start and not to and not end:
                    replace_with = start
                elif start and to and not end:
                    replace_with = numrangeregex.generate_to_bound(start, "upper")
                elif start and to and end:
                    replace_with = numrangeregex.generate_numeric_range_regex(start, end)
                elif to and end:
                    replace_with = numrangeregex.generate_to_bound(end, "lower")
                elif to:
                    # Only to is present (-). Means all, same as nothing
                    replace_with = p[1]
                out = p[1] % out.replace(match.group(0), replace_with)
    return out


# def pattern_to_regex(pattern):
#     """Convert named pattern to named regex"""
#
#     exp = re.compile(r'(.*?)([Ss])([0-9]+)([Ee])([0-9]+)(.*)', re.IGNORECASE)
#     match = exp.match(filename)
#     if match:
#
#     patterns = [('%Y\((\d+)(-)?(\d+)\)', '(?P<Y>[0-9]{4})'),
#                 ('%y', '(?P<y>[0-9]{2})'),
#                 ('%m', '(?P<m>[0-9]{1,2})'),
#                 ('%d', '(?P<d>[0-9]{1,2})'),
#                 ('%s', '(?P<s>[0-9]+)'),
#                 ('%S', '(?P<s>[0-9]+){1}'),
#                 ('%e', '(?P<e>[0-9]+)'),
#                 ('%E', '(?P<e>[0-9]{2})')]
#
# #    patterns = [('%Y', '(?P<Y>[0-9]{4})'),
# #                ('%y', '(?P<y>[0-9]{2})'),
# #                ('%m', '(?P<m>[0-9]{1,2})'),
# #                ('%d', '(?P<d>[0-9]{1,2})'),
# #                ('%s', '(?P<s>[0-9]+)'),
# #                ('%S', '(?P<s>[0-9]+){1}'),
# #                ('%e', '(?P<e>[0-9]+)'),
# #                ('%E', '(?P<e>[0-9]{2})')]
# #    out = pattern
#     for p in patterns:
#         out = out.replace(p[0], p[1])
#     return out
#


def escape_regex(pattern):
    escape_chars = '[]()^$\\.?*+|'
    out = []
    for c in pattern:
        try:
            escape_chars.index(c)
            out.append('\\' + c)
        except ValueError:
            out.append(c)
    return ''.join(out)


def suggest_pattern(filename):

    # E.g. S02E03, s5e13
    exp = re.compile(r'(.*?)([Ss])([0-9]+)([Ee])([0-9]+)(.*)', re.IGNORECASE)
    match = exp.match(filename)
    if match:
        suggestion = (escape_regex(match.group(1)) + escape_regex(match.group(2)) + "%s"
                      + escape_regex(match.group(4)) + "%e" + escape_regex(match.group(6)))
        return [suggestion]

    # Date e.g. 2012.05.20
    exp = re.compile(r'(.*?)([0-9]{4})([\.\-xX])([0-9]{1,2})([\.\-xX])([0-9]{1,2})(.*)', re.IGNORECASE)
    match = exp.match(filename)
    if match:
        suggestions = []
        suggestions.append(escape_regex(match.group(1)) + "%Y" + escape_regex(match.group(3))
                           + "%m" + escape_regex(match.group(5)) + "%d" + escape_regex(match.group(7)))
        suggestions.append(escape_regex(match.group(1)) + "%Y" + escape_regex(match.group(3))
                           + "%d" + escape_regex(match.group(5)) + "%m" + escape_regex(match.group(7)))
        return suggestions

    exp = re.compile(r'(.*?)([0-9]{2}).([0-9]{2}).([0-9]{2})', re.IGNORECASE)
    match = exp.match(filename)
    if match:
        suggestions = []
        suggestions.append(escape_regex(match.group(1)) + "%y" + "." + "%m" + "." + "%d" + escape_regex(match.group(5)))
        suggestions.append(escape_regex(match.group(1)) + "%y" + "." + "%d" + "." + "%m" + escape_regex(match.group(5)))
        suggestions.append(escape_regex(match.group(1)) + "%d" + "." + "%m" + "." + "%y" + escape_regex(match.group(5)))
        suggestions.append(escape_regex(match.group(1)) + "%m" + "." + "%d" + "." + "%y" + escape_regex(match.group(5)))
        return suggestions

    # E.g. 1x01 1.01 1-01
    exp = re.compile(r'(.*?)([0-9]+)[xX\.\-]{1}([0-9]+)(.*)', re.IGNORECASE)
    match = exp.match(filename)
    if match:
        suggestion = match.group(1) + "%s" + match.group(3) + "%e" + match.group(4)
        return [suggestion]

    # E.g. 108  for Season 1, episode 8
    exp = re.compile(r'(.*?)([0-9]{3})(.*)', re.IGNORECASE)
    match = exp.match(filename)
    if match:
        suggestion = match.group(1) + "%s" + "%E" + match.group(3)
        return [suggestion]


def test(title, pattern):
    print("Title  :", title)
    print("Pattern:", pattern)
    regex = pattern_to_regex(pattern)
    print("regex  :", regex)

    exp = re.compile(regex, re.IGNORECASE)
    m = exp.match(title)
    if m:
        # pattern = self.escape_regex_special_chars(match.group(1)).lower().translate(trans_table) +
        # '%s' + self.escape_regex_special_chars(match.group(3)) + '%e'
        # if m
        return m.groupdict()
    else:
        return None


if __name__ == '__main__':
    print("\n" * 6)

    pattern = "%Y(2011-2014)"

    title = "2011"
    print("%s  : %s : %s" % (title, pattern, test(title, pattern)))

    # print("\n", test("2012", "%Y(2011-2030)")
    pattern = "%Y"
    print("%s   : %s : %s" % (title, pattern, test(title, pattern)))

    title = "Tron Uprising S01E01 HDTV x264-2HD"
    # patterns = suggest_pattern(title)[0]
    pattern = "Tron Uprising S%sE%e HDTV x264-2HD"

    print("%s   : %s : %s" % (title, pattern, test(title, pattern)))
    print()
    title = "My Favourite Show 108"
    pattern = "My Favourite Show %s(?P<e>[0-9]{2})"
    # patterns = suggest_pattern(title)[9]
    print("%s   : %s : %s" % (title, pattern, test(title, pattern)))
    print()
    title = "The Colbert Report - 2012x10.02 - Jorge Ramos (.mp4)"
    pattern = "The Colbert Report - %Yxm%.%d - Jorge Ramos (.mp4)"
    # print("%s   : %s : %s" % (title, pattern, test(title, pattern))
    # patterns = suggest_pattern(title)
    # print("\n", test(title, patterns[0])

    title = "Tron Uprising S01E01 HDTV x264-2HD"
    # patterns = suggest_pattern(title)[0]
    pattern = "Tron Uprising S%sE%e HDTV %sE%e %y %S %S"
    print("%s   : %s : %s" % (title, pattern, test(title, pattern)))
