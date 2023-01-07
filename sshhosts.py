#!/usr/bin/env python3
#
# sshhosts.py
#
# incomplete but sufficient parser and generator for ssh config files
# with lists of hosts
#
# (c) Kurt Garloff <kurt@garloff.de>, 01/2023
# SPDX-License-Identifier: Apache-2.0

import os, sys

class Host:
    def __init__(self):
        self.name = None
        self.hostname = None
        self.idFile = None
        self.user = None
        self.fwdAgent = False
        self.misc = ""
        
    def parsecfg(self, lines):
        found = False
        parsed = 0
        for ln in lines:
            ln = ln.rstrip("\r\n")
            parsed += 1
            if ln[:5] == "Host ":
                if found:
                    return parsed - 1
                nm = ln[5:]
                if self.name and self.name != nm:
                    continue
                found = True
                self.name = nm
            elif found:
                cont = ln.lstrip("  ")
                if cont[:9] == "Hostname ":
                    self.hostname = cont[9:]
                elif cont[:13] == "ForwardAgent ":
                    if cont[13:16] == "yes":
                        self.fwdAgent = True
                elif cont[:13] == "IdentityFile ":
                    self.idFile = cont[13:]
                elif cont[:5] == "User ":
                    self.user = cont[5:]
                else:
                    if cont:
                        self.misc = self.misc + "  " + cont + "\n"
        if found:
            return parsed
        else:
            return 0
            
    def __str__(self):
        out = f"Host {self.name}\n  Hostname {self.hostname}"
        if self.user:
            out += f"\n  User {self.user}"
        if self.idFile:
            out += f"\n  IdentityFile {self.idFile}"
        if self.fwdAgent:
            out += f"\n  ForwardAgent yes"
        if self.misc != "":
            out += f"\n{self.misc}"
        return out

def readfile(fnm):
    hosts = []
    processed = 0
    lns = open(fnm, "r").readlines()
    while processed < len(lns):
        host = Host()
        noln = host.parsecfg(lns[processed:])
        if not noln:
            break
        hosts.append(host)
        processed += noln
    return hosts

def main(argv):
    for fnm in argv:
        print(f"#FILE: {fnm}")
        hosts = readfile(fnm)
        for host in hosts:
            print("%s\n" % host)

if __name__ == "__main__":
    main(sys.argv[1:])
