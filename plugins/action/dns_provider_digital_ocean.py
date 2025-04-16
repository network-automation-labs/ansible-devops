from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

from ansible_collections.network_automation_labs.devops.plugins.module_utils.common import ActionPluginMixin
from ansible_collections.network_automation_labs.devops.plugins.module_utils.crypto import CryptoPluginMixin

class ActionModule(CryptoPluginMixin, ActionPluginMixin, ActionBase):
    def _record(self, task_vars, module_args, name, **options):
        return self.run_local_module(
            "community.digitalocean.digital_ocean_domain_record",
            task_vars,
            state=module_args["state"],
            record_id=0,
            oauth_token=module_args["oauth_token"],
            domain=module_args["domain"],
            type=module_args["type"],
            name=name,
            ttl=module_args["ttl"],
            **options
        )

    def _lookup_records(self, task_vars, module_args, domain):
        return self.run_local_module(
            "community.digitalocean.digital_ocean_domain_record_info",
            task_vars,
            oauth_token=module_args["oauth_token"],
            type=module_args["type"],
            domain=domain,
        )

    def run_txt(self, result, task_vars):
        _, module_args = self.validate_argument_spec(
            argument_spec={
                "type": {"type": "str", "required": True},
                "state": {"type": "str", "choices": ["present", "absent"], "required": True},
                "records": {"type": "list", "elements": "dict", "required": True},
                "oauth_token": {"type": "str", "required": True},
                "domain": {"type": "str", "required": True},
                "ttl": {"type": "int", "required": False, "default": 60}
            },
        )

        for record in module_args["records"]:
            if module_args["state"] == "present":
                for data in record["values"]:
                    self._record(task_vars, module_args, record["name"], force_update=True, data=data)
                    self.display_changed(f"Created TXT record {record['name']}: {data}")
            else:
                lookup = self._lookup_records(task_vars, module_args, record["name"])
                for record in lookup["data"]["records"]:
                    self._record(task_vars, module_args, record["name"], record_id=record["id"])
                    self.display_changed(f"Removed TXT record {record['id']}: {record['name']}")

        return result

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)

        result["changed"] = False
        record_type = self._task.args.get("type", None) # type: ignore
        if record_type == "TXT":
            return self.run_txt(result, task_vars)

        raise AnsibleActionFail(f"{record_type} is not a valid DNS record type.")
