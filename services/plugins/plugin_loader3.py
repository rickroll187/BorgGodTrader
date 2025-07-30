import importlib.util
import os

class PluginLoader:
    def __init__(self, plugins_dir="plugins"):
        self.plugins_dir = plugins_dir
        self.plugins = {}

    def load_plugins(self):
        for fname in os.listdir(self.plugins_dir):
            if fname.endswith(".py"):
                path = os.path.join(self.plugins_dir, fname)
                spec = importlib.util.spec_from_file_location(fname[:-3], path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                self.plugins[fname[:-3]] = mod

    def get_plugin(self, name):
        return self.plugins.get(name)