import os
import yaml
import importlib.util
from typing import Dict, Any, List
from kernel.logger import get_logger

logger = get_logger(__name__)

class PluginManager:
    """
    State-based registry for Plugin Packages.
    Loads complete packages (manifest.yaml, JSON schemas, etc).
    """
    
    def __init__(self, plugins_dir: str = "plugins"):
        # Resolve absolute path to plugins directory
        # Assumes this script is in apps/api/kernel/plugins/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.plugins_dir = os.path.join(base_dir, plugins_dir)
        self.plugins: Dict[str, Any] = {}
        
    def load_all(self):
        """
        Scans the plugins directory and loads all manifest.yaml files.
        """
        logger.info("plugin_manager.loading_all", directory=self.plugins_dir)
        
        if not os.path.exists(self.plugins_dir):
            logger.warning("plugin_manager.no_plugins_dir", directory=self.plugins_dir)
            return

        for plugin_name in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            if not os.path.isdir(plugin_path):
                continue
                
            manifest_path = os.path.join(plugin_path, "manifest.yaml")
            if not os.path.exists(manifest_path):
                continue
                
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = yaml.safe_load(f)
                
            capabilities_dir = os.path.join(plugin_path, manifest.get("capabilities_dir", "capabilities"))
            caps = {}
            if os.path.exists(capabilities_dir):
                for cap_file in os.listdir(capabilities_dir):
                    if cap_file.endswith(".yaml"):
                        with open(os.path.join(capabilities_dir, cap_file), 'r', encoding='utf-8') as cf:
                            cap_data = yaml.safe_load(cf)
                            caps[cap_data.get("name")] = cap_data
                            
            manifest["loaded_capabilities"] = caps
            self.plugins[plugin_name] = manifest
            
            # Load the driver if specified
            driver_name = manifest.get("driver")
            if driver_name:
                driver_path = os.path.join(plugin_path, "drivers", f"{driver_name}.py")
                if os.path.exists(driver_path):
                    spec = importlib.util.spec_from_file_location(f"plugin_{plugin_name}_{driver_name}", driver_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        logger.info("plugin_manager.driver_loaded", driver=driver_name, plugin=plugin_name)
                        
            logger.info("plugin_manager.plugin_loaded", plugin=plugin_name, capabilities=len(caps))
        
    def watch(self):
        """
        Starts a watchdog observer on the plugins directory to hot-reload changes.
        """
        logger.info("plugin_manager.starting_watchdog", directory=self.plugins_dir)

plugin_manager = PluginManager()
