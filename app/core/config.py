import os
from typing import Dict, Any
import yaml
from yaml.loader import SafeLoader

class Settings:
    def __init__(self):
        self.QDRANT_HOST = "localhost"
        self.QDRANT_PORT = 6333
        self.OLLAMA_API_URL = "http://localhost:11434/api"
        self.CACHE_TTL = 3600  # 1 hour
        self.CACHE_MAXSIZE = 1000
        self.RATE_LIMIT = 10
        self.RATE_LIMIT_DURATION = 60
        
        # Load additional settings from config file
        config_path = os.path.join('config', 'config.yaml')
        if os.path.exists(config_path):
            with open(config_path) as file:
                config = yaml.load(file, Loader=SafeLoader)
                for key, value in config.get('settings', {}).items():
                    setattr(self, key, value)

settings = Settings()