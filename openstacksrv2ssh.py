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

import os
import sys
import getopt
import openstack
import sshhosts
import servers
import allclouds
import ipconnected

def usage():
    "Help"
    print("Usage: openstacksrv2ssh.py [options] -a | [ENV [ENV [...]]]")
    print("Creates ~/.ssh/ENV.sshcfg files from OpenStack server lists.")
    print("-a (or --all) iterates over all cloud configs known and also generates")
    print(" ~/.ssh/openstacksrv.sshcfg referencing all non-empty ones.")
    print("If OS_CLOUD is set and no ENV passed, it will be used.")
    print("Options: -v/--verbose, -d/--debug, -q/--quiet and -h/--help.")
    return 1

_home = os.environ["HOME"]
_cfgtempl = f"{_home}/.ssh/%s.sshcfg"
_nametempl = "%1s-%2s"

DEBUG = False
VERBOSE = False
QUIET = False

def find_by_name(srch, lst):
    "Search list lst for a .name == srch), return idx, -1 if not found."
    idx = 0
    for elem in lst:
        if elem.name == srch:
            return idx
        idx += 1
    return -1

def fill_values(shost, sshnm, osrv, ipaddr, oconn):
    """Fill in SSHhost fields from osrv, with name sshnm,
        using oconn to query more data if needed."""
    shost.name = sshnm
    if ipaddr:
        shost.hostname = ipaddr
    if not shost.user:
        osrv.collectinfo2(oconn)
        if osrv.usernm:
            shost.user = osrv.usernm
    # Any magic to fill in fwd_agent?
    if osrv.keypair and not shost.id_file:
        keyfile = sshhosts.find_sshkeyfile(osrv.keypair)
        if keyfile:
            shost.id_file = keyfile

def ssh_host_from_srv(osrv, ipaddr, oconn, sshnm=None):
    """Create new SSHhost object from osrv.
       Only returns object if hostname is set."""
    if not sshnm:
        sshnm = osrv.name
    shost = sshhosts.SSHhost()
    fill_values(shost, sshnm, osrv, ipaddr, oconn)
    if shost.hostname:
        return shost
    return None

def write_sshcfg(cnm, shosts):
    "Write out ssh cfg file with hosts for cloud cnm"
    sshfn = _cfgtempl % cnm
    sshcf = open(sshfn, "w", encoding="UTF-8")
    print("# SSH config file written by openstacksrv2ssh.py", file=sshcf)
    print(f"# Hosts from cloud {cnm}\n", file=sshcf)
    for shost in shosts:
        print(f"{shost}\n", file=sshcf)
    if not QUIET and len(shosts):
        print(f"{len(shosts)} entries written to {sshfn}")

def write_allsshcfg(fnames):
    "Write out openstacksrc2ssh.sshcfg including all others"
    if not fnames:
        return
    home = os.environ["HOME"]
    with open(home + "/.ssh/openstacksrv2ssh.sshcfg", "w", encoding='UTF-8') as ofile:
        print("# SSH config file including openstack host list files", file=ofile)
        print("# written by openstacksrv2ssh.py -a, don't change as it will be overwritten",
                file=ofile)
        for fnm in fnames:
            print(f"Include {fnm}", file=ofile)
    if not QUIET:
        print(f"{len(fnames)} files included in ~/.ssh/openstacksrv2ssh.sshcfg")

def connect(cnm):
    "Try to establish an authorized connection to cloud cnm"
    try:
        conn = openstack.connect(cnm, timeout=16, api_timout=24)
        conn.authorize()
    except BaseException as exc:
        try:
            if conn:
                # Connection succeeded, authorization did not, so retry with default domain
                conn = openstack.connect(cnm, timeout=16, api_timout=24,
                                         default_domain='default', project_domain_id='default')
                conn.authorize()
            else:
                raise exc
        except:
            if not QUIET:
                print(f"No connection to cloud {cnm}", file=sys.stderr)
            if VERBOSE:
                print(f"{exc}", file=sys.stderr)
            return None
    return conn


def process_cloud(cnm):
    "Iterate over all servers in cloud and return list of SSHhost objects"
    sshfn = _cfgtempl % cnm
    ssh_hosts = []
    if os.access(sshfn, os.R_OK):
        ssh_hosts = sshhosts.collect_sshhosts(sshfn)
        if DEBUG:
            print(f"Found {len(ssh_hosts)} ssh hosts in {sshfn}", file=sys.stderr)
    else:
        if DEBUG:
            print(f"No ssh hosts in {sshfn}", file=sys.stderr)
    conn = connect(cnm)
    if not conn:
        return 0
    os_servers = servers.collect_servers(conn)
    ownnet, routers = ipconnected.ownnet_and_routers(conn, DEBUG)
    # Add / correct OpenStack servers
    for srv in os_servers:
        ipaddr = ipconnected.preferred_ip(srv.ipaddrs, ownnet, routers, DEBUG)
        sshnm = _nametempl % (cnm, srv.name)
        idx = find_by_name(sshnm, ssh_hosts)
        if DEBUG:
            print(f"OpenStack Server {sshnm} in ssh list: {idx}, IP {ipaddr}")
        if idx == -1:
            newhost = ssh_host_from_srv(srv, ipaddr, conn, sshnm)
            if newhost:
                ssh_hosts.append(newhost)
        else:
            host = ssh_hosts[idx]
            fill_values(host, sshnm, srv, ipaddr, conn)
    # Remove servers that no longer exist
    for shost in ssh_hosts:
        shortnm = shost.name[len(cnm)+1:]
        if find_by_name(shortnm, os_servers) == -1:
            if DEBUG:
                print(f"Remove {shost.name} ({shortnm}) as it's not in OpenStack server list",
                      file=sys.stderr)
            ssh_hosts.remove(shost)
    if VERBOSE:
        print(f"# Servers from cloud {cnm}")
        for shost in ssh_hosts:
            print(f"{shost}\n")
    if len(ssh_hosts) != 0:
        write_sshcfg(cnm, ssh_hosts)
    return len(ssh_hosts)


def main(argv):
    "Entry point for main program"
    doall = False
    global DEBUG, VERBOSE, QUIET
    try:
        optlist, args = getopt.gnu_getopt(argv, "havdq",
            ("help", "all", "verbose", "debug", "quiet"))
    except getopt.GetoptError as exc:
        print("Error:", exc, file=sys.stderr)
        return usage()
    for opt in optlist:
        if opt[0] == "-h" or opt[0] == "--help":
            usage()
            sys.exit(0)
        elif opt[0] =="-a" or opt[0] == "--all":
            doall = True
        elif opt[0] =="-v" or opt[0] == "--verbose":
            VERBOSE = True
        elif opt[0] =="-d" or opt[0] == "--debug":
            DEBUG = True
        elif opt[0] =="-q" or opt[0] == "--quiet":
            QUIET = True
        else:
            raise RuntimeError("option parser error")
    if not doall and not args:
        if "OS_CLOUD" in os.environ:
            args = (os.environ["OS_CLOUD"],)
    if not doall and not args:
        sys.exit(usage())
    if doall:
        args = allclouds.collectallclouds()
    processed = 0
    cloudhostfiles = []
    for cloud in args:
        thiscloud = process_cloud(cloud)
        processed += thiscloud
        if thiscloud and allclouds:
            cloudhostfiles.append(_cfgtempl % cloud)
    if doall:
        write_allsshcfg(cloudhostfiles)
    if processed == 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
