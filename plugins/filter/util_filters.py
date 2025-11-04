"""Various utility filters."""

from collections.abc import Mapping

from ansible.errors import AnsibleFilterTypeError


def dict2tuple(mydict):
    """Conver a dictionary to a list of (key, value) tuples."""
    if not isinstance(mydict, Mapping):
        raise AnsibleFilterTypeError(
            f"dict2tuple requires a dictionary, got {type(mydict)} instead."
        )
    return [(key, value) for key, value in mydict.items()]


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


class FilterModule:
    """Utility filters."""

    def filters(self):
        """Get the filter name to method mapping."""
        return {
            "deb_architecture": deb_architecture,
            "dict2tuple": dict2tuple,
        }
