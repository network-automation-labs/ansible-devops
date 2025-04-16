import base64
from typing import Any
from ansible.errors import AnsibleError
from ansible.plugins.loader import connection_loader
from ansible.utils.display import Display
from ansible import constants as C


from contextlib import contextmanager
from functools import wraps
import os
from os import path
from tempfile import mkstemp

from .types import ActionBaseProtocol

display = Display()


def list_action_plugins(filter_predicate = None):
    filenames = os.listdir(path.join(path.dirname(__file__), "..", "action"))
    filenames = filter(lambda filename: filename.endswith(".py"), filenames)
    action_plugins = [filename.removesuffix(".py") for filename in filenames]

    if filter_predicate:
        action_plugins = filter(filter_predicate, action_plugins)
    return action_plugins

class RunFailedError(AnsibleError):
    def __init__(self, msg: str, result: dict):
        super().__init__(msg)
        self.result = result


def raise_on_failure(wrapped):
    @wraps(wrapped)
    def wrapper(*args, **kwargs):
        result = wrapped(*args, **kwargs)
        if result is not None and "failed" in result:
            raise RunFailedError(result.get("msg", "Error occurred"), result)
        return result
    return wrapper

class ActionPluginMixin(ActionBaseProtocol):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = {}
        self._task_vars = task_vars
        self.host_label = self._task_vars["inventory_hostname"]
        return super().run(tmp, task_vars) # type: ignore

    def display_changed(self, msg):
        display.display(f"[{self.host_label}] {msg}", C.COLOR_CHANGED) # type: ignore

    def display_ok(self, msg):
        display.display(f"[{self.host_label}] {msg}", C.COLOR_UNCHANGED) # type: ignore

    @contextmanager
    def tempfile(self, task_vars, dest=None, dest_mode="600"):
        filepath = ""
        try:
            fd, filepath = mkstemp()
            os.close(fd)
            yield filepath
            if dest is not None:
                self.run_action_plugin(
                    "ansible.builtin.copy",
                    task_vars,
                    src=filepath,
                    dest=dest,
                    mode=dest_mode,
                )
        finally:
            if filepath:
                os.remove(filepath)

    @raise_on_failure
    def run_local_module(self, module_name: str, task_vars, **module_args) -> dict:
        old_connection = self._connection
        old_delegate = self._task.delegate_to
        self._task.delegate_to = "localhost"
        delegated_vars, _ = self._task._variable_manager.get_delegated_vars_and_hostname(self._templar, self._task, task_vars) # type: ignore
        task_vars = {**task_vars, **delegated_vars, "ansible_host": "localhost", "ansible_connection": "local"}
        self._connection = connection_loader.get("local", self._play_context, "/dev/null")
        result = self._execute_module( # type: ignore
            module_name,
            module_args=module_args,
            task_vars=task_vars,
        )
        self._task.delegate_to = old_delegate
        self._connection = old_connection
        return result

    @raise_on_failure
    def run_remote_module(self, module_name: str, task_vars, **module_args) -> dict:
        return self._execute_module( # type: ignore
            module_name,
            module_args=module_args,
            task_vars=task_vars,
        )


    @raise_on_failure
    def run_action_plugin(self, plugin_name, task_vars, **module_args) -> dict:
        new_task = self._task.copy()
        new_task.args = module_args
        plugin = self._shared_loader_obj.action_loader.get(
            plugin_name,
            task=new_task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj
        )
        return plugin.run(task_vars=task_vars)

    def load_file_if_exists(self, task_vars, remote_file_path, default_content=None) -> tuple[str|None, bool]:
        content = default_content
        result = self.run_remote_module(
            "ansible.builtin.stat",
            task_vars,
            path=remote_file_path,
        )
        loaded = False
        if result["stat"]["exists"]:
            result = self.run_remote_module(
                "ansible.builtin.slurp",
                task_vars,
                src=remote_file_path,
            )
            content = base64.b64decode(result["content"]).decode("utf-8")
            loaded = True
        return content, loaded

    def load_or_content(self, task_vars, remote_path, default_content)-> Any:
        content = default_content
        if remote_path is not None:
            content, _ = self.load_file_if_exists(task_vars, remote_path, default_content)
        return content

    def load_or_run(self, task_vars, module_args, remote_file_path, callback):
        content, loaded = self.load_file_if_exists(task_vars, remote_file_path)
        if not loaded:
            content = callback(task_vars, module_args)
        return content, loaded
