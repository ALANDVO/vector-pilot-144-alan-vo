"""Lazy module loader for cadgen submodules."""

import importlib
import sys
from types import ModuleType
from typing import Any


class LazyModule:
    """Lazily load a module on first attribute access."""

    def __init__(self, name: str):
        self._name = name
        self._module: ModuleType | None = None

    def _load(self) -> ModuleType:
        if self._module is None:
            self._module = importlib.import_module(self._name)
            sys.modules[self._name] = self._module
        return self._module

    def __getattr__(self, item: str) -> Any:
        return getattr(self._load(), item)

    def __dir__(self) -> list[str]:
        return dir(self._load())

