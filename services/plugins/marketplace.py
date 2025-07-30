import os
import importlib.util
import sys

class PluginMarketplace:
    """
    Simple plugin loader with dynamic import and basic sandboxing.
    """
    def __init__(self, plugins_dir="plugins"):
        self.plugins_dir = plugins_dir
        os.makedirs(plugins_dir, exist_ok=True)

    def list_plugins(self):
        return [f for f in os.listdir(self.plugins_dir) if f.endswith(".py")]

    def load_plugin(self, plugin_name):
        plugin_path = os.path.join(self.plugins_dir, plugin_name)
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin_name] = module
        spec.loader.exec_module(module)
        return module

    def sandbox_plugin(self, plugin_code):
        # For now, just execute in a restricted dict
        exec(plugin_code, {"__builtins__": {}})