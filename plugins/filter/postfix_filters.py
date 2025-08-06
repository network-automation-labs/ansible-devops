"""Filter plugins for the postfix role."""

def postfix_relay_host(relay_dict: dict):
    relay_host = relay_dict["host"]
    try:
        relay_port = relay_dict["port"]
        if relay_port:
            return f"[{relay_host}]:{relay_port}"
    except KeyError:
        pass
    return f"[{relay_host}]"


class FilterModule(object):
    def filters(self):
        return {
            "postfix_relay_host": postfix_relay_host
        }
