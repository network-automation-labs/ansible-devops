from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

from ansible_collections.network_automation_labs.devops.plugins.module_utils.common import ActionPluginMixin, list_action_plugins
from ansible_collections.network_automation_labs.devops.plugins.module_utils.crypto import CryptoPluginMixin

class ActionModule(CryptoPluginMixin, ActionPluginMixin, ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        result["changed"] = False
        _, module_args = self.validate_argument_spec(
            argument_spec={
                "path": {"type": "str", "required": True},
                "csr_path": {"type": "str", "required": False},
                "csr_content": {"type": "str", "required": False},
                "acme_directory": {"type": "str", "required": True},
                "acme_account_email": {"type": "str", "required": True},
                "acme_account_key": {"type": "str", "required": True},
                "dns_provider": {"type": "dict", "required": True},
            },
            required_one_of=[["csr_path", "csr_content"]],
        )
        num_providers = len(module_args["dns_provider"])
        if num_providers > 1:
            raise AnsibleActionFail(f"Got {num_providers} dns providers, but only one dns_provider can be given.")

        dns_provider = next(iter(module_args["dns_provider"].keys()))

        dns_providers = [plugin.removeprefix("dns_provider_") for plugin in list_action_plugins(lambda action_plugin: action_plugin.startswith("dns_provider_"))]
        if dns_provider not in dns_providers:
            raise AnsibleActionFail(f"Got invalid dns provider {dns_provider} choose one of {dns_providers}")

        dns_provider_options = module_args["dns_provider"][dns_provider]

        # 1. Load existing certificate
        certificate_content, loaded = self.load_file_if_exists(task_vars, module_args["path"])
        certificate = None
        if loaded and certificate_content is not None:
            certificate = self.run_local_module(
                "community.crypto.x509_certificate_info",
                task_vars,
                content=certificate_content,
                valid_at={"month": "+30d"}
            )

        # 2. Load signing request
        csr_content = self.load_or_content(task_vars, module_args["csr_path"], module_args["csr_content"])
        if csr_content is None:
            result["failed"] = True
            result["msg"] = "Empty certificate sigining request. Provide valid csr_path or csr_content."
            return result

        csr = self.run_local_module(
            "community.crypto.openssl_csr_info",
            task_vars,
            content=csr_content,
        )

        # 3. Check if needs re-signing
        if certificate is None or not certificate["valid_at"]["month"] or csr["subject_alt_name"] != certificate["subject_alt_name"]:
            self.display_changed("Certificate needs to be re-signed.")
            # 4. Generate challenge
            dns_challenge = self.run_remote_module(
                "community.crypto.acme_certificate",
                task_vars,
                acme_version=2,
                terms_agreed=True,
                acme_directory=module_args["acme_directory"],
                challenge="dns-01",
                account_email=module_args["acme_account_email"],
                account_key_content=module_args["acme_account_key"],
                csr_content=csr_content,
                fullchain_dest=module_args["path"],
                force=True,
            )

            # collect the TXT records
            txt_records = [{"name": f"{name}.", "values": data, "mode": "subset"} for name, data in dns_challenge["challenge_data_dns"].items()]

            # 5. Set challenge TXT records
            self.run_action_plugin(
                f"network_automation_labs.devops.dns_provider_{dns_provider}",
                task_vars,
                state="present",
                type="TXT",
                records=txt_records,
                **dns_provider_options,
            )

            # 6. Wait for DNS records to become available
            self.run_local_module(
                "community.dns.wait_for_txt",
                task_vars,
                records=txt_records,
                # TODO: Remove this when my home dns is fixed
                always_ask_default_resolver=False,
                server=["1.1.1.1"],
            )
            # 7. Perform challenge
            self.run_remote_module(
                "community.crypto.acme_certificate",
                task_vars,
                acme_version=2,
                terms_agreed=True,
                acme_directory=module_args["acme_directory"],
                challenge="dns-01",
                account_email=module_args["acme_account_email"],
                account_key_content=module_args["acme_account_key"],
                csr_content=csr_content,
                fullchain_dest=module_args["path"],
                data=dns_challenge,
                force=True,
            )
            result["changed"] = True

            # 8. Cleanup
            self.run_action_plugin(
                f"network_automation_labs.devops.dns_provider_{dns_provider}",
                task_vars,
                state="absent",
                type="TXT",
                records=txt_records,
                **dns_provider_options,
            )

        return result
