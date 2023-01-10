# openstacksrv2ssh

Query OpenStack cloud servers and create ssh config files for them

## All your OpenStack VMs at your fingertips

If you have a number of VMs running in a number of OpenStack projects
or clouds, it may quickly become tedious to access them with ssh/scp,
looking up (floating) IPs and then copy-pasting the addresses and
remembering user names and SSH keypairs associated with them.

Admins may add server aliases (Hosts) to their `~/.ssh/config` file, so
tab completion works and IP addresses, user names, key pair names are
stored.

`openstacksrv2ssh.py` automates the creation of Host entries by asking
the OpenStack API of all clouds that are configured in your `clouds.yaml` /
`secure.yaml` files.

### Quick Start

* Ensure your cloud projects are all listed in `~/.config/openstack/clouds.yaml`
* Ensure that keypairs files are stored in `~/.ssh/$KEY_NAME.pem`
* Have an `Include openstacksrv2ssh.sshcfg` statement before the (manually
  managed) `Host` entries in your `~/.ssh/config` file
* Run `openstacksrv2ssh.py -a` regularly or `openstacksrv2ssh.py $OS_CLOUD`
  prior to using ssh or scp.

## Goodies

* When run on a VM in a cloud, locally accessible IP addresses from other
  servers are being detected (in same subnet or connected via a single
  hop router) and used in preference over a floating IP.

## Limitations and TODOs

* The names of the host aliases are currently hardcoded as `$OS_CLOUD-$VMNAME`,
  which we may make configurable later.
* We currently exclusively look for IPv4 IP addresses; we may allow IPv6
  later.
* The .sshcfg files are overwritten and custom changes have a limited chance
  to survive.
