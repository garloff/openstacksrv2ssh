#!/usr/bin/env python3
# vim: set ts=4 sw=4 et:
#
# sshhosts.py
#
# incomplete but sufficient parser and generator for ssh config files
# with lists of hosts
#
# (c) Kurt Garloff <kurt@garloff.de>, 01/2023
# SPDX-License-Identifier: Apache-2.0

"""sshhosts contains class SSHhost which parses and outputs again
   some of the Host attributes from ssh config files.
   collect_sshhosts() returns list of SSHhost objects parsed
   from the passed ssh config file."""

#import os
import sys

class SSHhost:
    "class to parse and output some ssh Host settings"
    def __init__(self):
        "default c'tor"
        self.name = None
        self.hostname = None
        self.id_file = None
        self.user = None
        self.fwd_agent = False
        self.misc = ""

    def parsecfg(self, lines):
        """Parse the passed lines for a Host entry. Uses first Host entry
           found, unless self.name is already set in which case it looks
           for a Host entry matching it. Stops parsing on next entry.
           Returns number of lines advanced or 0 if nothing was found."""
        found = False
        parsed = 0
        for line in lines:
            line = line.rstrip("\r\n")
            parsed += 1
            if line[:5] == "Host ":
                if found:
                    return parsed - 1
                name = line[5:]
                if self.name and self.name != name:
                    continue
                found = True
                self.name = name
            elif found:
                cont = line.lstrip("  ")
                if cont[:9] == "Hostname ":
                    self.hostname = cont[9:]
                elif cont[:13] == "ForwardAgent ":
                    if cont[13:16] == "yes":
                        self.fwd_agent = True
                elif cont[:13] == "IdentityFile ":
                    self.id_file = cont[13:]
                elif cont[:5] == "User ":
                    self.user = cont[5:]
                else:
                    if cont:
                        self.misc = self.misc + "  " + cont + "\n"
        if found:
            return parsed
        return 0

    def __str__(self):
        "String output in ssh config file format"
        out = f"Host {self.name}\n  Hostname {self.hostname}"
        if self.user:
            out += f"\n  User {self.user}"
        if self.id_file:
            out += f"\n  IdentityFile {self.id_file}"
        if self.fwd_agent:
            out += "\n  ForwardAgent yes"
        if self.misc != "":
            out += f"\n{self.misc}"
        return out

def collect_sshhosts(fnm):
    "Process ssh config file with filename fnm. Returns a list of SSHhost objects."
    hosts = []
    processed = 0
    lns = open(fnm, "r", encoding='UTF-8').readlines()
    while processed < len(lns):
        host = SSHhost()
        noln = host.parsecfg(lns[processed:])
        if not noln:
            break
        hosts.append(host)
        processed += noln
    return hosts

def main(argv):
    "Entry point for testing"
    for fnm in argv:
        print(f"#FILE: {fnm}")
        hosts = collect_sshhosts(fnm)
        for host in hosts:
            print(f"{host}\n")

if __name__ == "__main__":
    main(sys.argv[1:])
