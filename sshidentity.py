#!/usr/bin/env python3
# vim: set ts=4 sw=4 et:
#
# sshidentity
#
# Find ssh identity key files
#
# (c) Kurt Garloff, 01/2023
# SPDX-License-Identifier: Apache-2.0

"""find_sshkeyfile searches passed searchpath (colon-separated)
   for ssh keyfiles with name.pem."""

import os
import sys

DEF_SEARCHPATH="~/.ssh:~:."

def find_sshkeyfile(name, searchpath=DEF_SEARCHPATH):
    "Look for keyfile and return full filename or None"
    if "~" in searchpath:
        home = os.environ["HOME"]
        searchpath = searchpath.replace("~", home)
    for path in searchpath.split(":"):
        if path[0] != "/":
            path = os.getcwd() + "/" + path
            if path[-2:] == "/.":
                path = path[:-2]
        fname = f"{path}/{name}.pem"
        if os.access(fname, os.R_OK):
            return fname
    return None

def main(argv):
    "entry point for testing"
    for name in argv:
        filename = find_sshkeyfile(name)
        print(f"{name}: {filename}")

if __name__ == "__main__":
    main(sys.argv[1:])
