import logging
import json
import requests
from google import genai
from typing import Dict, Any, Optional, List
from config.settings import settings

logger = logging.getLogger(__name__)

class LLMProvider:
    """Base class for LLM providers"""
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

class OllamaProvider(LLMProvider):
    """Ollama implementation for local LLMs"""
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": kwargs.get("model", self.model),
                    "prompt": prompt,
                    "stream": False,
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.9),
                    "top_k": kwargs.get("top_k", 40),
                },
                timeout=kwargs.get("timeout", 20)
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            return ""

    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": kwargs.get("model", self.model),
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "temperature": kwargs.get("temperature", 0.2),
                },
                timeout=kwargs.get("timeout", 20)
            )
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "").strip()
            
            # Find and parse JSON
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                return json.loads(response_text[start_idx:end_idx])
            return {}
        except Exception as e:
            logger.error(f"Ollama JSON generation error: {e}")
            return {}

class GeminiProvider(LLMProvider):
    """Google Gemini implementation using new 'google-genai' SDK"""
    def __init__(self):
        if not settings.google_api_key:
            logger.error("GOOGLE_API_KEY not found in settings!")
            self.client = None
        else:
            # New SDK initialization
            self.client = genai.Client(api_key=settings.google_api_key)
        
        # Ensure model name is clean (new SDK handles models/ prefix internally)
        self.model_name = settings.gemini_model_name
        if self.model_name.startswith("models/"):
            self.model_name = self.model_name.replace("models/", "")
        
    def generate(self, prompt: str, **kwargs) -> str:
        if not self.client:
            return "Gemini Client not initialized"
        try:
            config = {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "top_k": kwargs.get("top_k", 40),
            }
            # New generate_content API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return ""

    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        if not self.client:
            return {}
        try:
            # Structured output configuration
            config = {
                "temperature": kwargs.get("temperature", 0.2),
                "response_mime_type": "application/json"
            }
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            response_text = response.text.strip()
            
            # Robust JSON parsing
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                return json.loads(response_text[start_idx:end_idx])
            return {}
        except Exception as e:
            logger.error(f"Gemini JSON generation error: {e}")
            return {}

class LLMClient:
    """Factory and client for LLM interactions with automatic fallback"""
    _instance = None
    _primary_provider = None
    _secondary_provider = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            provider_type = settings.llm_provider.lower()
            
            # Initialize both if possible for fallback
            ollama = OllamaProvider()
            gemini = GeminiProvider() if settings.google_api_key else None
            
            if provider_type == "gemini" and gemini:
                logger.info("🚀 PRIMARY: GEMINI | SECONDARY: OLLAMA")
                cls._primary_provider = gemini
                cls._secondary_provider = ollama
            else:
                logger.info("🏠 PRIMARY: OLLAMA | SECONDARY: GEMINI (if key exists)")
                cls._primary_provider = ollama
                cls._secondary_provider = gemini
                
        return cls._instance
    
    def generate(self, prompt: str, **kwargs) -> str:
        # Increase default timeout to configured value
        if "timeout" not in kwargs:
            kwargs["timeout"] = settings.llm_timeout if hasattr(settings, 'llm_timeout') else 30
            
        # Try Primary
        try:
            response = self._primary_provider.generate(prompt, **kwargs)
            if response and len(response.strip()) > 0:
                return response
            logger.warning("⚠️ Primary LLM returned empty response, trying fallback...")
        except Exception as e:
            logger.error(f"❌ Primary LLM failed: {e}")
            
        # Try Secondary (Fallback)
        if self._secondary_provider:
            try:
                logger.info("🔄 FALLBACK: Attempting secondary provider...")
                return self._secondary_provider.generate(prompt, **kwargs)
            except Exception as e:
                logger.error(f"❌ Secondary LLM also failed: {e}")
        
        return "Dạ, hệ thống xử lý đang bận một chút, anh chị vui lòng thử lại sau nhé!"

    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # Try Primary
        try:
            result = self._primary_provider.generate_json(prompt, **kwargs)
            if result:
                return result
        except Exception as e:
            logger.error(f"❌ Primary JSON LLM failed: {e}")
            
        # Try Secondary
        if self._secondary_provider:
            try:
                return self._secondary_provider.generate_json(prompt, **kwargs)
            except Exception as e:
                logger.error(f"❌ Secondary JSON LLM failed: {e}")
                
        return {}

# Singleton instance
llm_client = LLMClient()
