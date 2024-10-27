import requests
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import time

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434/api"):
        """Initialize OllamaService with API endpoint"""
        self.api_url = base_url
        self.embedding_model = "nomic-embed-text"
        self.generation_model = "llama3.2"
        self.default_timeout = 30
        self.max_retries = 3
        self.retry_delay = 1

    def get_embedding(self, text: str, retry_count: int = 0) -> Optional[List[float]]:
        """Get embeddings for text with retry logic"""
        try:
            response = requests.post(
                f"{self.api_url}/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=self.default_timeout
            )
            response.raise_for_status()
            return response.json()['embedding']
        except requests.RequestException as e:
            if retry_count < self.max_retries:
                logger.warning(f"Retry {retry_count + 1} for embedding generation")
                time.sleep(self.retry_delay)
                return self.get_embedding(text, retry_count + 1)
            logger.error(f"Error getting embedding: {str(e)}")
            return None

    def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate AI response with parameters"""
        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json={
                    "model": self.generation_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9,
                        "top_k": 40,
                        "max_tokens": 500,
                        "stop": ["###"]  # Custom stop token
                    }
                },
                timeout=self.default_timeout
            )
            response.raise_for_status()
            return response.json()['response']
        except requests.RequestException as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm unable to generate a response at the moment."

    def generate_response_stream(self, prompt: str, callback=None):
        """Generate response with streaming"""
        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json={
                    "model": self.generation_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40
                    }
                },
                stream=True,
                timeout=self.default_timeout
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    json_response = json.loads(line)
                    if callback:
                        callback(json_response.get('response', ''))
                    yield json_response.get('response', '')
        except Exception as e:
            logger.error(f"Error in stream generation: {str(e)}")
            yield "Error generating response"

    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Get embeddings for multiple texts"""
        return [self.get_embedding(text) for text in texts]

    def health_check(self) -> Dict[str, Any]:
        """Check if Ollama service is available"""
        try:
            # Test embedding generation
            test_embedding = self.get_embedding("test")
            embedding_status = bool(test_embedding)

            # Test response generation
            test_response = self.generate_response("Hello")
            generation_status = bool(test_response)

            return {
                'status': 'healthy' if embedding_status and generation_status else 'partial',
                'embedding_service': 'available' if embedding_status else 'unavailable',
                'generation_service': 'available' if generation_status else 'unavailable',
                'models': {
                    'embedding': self.embedding_model,
                    'generation': self.generation_model
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models"""
        try:
            response = requests.get(
                f"{self.api_url}/tags",
                timeout=self.default_timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            return {}