import os
import importlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Loads and manages plugins from the plugins directory.
    Plugins can extend functionality without modifying core code.
    """

    def __init__(self, plugin_dir: str = None):
        self.plugin_dir = Path(plugin_dir) if plugin_dir else Path(__file__).parent / "installed"
        self.plugins: Dict[str, Any] = {}
        self.plugin_configs: Dict[str, Dict] = {}

    def load_plugins(self):
        """Load all plugins from the plugin directory."""
        if not self.plugin_dir.exists():
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created plugin directory: {self.plugin_dir}")
            return

        for item in self.plugin_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                self._load_plugin(item.name)
            elif item.suffix == ".py" and item.name != "__init__.py":
                self._load_plugin(item.stem)

        logger.info(f"Loaded {len(self.plugins)} plugins")

    def _load_plugin(self, plugin_name: str):
        """Load a single plugin by name."""
        try:
            # Try to import the plugin module
            module = importlib.import_module(f"services.plugins.installed.{plugin_name}")

            # Look for a Plugin class or setup function
            if hasattr(module, "Plugin"):
                self.plugins[plugin_name] = module.Plugin()
            elif hasattr(module, "setup"):
                self.plugins[plugin_name] = module.setup()
            else:
                self.plugins[plugin_name] = module

            # Load config if available
            if hasattr(module, "CONFIG"):
                self.plugin_configs[plugin_name] = module.CONFIG

            logger.info(f"Loaded plugin: {plugin_name}")

        except ImportError as e:
            logger.warning(f"Failed to import plugin {plugin_name}: {e}")
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")

    def unload_plugin(self, plugin_name: str):
        """Unload a plugin."""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            if hasattr(plugin, "cleanup"):
                plugin.cleanup()
            del self.plugins[plugin_name]
            self.plugin_configs.pop(plugin_name, None)
            logger.info(f"Unloaded plugin: {plugin_name}")

    def reload_plugin(self, plugin_name: str):
        """Reload a plugin."""
        self.unload_plugin(plugin_name)
        self._load_plugin(plugin_name)

    def get_plugin(self, name: str) -> Optional[Any]:
        """Get a plugin by name."""
        return self.plugins.get(name)

    def list_plugins(self) -> List[str]:
        """List all loaded plugins."""
        return list(self.plugins.keys())

    def call_plugin_hook(self, hook_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Call a hook on all plugins that implement it."""
        results = {}
        for name, plugin in self.plugins.items():
            if hasattr(plugin, hook_name):
                try:
                    results[name] = getattr(plugin, hook_name)(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Plugin {name} hook {hook_name} failed: {e}")
                    results[name] = {"error": str(e)}
        return results

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information about all loaded plugins."""
        info = []
        for name, plugin in self.plugins.items():
            info.append({
                "name": name,
                "type": type(plugin).__name__,
                "config": self.plugin_configs.get(name, {}),
                "hooks": [m for m in dir(plugin) if not m.startswith("_") and callable(getattr(plugin, m))],
            })
        return info
