import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("app")

from app.embeddings.embedding_service import EmbeddingService

print(f"Is real model: {EmbeddingService.is_real_model()}")
try:
    # Trigger get_model
    vec = EmbeddingService.generate_embedding("director of data science")
    print(f"Vector dim: {len(vec)}")
    print(f"Is real model after get_model: {EmbeddingService.is_real_model()}")
except Exception as e:
    print(f"Error: {e}")
