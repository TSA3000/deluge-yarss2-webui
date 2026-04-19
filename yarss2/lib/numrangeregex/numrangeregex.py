def _get_first_digit_and_rest(num):
    if len(num) > 1:
        return (num[0], num[1:])
    elif len(num) == 1:
        return (num[0], "")
    else:
        return ("", "")


def _generate_head(first, zeros, rest, bound):
    parts = []
    for reg in generate_to_bound(rest, bound).split('|'):
        parts.append("%s%s%s" % (first, zeros, reg))
    return "|".join(parts)


def _strip_left_repeated_digit(num, digit):
    for i, ch in enumerate(num):
        if ch != digit:
            return (digit * i, num[i:])
    return (num, "")


def generate_to_bound(num, bound):
    if bound not in ["upper", "lower"]:
        raise ValueError("bound not in ['upper', 'lower']")

    if num == "":
        return ""
    no_range_exit = "0" if bound == "lower" else "9"
    if len(num) == 1 and int(num) == int(no_range_exit):
        return no_range_exit
    if len(num) == 1 and 0 <= int(num) < 10:
        return "[0-%s]" % num if bound == "lower" else "[%s-9]" % num

    first_digit, rest = _get_first_digit_and_rest(num)
    repeated, rest = _strip_left_repeated_digit(rest, no_range_exit)
    head = _generate_head(first_digit, repeated, rest, bound)
    tail = ""
    if bound == "lower":
        if int(first_digit) > 1:
            tail = "[0-%d]" % (int(first_digit) - 1)
            tail += "[0-9]" * (len(num) - 1)
        elif int(first_digit) == 1:
            tail = "0" + "[0-9]" * (len(num) - 1)
    else:
        if int(first_digit) < 8:
            tail = "[%d-9]" % (int(first_digit) + 1)
            tail += "[0-9]" * (len(num) - 1)
        elif int(first_digit) == 8:
            tail = "9" + "[0-9]" * (len(num) - 1)
    return "|".join([head, tail]) if tail else head


def _extract_common(min_, max_):
    fd_min, rest_min = _get_first_digit_and_rest(min_)
    fd_max, rest_max = _get_first_digit_and_rest(max_)
    common = ""
    while fd_min == fd_max and fd_min != "":
        common += fd_min
        fd_min, rest_min = _get_first_digit_and_rest(rest_min)
        fd_max, rest_max = _get_first_digit_and_rest(rest_max)

    return (common, fd_min, rest_min, fd_max, rest_max)


def _generate_for_same_len_nr(min_, max_):
    assert len(min_) == len(max_)
    common, fd_min, rest_min, fd_max, rest_max = _extract_common(min_, max_)
    starting = ending = ""
    if rest_min:
        starting = "|".join(
            "%s%s%s" % (common, fd_min, x)
            for x in generate_to_bound(rest_min, "upper").split("|"))
    else:
        starting = "%s%s" % (common, fd_min)

    if rest_max:
        ending = "|".join(
            "%s%s%s" % (common, fd_max, x)
            for x in generate_to_bound(rest_max, "lower").split("|"))
    else:
        ending = "%s%s" % (common, fd_max)
    if fd_min and fd_max and int(fd_min) + 1 > int(fd_max) - 1:
        assert starting and ending
        return "|".join([starting, ending])

    if fd_min and fd_max and int(fd_min) + 1 == int(fd_max) - 1:
        middle = "%s%d" % (common, int(fd_min) + 1)
    elif fd_min and fd_max:
        middle = common + "[%d-%d]" % (int(fd_min) + 1, int(fd_max) - 1)
    else:
        middle = common

    middle += "[0-9]" * len(rest_min)
    return "|".join([starting, middle, ending])


def _generate_regex(min_, max_):
    nr_dig_min = len(min_)
    nr_dig_max = len(max_)
    if nr_dig_min != nr_dig_max:
        middle_parts = []
        for i in range(nr_dig_min, nr_dig_max - 1):
            middle_parts.append(
                "[1-9]%s" % "".join(["[0-9]" for x in range(i)]))
        middle = "|".join(middle_parts)
        starting = generate_to_bound(min_, "upper")
        ending = _generate_for_same_len_nr("1" + "0" * (len(max_) - 1), max_)
        if middle:
            return "|".join([starting, middle, ending])
        else:
            return "|".join([starting, ending])
    else:
        return _generate_for_same_len_nr(min_, max_)


def _generate_word_bounded_regex(min_, max_, capturing=False):
    template = r"\b(%s)\b" if capturing else r"\b(?:%s)\b"
    return template % _generate_regex(min_, max_)


def generate_numeric_range_regex(min_, max_, capturing=False):
    if min_ > max_:
        raise ValueError("min > max")
    return _generate_word_bounded_regex(str(min_), str(max_))


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: numrageregex.py min max")
        sys.exit(1)
    min_, max_ = sys.argv[1:]
    print(generate_numeric_range_regex(int(min_), int(max_)))


# def assert_in_range(regex, min_, max_, lower, upper):
#     import re
#     pattern = re.compile(regex)
#     for i in xrange(lower, upper):
#         match = pattern.match(str(i))
#         if min_ <= i <= max_:
#             if match is None:
#                 print "ERROR", min_, max_, i
#                 return
#         else:
#             if match is not None:
#                 print "ERROR", min_, max_, i
#                 return


# def test_random_numbers():
#     import random
#     while True:
#         min_1 = random.randint(0, 999999)
#         max_1 = random.randint(min_1, 999999)
#         regex_1 = generate_numeric_range_regex(min_1, max_1)
#         min_2 = random.randint(0, 999)
#         max_2 = random.randint(10000, 999999)
#         regex_2 = generate_numeric_range_regex(min_2, max_2)
#         try:
#             assert_in_range(regex_1, min_1, max_1, 0, 1999999)
#             assert_in_range(regex_2, min_2, max_2, 0, 1999999)
#         except Exception, e:
#             print e


# if __name__ == "__main__":
#     regex = generate_numeric_range_regex(927, 496952)
#     print regex
#     assert_in_range(regex, 927, 496952, 0, 999999)
#     regex = generate_numeric_range_regex(0, 111111)
#     print regex
#     assert_in_range(regex, 0, 111111, 0, 999999)
#     test_random_numbers()
