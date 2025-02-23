import json
import os

CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

def get_api_key(key_name):
    config = load_config()
    return config.get(key_name, '')

def set_api_key(key_name, value):
    config = load_config()
    config[key_name] = value
    save_config(config)

def save_api_key(key_name, key_value):
    """Save an API key to the config file."""
    try:
        # Load existing config
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        
        # Update key
        config[key_name] = key_value
        
        # Save config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
            
    except Exception as e:
        print(f"Error saving API key: {str(e)}")
        raise  # Re-raise to show error in GUI
