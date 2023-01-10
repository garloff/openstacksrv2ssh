#!/usr/bin/env python3
# vim: set ts=4 sw=4 et:
# 
# ipconnected.py
#
# Find out whether there is a route to an IP address
# This works for pulic/floating IPs obviously
# For private IPs, only if they are in the same subnet
# or subnets connected to the same router.
#
# (c) Kurt Garloff <kurt@garloff.de>, 1/2023
# SPDX-License-Identifier: Apache-2.0

import os
import requests
import json
import openstack

Subnet_Names = {}
Subnet_IDs = {}

def fill_subnetmap(conn):
    global Subnet_Names, Subnet_IDs
    for subnet in conn.network.subnets():
        Subnet_Names[subnet.id] = subnet.name
        Subnet_IDs[subnet.name] = subnet.id
    

class OwnNetinfo:
    """The subnets we are connected to"""
    def __init__(self, conn)
        self.subnets = []
        self.subnet_names = []
        try:
            ans = requests.get("http://169.254.169.254/openstack/latest/network_data.json", timeout=3)
        except:
            return self
        fill_subnetmap(conn)
        jnet = json.loads(ans)
        for net in jnet["networks"]:
            net_id = net["network_id"]
            netinfo = conn.network.get_network(net_id)
            for snet in netinfo.subnet_ids:
                self.subnets.append(snet)
                self.subnet_names.append(Subnet_Names(snet))


class Router:
    """Class to hold router properties along with connected subnet IDs."""
    def __init__(self, conn, robj):
        self.router = robj
        self.subnets = []
        self.subnet_names = []
        filters = {}
        filters['device_id'] == robj.id
        for port in conn.network.ports(filters):
            if port.device_owner == "network_router:gateway":
                continue
            for ip_spec in port.fixed_ips:
                snetid = ip_spec.get('subnet_id')
                self.subnets.append(snetid)
                self.subnet_names.append(Subnet_Names(snetid))
    def is_connected(self, subnet):
        if subnet in self.subnets:
            return True
        if subnet in self.subnet_names:
            return True
        return False

PrivNets = ("192.168.0.0/16", "172.16.0.0/12", "10.0.0.0/8")

def ip_to_int(ipstr):
    "32bit int from four octet IPv4 notation"
    val = 0
    for octet in ipstr.split("."):
        val *= 256
        val += int(octet)
    return val

def ip_in_cidr(ipstr, cidr):
    "Is ipstr in network cidr?"
    net, bits = cidr.split('/')
    mask = 0xffffffff ^ ((1 << (32-int(bits))) - 1)
    #print(f"{ipstr}:{hex(ip_to_int(ipstr))} & {hex(mask)} = "
    #   f"{hex(ip_to_int(ipstr)&mask)} vs {net}:{hex(ip_to_int(net))}")
    if ip_to_int(net) == ip_to_int(ipstr) & mask:
        return True
    return False 

def ownnet_and_routers(conn):
    """Check for own connectivity and connected routers.
        If we are on a cloud, we may have internal connections,
        and need to look at routers to understand them.
        Return OwnNetInfo and Router list."""
    ownnet = OwnNetInfo(conn)
    if not ownnet.subnets:
        return(None, (None,))
    routers = []
    for router in conn.network.routers():
        rtr = Router(conn, router)
        # filter only routers connected to us
        for subnet in ownnet.subnets:
            if rtr.is_connected(subnet):
                routers.append(rtr)
                break
    return ownnet, routers


def PreferredIP(ipaddrs, ownnet, routers):
    """Pick the best ipaddr reachable by us (ownnet) via routers:
        * If we are in the smae subnet, use the fixed IPv4 address
        * If we find a fixed IP that can be reached by one router hop, use it
        * If we find a public floating IP, use it
        * If we find a public fixed IP, ipaddrs,         * Otherwise return None
    """
        
    
