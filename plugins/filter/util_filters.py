"""Various utility filters."""

from collections.abc import Mapping

import ansible.errors

try:
    AnsibleTypeError = ansible.errors.AnsibleTypeError  # type: ignore
except AttributeError:
    AnsibleTypeError = ansible.errors.AnsibleFilterTypeError


def dict2tuple(dictionary):
    """Convert a dictionary to a list of (key, value) tuples."""
    if not isinstance(dictionary, Mapping):
        raise AnsibleTypeError(
            f"dict2tuple requires a dictionary, got {type(dictionary)} instead."
        )
    return [(key, value) for key, value in dictionary.items()]


deb_architectures = {
    "armv6l": "armhf",
    "armv7l": "armhf",
    "aarch64": "arm64",
    "x86_64": "amd64",
    "i386": "i386",
}


def deb_architecture(ansible_architecture):
    """Translate the ansible architecture string to common debian architecture."""
    return deb_architectures.get(ansible_architecture, "unknown")


def next_subids(subids, username, count=65536):
    """Get the next available subid record."""
    records = []
    for line in subids.split("\n"):
        line = line.strip()
        if line == "":
            continue
        (subid_username, base_id, length) = line.split(":")
        if username == subid_username:
            return f"{username}:{base_id}:{length}"
        base_id = int(base_id)
        length = int(length)
        records.append((base_id, length))

    records = sorted(records, key=lambda item: item[1])
    max_base_id = 0
    last_id = 0
    last_length = 0
    gaps = []
    for base_id, length in records:
        expected_base = last_id + last_length
        if expected_base != 0 and (expected_base < base_id):
            gap_length = base_id - expected_base
            gaps.append((expected_base, gap_length))

        max_base_id = max(max_base_id, base_id)
        last_id = base_id
        last_length = length

    gaps.append((last_id + last_length, count))

    for gap in gaps:
        if gap[1] >= count:
            return f"{username}:{gap[0]}:{count}"

    # In theory, this line is never reached
    raise ValueError("Could not determine next sub id")


def set_uid_gid(config_dict, ansible_facts, username):
    return {
        **config_dict,
        "uid": ansible_facts["getent_passwd"][username][1],
        "gid": ansible_facts["getent_passwd"][username][2],
    }


class FilterModule:
    """Utility filters."""

    def filters(self):
        """Get the filter name to method mapping."""
        return {
            "deb_architecture": deb_architecture,
            "dict2tuple": dict2tuple,
            "next_subids": next_subids,
            "set_uid_gid": set_uid_gid,
        }
