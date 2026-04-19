from __future__ import absolute_import, unicode_literals

import datetime
import re

date_regex = re.compile("(?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{4})\s(?P<hour>\d{2}):(?P<minutes>\d{2}):(?P<seconds>\d{2})")


def _parse_date_ambiguous(datestring):
    """ Handle dates formatted as 10/04/2014 03:44:14
    If the first value is actually the month, the result will be incorrect.
    """
    result = date_regex.match(datestring)
    if result:
        try:
            d = result.groupdict()
            stamp = datetime.datetime(int(d["year"]), int(d["month"]), int(d["day"]),
                                      int(d["hour"]), int(d["minutes"]), int(d["seconds"]))
            result =  stamp.utctimetuple()
        except (ValueError, TypeError) as e:
            pass
    return result

