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

"""Routines to determine the best IP address that we can reach,
   see preferred_ip() documentation."""

#import os
import sys
import json
import requests
#import openstack

Subnet_Names = {}
Subnet_IDs = {}

def fill_subnetmap(conn):
    "Create maps for subnet ID->name and name->ID"
    #global Subnet_Names, Subnet_IDs
    for subnet in conn.network.subnets():
        Subnet_Names[subnet.id] = subnet.name
        Subnet_IDs[subnet.name] = subnet.id


class OwnNetInfo:
    """The subnets we are connected to"""
    def __init__(self, conn):
        self.subnets = []
        self.subnet_names = []
        try:
            ans = requests.get("http://169.254.169.254/openstack/latest/network_data.json",
                                timeout=3)
        except:
            return
        if not ans.ok:
            return
        fill_subnetmap(conn)
        jnet = json.loads(ans.text)
        for net in jnet["networks"]:
            net_id = net["network_id"]
            try:
                netinfo = conn.network.get_network(net_id)
            except:
                print(f"Could not retrieve info for network {net_id}", file=sys.stderr)
                continue
            for snet in netinfo.subnet_ids:
                self.subnets.append(snet)
                self.subnet_names.append(Subnet_Names[snet])


class Router:
    """Class to hold router properties along with connected subnet IDs."""
    def __init__(self, conn, robj, debug=False):
        "c'tor, creating list of connected subnets"
        self.router = robj
        self.subnets = []
        self.subnet_names = []
        filters = {}
        filters['device_id'] = robj.id
        for port in conn.network.ports(**filters):
            if port.device_owner == "network_router:gateway":
                continue
            for ip_spec in port.fixed_ips:
                snetid = ip_spec.get('subnet_id')
                if debug:
                    print(f"Router {robj.name} connected to subnet {Subnet_Names[snetid]}",
                          file=sys.stderr)
                self.subnets.append(snetid)
                self.subnet_names.append(Subnet_Names[snetid])
    def is_connected(self, subnet):
        "is subnet (id or name) connected to our router?"
        if subnet in self.subnets:
            return True
        if subnet in self.subnet_names:
            return True
        return False

PrivNets = ("192.168.0.0/16", "172.16.0.0/12", "10.0.0.0/8", "100.64.0.0/10", "169.254.0.0/16" )

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

def is_public(ipstr):
    "Return True if the ipstr is not private"
    for privnet in PrivNets:
        if ip_in_cidr(ipstr, privnet):
            return False
    return True

def ownnet_and_routers(conn, debug=False):
    """Check for own connectivity and connected routers.
        If we are on a cloud, we may have internal connections,
        and need to look at routers to understand them.
        Return OwnNetInfo and Router list."""
    ownnet = OwnNetInfo(conn)
    if debug:
        print(f"We are connected to subnets {ownnet.subnet_names}", file=sys.stderr)
    if not ownnet.subnets:
        return(None, (None,))
    routers = []
    for router in conn.network.routers():
        rtr = Router(conn, router, debug)
        # filter only routers connected to us
        for subnet in ownnet.subnets:
            if rtr.is_connected(subnet):
                routers.append(rtr)
                break
    if debug:
        print(f"We are connected to routers {list(map(lambda x: x.router.name, routers))}",
                file=sys.stderr)
    return ownnet, routers

def extract_ip(ipnets, iptype, version=4, debug=False):
    "extract the ip address"
    for netobj in ipnets:
        if netobj['version'] == version and netobj['OS-EXT-IPS:type'] == iptype:
            ipaddr = netobj['addr']
            if debug:
                print(f"{ipaddr}", file=sys.stderr)
            return ipaddr
    return None

def get_ip(ipaddrs, iptype, version=4, debug=False):
    """Iterate over networks in ipaddrs to find IP that matches
       iptype ('fixed' or 'floating') and ip version.
       Return none if not found.
    """
    for netnm in ipaddrs:
        ipaddr = extract_ip(ipaddrs[netnm], iptype, version, debug)
        if ipaddr:
            return ipaddr
    return None

def get_floating_ip(ipaddrs, debug=False):
    "Return floating IPv4 address if it exists"
    return get_ip(ipaddrs, "floating", 4, debug)


def preferred_ip(ipaddrs, ownnet, routers, debug=False):
    """Pick the best ipaddr reachable by us (ownnet) via routers:
        * If we are in the smae subnet, use the fixed IPv4 address
        * If we find a fixed IP that can be reached by one router hop, use it
        * If we find a public floating IP, use it
        * If we find a public fixed IP, ipaddrs,
        * Otherwise return None
    """
    if ownnet and ownnet.subnets:
        # same subnet
        for netnm in ipaddrs:
            if netnm in ownnet.subnet_names:
                ipaddr = extract_ip(ipaddrs[netnm], 'fixed', 4, debug)
                if ipaddr:
                    return ipaddr
        # connected via router (single hop)
        for netnm in ipaddrs:
            for router in routers:
                if router.is_connected(netnm):
                    ipaddr = extract_ip(ipaddrs[netnm], 'fixed', 4, debug)
                    if ipaddr:
                        return ipaddr
    # floating IP
    ipaddr = get_floating_ip(ipaddrs, debug)
    if ipaddr:
        return ipaddr
    # fixed ip with public address
    for netnm in ipaddrs:
        ipaddr = extract_ip(ipaddrs[netnm], 'fixed', 4, debug)
        if ipaddr:
            if is_public(ipaddr):
                return ipaddr
    return None
