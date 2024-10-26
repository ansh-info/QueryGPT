import requests
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self):
        self.api_url = settings.OLLAMA_API_URL
    
    def get_embedding(self, text: str):
        try:
            response = requests.post(
                f"{self.api_url}/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": text
                }
            )
            response.raise_for_status()
            return response.json()['embedding']
        except requests.RequestException as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None
    
    def generate_response(self, prompt: str):
        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()['response']
        except requests.RequestException as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm unable to generate a response at the moment."