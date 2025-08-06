"""NFT role rilters."""

from typing import Any

from ansible.errors import AnsibleFilterTypeError
from ansible.utils.display import Display
from netaddr import AddrFormatError, IPAddress

display = Display()

ACTIONS = {
    "accept",
    "drop",
}


def create_rule(rule_var: dict[str, Any]) -> str:
    """Create an nftables rule from a rule var.

    Args:
        rule (dict): The rule var to convert to an nftables rule string

    Returns:
        str: An nftables rule string for appending to a chain.

    """
    proto = rule_var.pop("proto", None)
    dport = rule_var.pop("dport", None)
    sport = rule_var.pop("sport", None)
    action = rule_var.pop("action", "").lower()

    if action not in ACTIONS:
        raise AnsibleFilterTypeError(
            f"{action} is not a valid action, must be one of {ACTIONS}"
        )

    rule = [
        "ct",
        "state",
        "new",
    ]

    for directive, value in rule_var.items():
        if directive == "comment":
            continue
        rule.extend([directive, value])

    if sport or dport:
        if not proto:
            raise AnsibleFilterTypeError(
                "Protocol must be specified when given source or destination port."
            )
        if sport:
            rule.extend([proto, "sport", sport])
        if dport:
            rule.extend([proto, "dport", dport])
    elif proto:
        rule.extend(["ip", "protocol", proto])

    rule.append(action)

    rule = map(str, rule)
    return " ".join(rule)


class ChainConfig:
    """A datastructure for organizing nftables rules."""

    def __init__(self, name):
        """Initialize the chain `name`."""
        self.name = name
        self._policy = None
        self.rules = []

    @property
    def policy(self):
        """Retrieve the chain's policy."""
        return self._policy

    @policy.setter
    def policy(self, policy):
        """Set the chain's policy.

        Args:
            policy (str): The policy (accept or drop)

        """
        if self._policy is not None:
            display.warning(
                f"Previous policy '{self._policy}' for nftables chain {self.name} redefined to {policy}"
            )
        self._policy = policy


def extract_config(hostvars):
    """Extract the nftables config from the host vars.

    This filter will iterate all the hostvars looking for any
    variable that ends with `_firewall_rules`. The associated
    rules are then appended to the configuration for the appropriate
    chain.

    Rules vars are in the form of:
        myhost_firewall_rules:
          - chain: input
            policy: accept
            rules:
                - {comment: "Some text comment", proto: "tcp", dport: 80, action: "ACCEPT"}
    """
    chains = {}
    for key in hostvars:
        if key.endswith("_firewall_rules"):
            for config in hostvars[key]:
                chain = config["chain"]
                chains.setdefault(chain, ChainConfig(config["chain"]))
                if "policy" in config:
                    chains[chain].policy = config["policy"]
                chains[chain].rules.extend(config.get("rules", []))
    return chains


def interfaces(hostvars, filter_names=None):
    """Get all of the ansible interface facts for all known interfaces."""
    filter_names = filter_names or []
    interface_names = [
        interface_name.replace("-", "_")
        for interface_name in hostvars["ansible_interfaces"]
        if interface_name != "lo"
    ]

    return [
        hostvars[f"ansible_{interface_name}"]
        for interface_name in sorted(interface_names)
        if interface_name not in filter_names
    ]


def broadcast_addresses(hostvars):
    """Get a list of broadcast addresses.

    Args:
        hostvars (dict): The hostvars for the desired host. E.g `hostvars[inventory_hostname]`

    Returns:
        list[netaddr.IPAddress]: A list of `netaddr.IPAddress` objects constructed from the
            broadcast address for all interfaces (not including lo). The interface list is
            constructed from the `hostvars['ansible_interfaces']` list of interface names.

    """
    addresses = {}

    for interface in interfaces(hostvars, filter_names=["lo"]):
        broadcast = interface.get("ipv4", {}).get("broadcast")
        if broadcast:
            try:
                addresses[interface["device"]] = IPAddress(broadcast)
            except AddrFormatError as ex:
                display.warning(str(ex))
    return addresses


class FilterModule:
    """Filters related to the `nft` role."""

    def filters(self):
        """Get the mapping of filter names to filter methods."""
        return {
            "nft_create_rule": create_rule,
            "nft_extract_config": extract_config,
            "nft_broadcast_addresses": broadcast_addresses,
            "nft_interfaces": interfaces,
        }
