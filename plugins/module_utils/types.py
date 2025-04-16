from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ansible.playbook.task import Task
    from ansible.playbook.play_context import PlayContext
    from ansible.plugins.loader import PluginLoader
    from ansible.template import Templar
    from ansible.parsing.dataloader import DataLoader

class SharedLoaderObj(Protocol):
    @property
    def action_loader(self) -> "PluginLoader": ...

class ActionBaseProtocol(Protocol):
    _task: "Task"
    _shared_loader_obj: "SharedLoaderObj"
    _play_context: "PlayContext"
    _templar: "Templar"
    _loader: "DataLoader"

