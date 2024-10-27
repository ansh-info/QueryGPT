import requests
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self):
        self.api_url = "http://localhost:11434/api"
        self.embedding_model = "nomic-embed-text"
        self.generation_model = "llama3.2"

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embeddings for text"""
        try:
            response = requests.post(
                f"{self.api_url}/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()['embedding']
        except requests.RequestException as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None

    def generate_response(self, prompt: str) -> str:
        """Generate AI response"""
        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json={
                    "model": self.generation_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40,
                        "max_tokens": 500
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()['response']
        except requests.RequestException as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm unable to generate a response at the moment."

    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Get embeddings for multiple texts"""
        return [self.get_embedding(text) for text in texts]

    def health_check(self) -> bool:
        """Check if Ollama service is available"""
        try:
            response = requests.get(f"{self.api_url}/health")
            return response.status_code == 200
        except requests.RequestException:
            return False