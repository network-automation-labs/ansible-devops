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


class FilterModule:
    """Utility filters."""

    def filters(self):
        """Get the filter name to method mapping."""
        return {"dict2tuple": dict2tuple}
