#!/usr/bin/python
# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase

from ansible_collections.network_automation_labs.devops.plugins.module_utils.common import ActionPluginMixin
from ansible_collections.network_automation_labs.devops.plugins.module_utils.crypto import CryptoPluginMixin

class ActionModule(CryptoPluginMixin, ActionPluginMixin, ActionBase):
    def generate_new_key(self, task_vars, module_args):
        result = {}
        with self.tempfile(task_vars, module_args["path"]) as filename:
            result.update(self.run_local_module(
                "community.crypto.openssl_privatekey",
                task_vars,
                path=filename,
                size=module_args["size"],
                type=module_args["type"],
                curve=module_args["curve"],
                return_content=True,
            ))
            result["content"] = result["privatekey"]
        return result

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = {}
        self._task_vars = task_vars

        result = super().run(tmp, task_vars)
        result["changed"] = False
        _, module_args = self.validate_argument_spec(
            argument_spec={
                "path": {"type": "str", "required": True},
                "size": {"type": "int", "required": True},
                "type": {"type": "str", "required": True},
                "curve": {"type": "str", "required": True},
            },
        )
        content, loaded = self.load_or_run(task_vars, module_args, module_args["path"], self.generate_new_key)
        result["changed"] = not loaded
        result["private_key_content"] = content
        return result
