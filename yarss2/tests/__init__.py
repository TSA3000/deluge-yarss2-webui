from deluge.log import setup_logger

# Ensure packages in include dir are added to sys.path
from . import common as test_common  # noqa: F401
from .utils.log_utils import setup_tests_logging

setup_logger()

setup_tests_logging()
