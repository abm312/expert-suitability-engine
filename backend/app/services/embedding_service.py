from typing import List, Optional
from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    """Service for generating text embeddings using OpenAI"""
    
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS
    
    def _ensure_client(self):
        if not self.client:
            raise ValueError("OpenAI API key not configured")
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        self._ensure_client()
        
        # Truncate if too long (rough estimate)
        max_chars = 8000 * 4  # ~8k tokens
        if len(text) > max_chars:
            text = text[:max_chars]
        
        response = self.client.embeddings.create(
            input=text,
            model=self.model,
        )
        
        return response.data[0].embedding
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        self._ensure_client()
        
        if not texts:
            return []
        
        # Truncate long texts
        max_chars = 8000 * 4
        processed_texts = [t[:max_chars] if len(t) > max_chars else t for t in texts]
        
        # Process in batches of 100
        all_embeddings = []
        batch_size = 100
        
        for i in range(0, len(processed_texts), batch_size):
            batch = processed_texts[i:i + batch_size]
            response = self.client.embeddings.create(
                input=batch,
                model=self.model,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def embed_query(self, query: str) -> List[float]:
        """Embed a search query (same as embed_text but semantically clear)"""
        return await self.embed_text(query)

