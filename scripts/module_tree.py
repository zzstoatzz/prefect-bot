"""not sure what to do with this yet, but it renders a tree of modules and their functions and classes"""

import importlib
import inspect
import pkgutil
from collections import OrderedDict
from typing import Any


def get_module_tree(package_name: str) -> dict[str, dict[str, Any]]:
    package = importlib.import_module(package_name)
    package_path = package.__path__[0]
    module_cache: dict[str, Any] = {}

    def walk_package(package_path: str, prefix: str) -> dict[str, dict[str, Any]]:
        module_tree: dict[str, dict[str, Any]] = OrderedDict()
        for importer, module_name, ispkg in pkgutil.iter_modules([package_path]):
            if any(module_name.startswith(p) for p in ["_", "beta", "cli"]):
                continue  # Skip private modules

            full_name = f"{prefix}.{module_name}" if prefix else module_name
            if full_name in module_cache:
                module = module_cache[full_name]
            else:
                try:
                    module = importlib.import_module(full_name)
                    module_cache[full_name] = module
                except ImportError:
                    continue

            # Get only public functions and classes defined in the module
            functions = {
                name: func
                for name, func in inspect.getmembers(module, inspect.isfunction)
                if not name.startswith("_") and func.__module__ == full_name
            }
            classes = {
                name: cls
                for name, cls in inspect.getmembers(module, inspect.isclass)
                if not name.startswith("_") and cls.__module__ == full_name
            }

            module_tree[full_name] = {
                "functions": {
                    name: str(inspect.signature(func))
                    for name, func in functions.items()
                },
                "classes": {
                    name: [
                        param.name
                        for param in inspect.signature(cls.__init__).parameters.values()
                        if param.name != "self"
                        and param.default == inspect.Parameter.empty
                    ]
                    for name, cls in classes.items()
                },
            }

            if ispkg:
                module_tree.update(
                    walk_package(f"{package_path}/{module_name}", full_name)
                )
        return module_tree

    return walk_package(package_path, package_name)


def print_module_tree(tree: dict[str, dict[str, Any]], indent: int = 0) -> None:
    for module, content in tree.items():
        print(" " * indent + module)
        if "functions" in content:
            for func_name, func_sig in content["functions"].items():
                print(" " * (indent + 2) + f"{func_name}{func_sig}")
        if "classes" in content:
            for class_name, init_args in content["classes"].items():
                init_args_str = ", ".join(init_args)
                print(" " * (indent + 2) + f"{class_name}({init_args_str})")


if __name__ == "__main__":
    import sys

    module_name = sys.argv[1] if len(sys.argv) > 1 else "raggy"
    tree: dict[str, dict[str, Any]] = get_module_tree(module_name)
    print_module_tree(tree)
