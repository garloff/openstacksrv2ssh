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
_nametempl = "%1s-%2s"

def find_by_name(srch, lst):
    "Search list lst for a .name == srch), return idx, -1 if not found."
    idx = 0
    for elem in lst:
        if elem.name == srch:
            return idx
        idx += 1
    return -1

def fill_values(shost, sshnm, osrv, oconn):
    shost.name = sshnm
    ipaddr = osrv.get_ip()
    if ipaddr:
        shost.hostname = osrv.get_ip()
    if not shost.user:
        osrv.collectinfo2(oconn)
        if osrv.usernm:
            shost.user = osrv.usernm
    # Any magic to fill in fwd_agent?
    if osrv.keypair and not shost.id_file:
        keyfile = find_sshkeyfile(osrv.keypair)
        if keyfile:
            shost.id_file = keyfile

def ssh_host_from_srv(osrv, oconn, sshnm=None):
    if not sshnm:
        sshnm = osrv.name
    shost = sshhosts.SSHhost()
    fill_values(shost, sshnm, osrv, oconn)
    if shost.hostname:
        return shost
    else:
        return None

def process_cloud(cnm):
    sshfn = _cfgtempl % cnm
    nserv = 0
    if os.access(sshfn, os.R_OK):
        ssh_hosts = sshhosts.collect_sshhosts(sshfn)
        nserv = len(nserv)
    else:
        ssh_hosts = []
    try:
        conn = openstack.connect(cnm, timeout = 24)
    except:
        return nserv
    os_servers = servers.collect_servers(conn)
    for srv in os_servers:
        sshnm = _nametempl % (cnm, srv.name)
        idx = find_by_name(sshnm, ssh_hosts)
        if idx == -1:
            newhost = ssh_host_from_srv(srv, conn, sshnm)
            if newhost:
                ssh_hosts.append(newhost)
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
