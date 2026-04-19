from __future__ import print_function

import os
import shutil
import tempfile

from yarss2.util import logging

from .log_utils import plugin_tests_logger_name

logger = logging.getLogger(plugin_tests_logger_name)


def mkdir(path, ignore_errors=True):
    try:
        os.mkdir(path)
    except OSError:
        if not ignore_errors:
            raise


class TempDir(object):
    """
    class for temporary directories
    creates a (named) directory which is deleted after use.
    All files created within the directory are destroyed

    """
    def __init__(self, suffix="", prefix=None, basedir=None, name=None, clear=True, cleanup=True, id=None):
        """
        Args:
            suffix (str): Suffix to add to directory name
            prefix (str): Prefix to add to directory name
            basedir (str): The base path there to create the dir. Defaults to /tmp
            clear (bool): Clear directory if already exists
            cleanup (bool): Clear directory on exit
            id (str): A unique ID to include in __str__ and disolve error message

        If name is given, no random name value will be generated.
        """
        self.cleanup = cleanup
        self.id = id
        if prefix is None:
            prefix = tempfile.gettempprefix()
        if basedir is None:
            basedir = tempfile.gettempdir()

        # Use the given name as directory name
        if name:
            path = os.path.join(basedir, name)

            if clear:
                logger.debug("Clearing temporary directory: %s", path)
                shutil.rmtree(path, ignore_errors=True)

            mkdir(path, ignore_errors=False)
            self.name = path
        else:
            self.name = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=basedir)

    def mkdir(self, dirname):
        dirpath = os.path.join(self.name, dirname)
        mkdir(dirpath, ignore_errors=False)
        return dirpath

    def mkdirs(self, dirname):
        dirpath = os.path.join(self.name, dirname)
        os.makedirs(dirpath)
        return dirpath

    @property
    def path(self):
        return self.name

    def __del__(self):
        try:
            if self.name:
                self.dissolve()
        except AttributeError:
            pass

    def __enter__(self):
        return self.name

    def __exit__(self, *errstuff):
        self.dissolve()

    def dissolve(self):
        """remove all files and directories created within the tempdir"""
        if self.name and self.cleanup:
            try:
                shutil.rmtree(self.name)
            except OSError as err:
                logger.warn("Error when cleaning up directory %s%s: %s", self.name, " (id: %s)" % self.id, err)
                raise

        self.name = ""

    def __str__(self):
        if self.name:
            return "temporary directory at: %s%s" % (self.name, " (id: %s)" % self.id)
        else:
            return "dissolved temporary directory"
