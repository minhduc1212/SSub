import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

def load_config():
    default_config = {
        "username": "",
        "password": "",
        "subdl_api_key": "",
        "subscene_cf_clearance": "",
        "subscene_user_agent": ""
    }
    
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)
            print(f"Created configuration template '{CONFIG_FILE}'.")
        except Exception as e:
            print(f"Error creating default config: {e}")
        return default_config
        
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Ensure all keys exist
            updated = False
            for k, v in default_config.items():
                if k not in config:
                    config[k] = v
                    updated = True
            if updated:
                save_config(config)
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
