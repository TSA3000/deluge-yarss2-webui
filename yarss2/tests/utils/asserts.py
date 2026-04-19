import difflib

from .assert_funcs import assert_almost_equal, assert_equal


def _get_lists_diff(l1, l2):
    def get_list_str(lines):
        return "[\n%s\n]" % ("\n".join([line for line in lines]))

    diff = ('\n' + '\n'.join(difflib.ndiff(
        get_list_str(l1).splitlines(),
        get_list_str(l2).splitlines())))
    return diff


def _dict_keys_equal(dict1, dict2):
    if len(dict1) != len(dict2):
        return False

    dict1_keys_set = set(list(dict1.keys()))
    dict2_keys_set = set(list(dict2.keys()))
    return dict1_keys_set == dict2_keys_set


def _get_dicts_diff(dict1, dict2, diff_keys=[]):
    def get_dict_str(d, keys):
        return "{\n    %s\n}" % \
            (",\n    ".join(["'%s': %s" % (k, "'%s'" % d[k] if type(d[k]) is str else d[k]) for k in keys]))

    dict1_str = get_dict_str(dict1, diff_keys if diff_keys else sorted(list(dict1.keys())))
    dict2_str = get_dict_str(dict2, diff_keys if diff_keys else sorted(list(dict2.keys())))
    dict1_str_lines = dict1_str.splitlines()
    dict2_str_lines = dict2_str.splitlines()

    difflines = difflib.ndiff(dict1_str_lines, dict2_str_lines)
    diff = ('\n' + '\n'.join([line.strip() for line in difflines]))
    return diff


def assert_almost_equal_any(elt1, elt2, **kwargs):
    if isinstance(elt1, list) and isinstance(elt2, list):
        assert_almost_equal_list(elt1, elt2, **kwargs)
    elif isinstance(elt1, dict) and isinstance(elt2, dict):
        assert_almost_equal_dict(elt1, elt2, **kwargs)
    elif isinstance(elt1, dict) or isinstance(elt2, float):
        assert_almost_equal(elt1, elt2, places=kwargs.get('places', 3), msg='Got {}. Expected: {}'.format(elt1, elt2))
    else:
        assert_equal(elt1, elt2)


def assert_almost_equal_list(list1, list2, **kwargs):
    """
    Catch the initial AssertError and print the output diff created by assert_equal
    """
    try:
        _assert_almost_equal_list(list1, list2, **kwargs)
    except AssertionError as err1:
        try:
            assert_equal(list1, list2)
        except AssertionError as err2:
            raise AssertionError("%s\n%s" % (err1, err2))


def _assert_almost_equal_list(list1, list2, **kwargs):
    if not isinstance(list1, list) or not isinstance(list2, list):
        if not isinstance(list1, list):
            raise TypeError("Expected list, but found type %s for list1" % (type(list1)))
        else:
            raise TypeError("Expected list, but found type %s for list2" % (type(list2)))

    if len(list1) != len(list2):
        msg = "List lengths differ. %d != %d" % (len(list1), len(list2))
        diff = _get_lists_diff(sorted(list1), sorted(list2))
        raise AssertionError("%s\n%s" % (msg, diff))

    for i, _ in enumerate(list1):
        assert_almost_equal_any(list1[i], list2[i], **kwargs)


def assert_almost_equal_dict(dict1, dict2, **kwargs):
    """
    Catch the initial AssertError and print the output diff created by assert_equal
    """
    try:
        _assert_almost_equal_dict(dict1, dict2, **kwargs)
    except AssertionError as err1:
        try:
            assert_equal(dict1, dict2)
        except AssertionError as err2:
            raise AssertionError("%s\n\n%s" % (err2, err1))


def _assert_almost_equal_dict(dict1, dict2, **kwargs):

    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        if not isinstance(dict1, dict):
            raise TypeError("Expected dict, but found type %s for dict1" % (type(dict1)))
        else:
            raise TypeError("Expected dict, but found type %s for dict2" % (type(dict2)))

    if not _dict_keys_equal(dict1, dict2):
        msg = "Dicts lengths differ. %d != %d" % (len(dict1), len(dict2))
        diff = _get_lists_diff(sorted(list(dict1.keys())), sorted(list(dict2.keys())))
        raise AssertionError("%s\n%s" % (msg, diff))

    diffing_keys = []
    for key in dict1:
        try:
            assert_almost_equal_any(dict1[key], dict2[key], **kwargs)
        except AssertionError:
            diffing_keys.append(key)

    if diffing_keys:
        diff = _get_dicts_diff(dict1, dict2, diff_keys=diffing_keys)
        raise AssertionError("%s\n%s" % ("Differing dict values:", diff))
