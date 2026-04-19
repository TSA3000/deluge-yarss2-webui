import re
import unittest

from numrangeregex import generate_numeric_range_regex


class NrRangeRegexGeneratorTest(unittest.TestCase):

    def _verify_range(self, regex, min_, max_, from_min_, to_max_):
        for nr in range(from_min_, to_max_ + 1):
            if min_ <= nr <= max_:
                self.assertTrue(re.search(regex, str(nr)) is not None)
            else:
                self.assertTrue(re.search(regex, str(nr)) is None)

    def test_repeated_digit(self):
        regex = generate_numeric_range_regex(10331, 20381)
        self._verify_range(regex, 10331, 20381, 0, 99999)

    def test_repeated_zeros(self):
        regex = generate_numeric_range_regex(10031, 20081)
        self._verify_range(regex, 10031, 20081, 0, 99999)

    def test_zero_one(self):
        regex = generate_numeric_range_regex(10301, 20101)
        self._verify_range(regex, 10301, 20101, 0, 99999)

    def test_different_len_numbers_1(self):
        regex = generate_numeric_range_regex(1030, 20101)
        self._verify_range(regex, 1030, 20101, 0, 99999)

    def test_repetead_one(self):
        regex = generate_numeric_range_regex(102, 111)
        self._verify_range(regex, 102, 111, 0, 1000)

    def test_small_diff_1(self):
        regex = generate_numeric_range_regex(102, 110)
        self._verify_range(regex, 102, 110, 0, 1000)

    def test_small_diff_2(self):
        regex = generate_numeric_range_regex(102, 130)
        self._verify_range(regex, 102, 130, 0, 1000)

    def test_random_range_1(self):
        regex = generate_numeric_range_regex(4173, 7981)
        self._verify_range(regex, 4173, 7981, 0, 99999)

    def test_one_digit_numbers(self):
        regex = generate_numeric_range_regex(3, 7)
        self._verify_range(regex, 3, 7, 0, 99)

    def test_one_digit_at_bounds(self):
        regex = generate_numeric_range_regex(1, 9)
        self._verify_range(regex, 1, 9, 0, 1000)

    def test_power_of_ten(self):
        regex = generate_numeric_range_regex(1000, 8632)
        self._verify_range(regex, 1000, 8632, 0, 99999)

    def test_different_len_numbers_2(self):
        regex = generate_numeric_range_regex(13, 8632)
        self._verify_range(regex, 13, 8632, 0, 10000)

    def test_different_len_numbers_small_diff(self):
        regex = generate_numeric_range_regex(9, 11)
        self._verify_range(regex, 9, 11, 0, 100)

    def test_different_len_zero_eight_nine(self):
        regex = generate_numeric_range_regex(90, 980099)
        self._verify_range(regex, 90, 980099, 0, 999999)

    def test_small_diff(self):
        regex = generate_numeric_range_regex(19, 21)
        self._verify_range(regex, 19, 21, 0, 100)

    def test_different_len_zero_one_nine(self):
        regex = generate_numeric_range_regex(999, 10000)
        self._verify_range(regex, 999, 10000, 1, 20000)


if __name__ == "__main__":
    unittest.main()
