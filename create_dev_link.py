#!/usr/bin/env python
from __future__ import print_function

import argparse
import os
import shutil
import sys
from subprocess import check_output

try:
    from termcolor import colored, cprint
except ImportError:

    def cprint(*arg, **kwargs):
        arg = [arg[0]]
        print(*arg)

    def colored(text, color):
        return text


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="Create development link for Deluge plugin into config directory")
    argparser.add_argument("-c", "--config",
                           help="Config path to copy dev link to. Default: '%(default)s'.", default="~/.config/deluge")
    argparser.add_argument("-w", "--workdir", help="Workdir. Default: '%(default)s'.", default=".")
    argparser.add_argument("-f", "--force", action='store_true', default=False,
                           help="Create config dir if it doesn't exist and delete temp dir before build.")
    argparser.add_argument("--temp-dir", default="temp",
                           help="The name of the temporary dir for building. Default: '%(default)s'.")
    argparser.add_argument("--no-delete-temp", action='store_true', help="Do not delete the temporary build directory.")
    argparser.add_argument("-v", "--verbose", action='store_true', help="Be verbose.")
    args = argparser.parse_args()

    config_path = os.path.expanduser(args.config)
    temp_dir = os.path.expanduser(args.temp_dir)

    if not os.path.isdir(config_path):
        if not args.force:
            cprint("Directory does not exist: %s" % config_path, 'red')
            sys.exit(1)
        else:
            os.makedirs(config_path)

    if os.path.isdir(args.temp_dir):
        if not args.force:
            cprint("Temp dir '%s' dir already exists in this directory. Remove this directory first." %
                   args.temp_dir, 'red')
            sys.exit(1)
        else:
            shutil.rmtree(args.temp_dir)

    if args.verbose:
        print("Creating dir '%s'" % args.temp_dir)

    os.mkdir(args.temp_dir)

    os.environ['PYTHONPATH'] = args.temp_dir
    cmd = ["python", "setup.py", "build", "develop", "--install-dir", "%s" % args.temp_dir]

    if args.verbose:
        print("Building: '%s'" % " ".join(cmd))

    build_result = check_output(cmd)

    if args.verbose:
        cprint(build_result, 'yellow')

    d = os.listdir(args.workdir)
    egg_dir = [d for d in os.listdir(args.workdir) if d.endswith('.egg-info')]

    if not egg_dir:
        print("No '.egg-info' directory found in '%s'" % args.workdir)
        sys.exit(1)

    plugin_name = egg_dir[0].split(".egg-info")[0]
    cmd = ["cp", "%s/%s.egg-link" % (args.temp_dir, plugin_name), "%s/plugins/" % config_path]

    if args.verbose:
        print("Copying egg-link: '%s'" % " ".join(cmd))

    copy_result = check_output(cmd)

    if not args.no_delete_temp:
        if args.verbose:
            print("Deleting temp dir '%s'" % args.temp_dir)

        shutil.rmtree(args.temp_dir)
