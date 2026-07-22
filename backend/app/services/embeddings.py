import os
from typing import List
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global model instance cache
_sentence_transformer_model = None


def get_embedding_model():
    global _sentence_transformer_model
    if _sentence_transformer_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Fast, high-performance light model (384 dims)
            _sentence_transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded SentenceTransformer model: all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer: {e}. Falling back to deterministic embedding.")
            _sentence_transformer_model = "fallback"
    return _sentence_transformer_model


class EmbeddingService:
    @staticmethod
    def get_embeddings(texts: List[str]) -> List[List[float]]:
        """Generates vector embeddings for a list of text strings."""
        if not texts:
            return []

        # Try OpenAI embeddings if API key is set and valid
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "mock-openai-key":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.embeddings.create(
                    input=texts,
                    model="text-embedding-3-small"
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                logger.warning(f"OpenAI embedding call failed: {e}. Falling back to SentenceTransformers.")

        # Local SentenceTransformer
        model = get_embedding_model()
        if model != "fallback":
            embeddings = model.encode(texts, show_progress_bar=False)
            return embeddings.tolist()

        # Deterministic dummy fallback for offline testing without models downloaded
        results = []
        for text in texts:
            seed = sum(ord(c) for c in text) % 1000
            vector = [((seed + i) % 100) / 100.0 for i in range(384)]
            results.append(vector)
        return results

    @staticmethod
    def get_embedding(text: str) -> List[float]:
        """Generates a single vector embedding."""
        res = EmbeddingService.get_embeddings([text])
        return res[0] if res else []
