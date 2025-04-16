from typing import Any
from .types import ActionBaseProtocol

class CryptoPluginMixin(ActionBaseProtocol):
    _task_vars: dict

    @property
    def tls_vars(self) -> dict[str, Any]:
        if not hasattr(self, "_tls_vars"):
            inventory_hostname = self._task_vars["inventory_hostname"]
            host_vars = self._task_vars["hostvars"][inventory_hostname]
            if "tls_cert" in host_vars:
                self._tls_vars = host_vars["tls_cert"]
            else:
                self._tls_vars = {}
        return self._tls_vars
