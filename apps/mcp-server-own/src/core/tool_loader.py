import importlib
import inspect
import pkgutil

def load_tools(package_name: str):
    tools = []
    package = importlib.import_module(package_name)

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_name}")

        for _, obj in inspect.getmembers(module):
            if callable(obj) and hasattr(obj, "__mcp_tool__"):
                tools.append(obj)

    return tools
