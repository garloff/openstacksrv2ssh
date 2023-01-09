#!/usr/bin/env python3
# vim: set ts=4 sw=4 et:
#
# allclouds.py
#
# Collects a list of all configured clouds from clouds.yaml
# at .:~/.config/openstack/:/etc/openstack
#
# (c) Kurt Garloff <kurt@garloff.de>, 1/2023
# SPDX-License-Identifier: Apache-2.0

"Parse cloud.yaml files and return a list of configured clouds."

import os
import sys
import yaml

def collectclouds(cyaml, syaml = None):
    "return a list of configured clouds in cyaml"
    with open(cyaml, "r", encoding='UTF-8') as cfile:
        clouddict = yaml.safe_load(cfile)
    #clouddict = yaml.safe_load(open(cyaml, "r", encoding='UTF-8'))
    #securedict = None
    if syaml:
        #securedict = yaml.safe_load(open(syaml, "r", encoding='UTF-8'))
        pass
    # Could check whether we all needed secrets
    #print(f"{clouddict}")
    return list(clouddict["clouds"].keys())

def collectallclouds():
    "Look for clouds.yaml at all known places and collect all"
    cloudlist = []
    for path in (".", "~/.config/openstack", "/etc/openstack"):
        if "~" in path:
            home = os.environ["HOME"]
            path = path.replace("~", home)
        if os.access(path+"/clouds.yaml", os.R_OK):
            if os.access(path+"/secure.yaml", os.R_OK):
                cloudlist.extend(collectclouds(path+"/clouds.yaml", path+"/secure.yaml"))
            else:
                cloudlist.extend(collectclouds(path+"/clouds.yaml"))
    # TODO: Remove duplicates
    return cloudlist

def main(argv):
    "Main entry point for testing"
    clouds = collectallclouds()
    print(f"{clouds}")


if __name__ == "__main__":
    main(sys.argv[1:])
