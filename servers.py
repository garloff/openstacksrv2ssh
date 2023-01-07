#!/usr/bin/env python3
#
# servers.py
#
# Collect information from OpenStack to create information
# for creating ssh config Host entries
#
# (c) Kurt Garloff <kurt@garloff.de>
# SPDX-License-Identifier: Apache-2.0

import sys, os
import openstack

class OStackServer:
    def __init__(self):
        self.uid = None
        self.name = None
        self.ipaddrs = []
        self.keypair = None
        self.flavor = None
        self.image = None
        self.usernm = None
    def collectinfo(self, srvlistentry):
        if srvlistentry.status != "ACTIVE":
            return False
        self.uid = srvlistentry.id
        self.name = srvlistentry.name
        self.ipaddrs = srvlistentry.addresses
        self.keypair = srvlistentry.key_name
        self.flavor = srvlistentry.flavor["original_name"]
        self.image = srvlistentry.image.id
        return True
    def collectinfo2(self, ostackconn):
        if not self.image:
            return
        img = ostackconn.image.get_image(self.image)
        if "image_original_user" in img.properties:
            self.usernm = img.properties["image_original_user"]
        # TODO: Guess image username based on image name
    def __str__(self):
        return f"uid={self.uid}, name={self.name}, ipaddrs={self.ipaddrs}, keypair={self.keypair}, " \
                f"flavor={self.flavor}, image={self.image}, usernm={self.usernm}"

def collectServers(ostackconn, collectfull = False):
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
    servers = collectServers(conn, True)
    #servers = collectServers(conn)
    for srv in servers:
        print(srv)

if __name__ == "__main__":
    main(sys.argv[1:])


