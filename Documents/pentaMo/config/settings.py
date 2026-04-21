from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./pentamo.db"
    
    # Ollama (Model A - General Chat & Intent/Entity Extraction)
    # Kế hoạch đề xuất: Arcee-VyLinh (3B) - Fallback: llama3.2:1b
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    
    # Google Gemini
    google_api_key: Optional[str] = None
    gemini_model_name: str = "gemini-2.0-flash"
    
    # LLM Provider Selection
    llm_provider: str = "ollama"
    
    # llama.cpp Server / Ollama Model B
    # Kế hoạch đề xuất: LFM2 (1.2B)
    agent_model_b_name: str = "lfm2.5-thinking:1.2b"
    llama_cpp_url: Optional[str] = "http://localhost:11434"

    
    # Redis
    redis_url: Optional[str] = "redis://localhost:6379"
    
    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # JWT Authentication (Phase 3)
    jwt_secret_key: str = "pentamo-super-secret-key-change-in-production-please-123456"
    
    # Logging
    log_level: str = "INFO"
    
    # New Configurable Parameters
    llm_timeout: int = 30
    vector_search_threshold: float = 0.4
    
    class Config:
        env_file = ".env"
        extra = "ignore"
        protected_namespaces = ()

settings = Settings()
