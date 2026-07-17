"""Retrieval Provider Factories.

Implements the Factory Pattern to lazily instantiate underlying providers 
(Entity Extraction, Keyword Extraction, Reranking, Rewriting) based on configuration.
"""

import logging
from app.core.settings import settings
from app.engines.query.entity_extractor import BaseEntityExtractor, SpacyEntityExtractor
from app.engines.query.keyword_extractor import BaseKeywordExtractor, HeuristicKeywordExtractor
from app.engines.query.query_rewriter import BaseQueryRewriteProvider, HeuristicRewriteProvider, LLMRewriteProvider
from app.engines.reranking.cross_encoder import BaseRerankerProvider, SentenceTransformerReranker

logger = logging.getLogger("app")


class EntityProviderFactory:
    _instance: BaseEntityExtractor | None = None
    
    @classmethod
    def get_provider(cls) -> BaseEntityExtractor:
        if cls._instance is None:
            provider_type = settings.retrieval.entity_provider.lower()
            if provider_type == "spacy":
                cls._instance = SpacyEntityExtractor()
            else:
                logger.warning(f"Unknown Entity Provider '{provider_type}', falling back to spaCy.")
                cls._instance = SpacyEntityExtractor()
        return cls._instance


class KeywordProviderFactory:
    _instance: BaseKeywordExtractor | None = None
    
    @classmethod
    def get_provider(cls) -> BaseKeywordExtractor:
        if cls._instance is None:
            provider_type = settings.retrieval.keyword_provider.lower()
            if provider_type == "heuristic":
                cls._instance = HeuristicKeywordExtractor()
            else:
                logger.warning(f"Unknown Keyword Provider '{provider_type}', falling back to Heuristic.")
                cls._instance = HeuristicKeywordExtractor()
        return cls._instance


class QueryRewriteProviderFactory:
    _instance: BaseQueryRewriteProvider | None = None
    
    @classmethod
    def get_provider(cls) -> BaseQueryRewriteProvider:
        if cls._instance is None:
            provider_type = settings.retrieval.rewrite_provider.lower()
            if provider_type == "llm":
                cls._instance = LLMRewriteProvider()
            else:
                cls._instance = HeuristicRewriteProvider()
        return cls._instance


class RerankerProviderFactory:
    _instance: BaseRerankerProvider | None = None
    
    @classmethod
    def get_provider(cls) -> BaseRerankerProvider:
        if cls._instance is None:
            provider_type = settings.retrieval.reranker_provider.lower()
            model_name = settings.retrieval.reranker_model
            if provider_type == "sentence_transformer":
                cls._instance = SentenceTransformerReranker(model_name=model_name)
            else:
                logger.warning(f"Unknown Reranker Provider '{provider_type}', falling back to SentenceTransformer.")
                cls._instance = SentenceTransformerReranker(model_name=model_name)
        return cls._instance
