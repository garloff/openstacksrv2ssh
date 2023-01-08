#!/usr/bin/env python3
# vim: set ts=4 sw=4 et:
#
# openstacksrv2ssh.py
#
# Collects servers from OpenStack and creates ssh config files
# with Host collections for inclusion into ~/.ssh/config
#
# (c) Kurt Garloff <kurt@garloff.de>, 1/2023
# SPDX-License-Identifier: Apache-2.0

"openstacksrv2ssh.py collects VMs from OpenStack to generate ssh config Host entries"

import sshhosts
from sshidentity import *
import servers
import getopt
import openstack

def usage():
    print("Usage: openstacksrv2ssh.py -a | [ENV [ENV [...]]]")
    print("Creates ~/.ssh/ENV.sshcfg files from OpenStack server lists.")
    print("-a iterates over all cloud configs known and also generates")
    print(" ~/.ssh/openstacksrv.sshcfg referencing all non-empty ones")
    print("If OS_CLOUD is set and no ENV passed, it will be used.")
    return 1

_home = os.environ["HOME"]
_cfgtempl = f"{_home}/.ssh/%s.sshcfg"

def process_cloud(cnm):
    sshfn = _cfgtempl % cnm
    nserv = 0
    if os.access(sshfn, os.R_OK):
        ssh_hosts = sshhosts.collect_sshhosts(sshfn)
        nserv = len(nserv)
    try:
        conn = openstack.connect(cnm, timeout = 24)
    except:
        return nserv
    os_servers = servers.collect_servers(conn)
    for srv in os_servers:
        #if srv.name in ssh_hosts
        print(srv)
    return len(os_servers)

def main(argv):
    allclouds = False
    try:
        optlist, args = getopt.gnu_getopt(argv, "ha", ("help", "all"))
    except getopt.GetoptError as exc:
        print("Error:", exc, file=sys.stderr)
        sys.exit(usage())
    for opt in optlist:
        if opt[0] == "-h" or opt[0] == "--help":
            usage()
            sys.exit(0)
        elif opt[0] =="-a" or opt[0] == "--all":
            allclouds = True
        else:
            raise RuntimeError("option parser error")
    if not allclouds and not args:
        if "OS_CLOUD" in os.environ:
            args = (os.environ["OS_CLOUD"],)
    if not allclouds and not args:
        sys.exit(usage())
    if allclouds:
        print("-a not yet implemented!", file-sys.stderr)
        sys.exit(1)
    processed = 0
    cloudhostfiles = []
    for cloud in args:
        thiscloud = process_cloud(cloud)
        processed += thiscloud
        if thiscloud and allclouds:
            cloudhostfiles.append(_cfgtempl % cloud)
    if processed == 0:
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
