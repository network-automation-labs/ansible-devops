from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible_collections.network_automation_labs.devops.plugins.module_utils.common import (
    ActionPluginMixin,
)
from ansible_collections.network_automation_labs.devops.plugins.module_utils.crypto import (
    CryptoPluginMixin,
)

display = Display()


class ActionModule(CryptoPluginMixin, ActionPluginMixin, ActionBase):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = {}
        self._task_vars = task_vars

        results = super().run(tmp, task_vars)
        results["changed"] = False

        _, module_args = self.validate_argument_spec(
            argument_spec={
                "private_key_content": {"type": "str", "required": True},
                "options": {"type": "dict", "required": False, "default": {}},
            },
        )
        with self.tempfile(task_vars) as filename:
            csr_results = self.run_local_module(
                "community.crypto.openssl_csr",
                task_vars,
                path=filename,
                privatekey_content=module_args["private_key_content"],
                return_content=True,
                **module_args["options"],
            )
            results["content"] = csr_results["csr"]

        return results
