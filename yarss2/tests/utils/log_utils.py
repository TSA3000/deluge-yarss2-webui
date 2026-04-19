from __future__ import print_function

import logging
import os
import sys

# isort:imports-localfolder
from .log_color_fmt import ColorFormatter

# Name of logger used by unit tests
plugin_tests_logger_name = 'yarss2_unit_tests'
logging_console_handler_name = 'console_handler'

DEFAULT_CONSOL_LOG_LEVEL = logging.CRITICAL

# Set the environment variable YARSS2_TESTS_LOG_LEVEL to a proper log level to output
# the log statements of the tests logger (plugin_tests_logger_name)
env_yarss2_tests_log_level = os.environ.get('YARSS2_TESTS_LOG_LEVEL', "")

# Set the environment variable YARSS2_LOG_LEVEL and DELUGE_LOG_LEVEL to a proper level to get
# the log statements from the deluge and yarss2 plugin
env_yarss2_log_level = os.environ.get('YARSS2_LOG_LEVEL', "warning")
env_deluge_log_level = os.environ.get('DELUGE_LOG_LEVEL', "error")

default_log_format = "%(asctime)s - %(name)-29s %(filename)35s:%(lineno)-3s - [%(levelname)-7s] %(message)s"
log_format = os.environ.get('TESTS_LOG_FORMAT', default_log_format)


log_str_to_levels = {'critial': logging.CRITICAL,
                     'error': logging.ERROR,
                     'warning': logging.WARNING,
                     'warn': logging.WARNING,
                     'info': logging.INFO,
                     'debug': logging.DEBUG,
                     'notset': logging.NOTSET}


def get_log_level_from_string(str_level, default='info'):
    default_level = log_str_to_levels.get(default, logging.INFO)
    return log_str_to_levels.get(str_level.lower(), default_level)


def get_str_from_log_level(level):
    if level == logging.NOTSET:
        return "unset"
    for k, v in log_str_to_levels.items():
        if level == v:
            return k
    raise Exception("No level with value %s" % level)


def setup_tests_logging():
    setup_tests_loggers(env_yarss2_tests_log_level, env_yarss2_log_level, env_deluge_log_level, log_format)


def setup_tests_loggers(yarss2_tests_log_level_str, yarss2_log_level_str, deluge_log_level_str, log_format):
    yarss2_tests_log_level = DEFAULT_CONSOL_LOG_LEVEL
    yarss2_log_level = DEFAULT_CONSOL_LOG_LEVEL
    deluge_log_level = DEFAULT_CONSOL_LOG_LEVEL

    def get_level(str_level):
        log_level = get_log_level_from_string(str_level, 'notset')
        if log_level == logging.NOTSET:
            raise Exception("Bad log level given: '%s'" % (str_level))
        return log_level

    if yarss2_tests_log_level_str:
        yarss2_tests_log_level = get_level(yarss2_tests_log_level_str)

    if yarss2_log_level_str:
        yarss2_log_level = get_level(yarss2_log_level_str)

    if deluge_log_level_str:
        deluge_log_level = get_level(deluge_log_level_str)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.set_name(logging_console_handler_name)
    formatter = ColorFormatter(fmt=log_format)
    console_handler.setFormatter(formatter)

    class ConsoleFilter(logging.Filter):

        def filter(self, rec):
            if rec.name == plugin_tests_logger_name:
                return rec.levelno >= yarss2_tests_log_level
            if rec.name.startswith("yarss2."):
                return rec.levelno >= yarss2_log_level
            elif rec.name.startswith("deluge."):
                return rec.levelno >= deluge_log_level

    console_handler.addFilter(ConsoleFilter())

    root.addHandler(console_handler)
