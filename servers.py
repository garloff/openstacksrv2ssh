#!/usr/bin/env python3
# vim: set ts=4 sw=4 et:
#
# servers.py
#
# Collect information from OpenStack to create information
# for creating ssh config Host entries
#
# (c) Kurt Garloff <kurt@garloff.de>
# SPDX-License-Identifier: Apache-2.0

"""Implements class OStackServer which collects infos on
   Servers (VMs) via the OpenStack API. Used to create
   Host entries for ssh.
   collect_servers() returns a list of OStackServer objects
   collected by calling the passed OpenStack connection object.
"""

import sys
import os
import openstack

class OStackServer:
    "class collecting infos about servers (VMs) from OpenStack"
    def __init__(self):
        "default c'tor"
        self.uid = None
        self.name = None
        self.ipaddrs = []
        self.keypair = None
        self.flavor = None
        self.image = None
        self.usernm = None
    def collectinfo(self, srvlistentry):
        """extract information from passed server list entry,
           does not fill in usernm"""
        self.uid = srvlistentry.id
        self.name = srvlistentry.name
        self.ipaddrs = srvlistentry.addresses
        self.keypair = srvlistentry.key_name
        self.flavor = srvlistentry.flavor["original_name"]
        self.image = srvlistentry.image.id
        self.vols = srvlistentry.attached_volumes
        return self
    def collectinfo2(self, ostackconn):
        "investigate image properties to find ssh user name"
        if not self.image:
            if not self.vols:
                return self
            volinfo = ostackconn.volume.get_volume(self.vols[0]["id"])
            vmeta = volinfo.volume_image_metadata
            if not vmeta or not 'image_id' in vmeta:
                return self
            self.image = vmeta.get('image_id')
        img = ostackconn.image.get_image(self.image)
        if "image_original_user" in img.properties:
            self.usernm = img.properties["image_original_user"]
        else:
            distro = None
            if "os_distro" in img.properties:
                distro = img.properties["os_distro"]
            # FIXME: Should we really guess image user names based on image name?
            # ubuntu
            if img.name[:6] == "Ubuntu" or img.name[:6] == "ubuntu" or distro == "ubuntu":
                self.usernm = "ubuntu"
            # we could do others ...
        return self

    def __str__(self):
        "string representation for debugging"
        return f"uid={self.uid}, name={self.name}, ipaddrs={self.ipaddrs}, " \
		f"keypair={self.keypair}, flavor={self.flavor}, image={self.image}, " \
		f"usernm={self.usernm}"

def collect_servers(ostackconn, collectfull = False):
    """Uses ostackconn to get server list and returns a list of
       OStackServer objects. collectfull controls whether we also
       do image API calls to get user names."""
    servers = []
    for srv in ostackconn.compute.servers():
        if srv.status != "ACTIVE":
            continue
        osrv = OStackServer()
        osrv.collectinfo(srv)
        if collectfull:
            osrv.collectinfo2(ostackconn)
        servers.append(osrv)
    return servers

def main(argv):
    "main entry point for testing"
    cloud = None
    if "OS_CLOUD" in os.environ:
        cloud = os.environ["OS_CLOUD"]
    if len(argv) and argv[0][:10] == "--os-cloud":
        if len(argv[0]) > 10 and argv[0][10] == "=":
            cloud = argv[0][11:]
        else:
            cloud = argv[1]
    if not cloud:
        print("You need to have OS_CLOUD set or pass --os-cloud=CLOUD.", file=sys.stderr)
    conn = openstack.connect(cloud = cloud, timeout=24)
    servers = collect_servers(conn, True)
    #servers = collect_servers(conn)
    for srv in servers:
        print(srv)

if __name__ == "__main__":
    main(sys.argv[1:])
