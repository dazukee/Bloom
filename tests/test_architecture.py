"""Checks that keep the project's structure honest.

1. Logic modules never import customtkinter or tkinter, so they can be
   tested without a window.
2. Every public function in a logic module has a docstring (its contract).
3. Every screen module imports cleanly.
"""

import ast
import importlib
import inspect
import pkgutil
from pathlib import Path

import pytest

import tracker.ui

TRACKER_DIR = Path(__file__).resolve().parent.parent / "tracker"
LOGIC_MODULES = sorted(p.stem for p in TRACKER_DIR.glob("*.py") if p.stem != "__init__")
GUI_PACKAGES = {"customtkinter", "tkinter", "PIL"}


def imported_packages(path: Path) -> set[str]:
    """Return the top-level names of every package a Python file imports."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_logic_modules_found():
    assert {"auth", "bmi", "cycle", "insights", "storage"} <= set(LOGIC_MODULES)


@pytest.mark.parametrize("module_name", LOGIC_MODULES)
def test_logic_module_does_not_import_gui(module_name):
    path = TRACKER_DIR / f"{module_name}.py"
    assert imported_packages(path).isdisjoint(GUI_PACKAGES)


@pytest.mark.parametrize("module_name", LOGIC_MODULES)
def test_every_public_function_has_a_contract(module_name):
    module = importlib.import_module(f"tracker.{module_name}")
    for name, function in inspect.getmembers(module, inspect.isfunction):
        if function.__module__ == module.__name__ and not name.startswith("_"):
            assert inspect.getdoc(function), f"{module_name}.{name} has no docstring"


@pytest.mark.parametrize(
    "module_name", sorted(m.name for m in pkgutil.iter_modules(tracker.ui.__path__))
)
def test_screen_module_imports(module_name):
    importlib.import_module(f"tracker.ui.{module_name}")
