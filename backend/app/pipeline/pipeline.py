"""Explicit pipeline configuration.

Defines the exact list and execution order of all conversation engines for Phase 6.
"""

from app.engines.alias import AliasEngine
from app.engines.empty_input import EmptyInputEngine
from app.engines.fallback import FallbackEngine
from app.engines.gibberish import GibberishEngine
from app.engines.goodbye import GoodbyeEngine
from app.engines.greeting import GreetingEngine
from app.engines.knowledge_engine import KnowledgeEngine
from app.engines.rag_engine import RAGEngine
from app.engines.normalization import NormalizationEngine
from app.engines.profanity import ProfanityEngine
from app.engines.query_decision_engine import QueryDecisionEngine
from app.engines.clarification_engine import ClarificationEngine
from app.engines.conversational_resolution_engine import ConversationalResolutionEngine
from app.engines.query_understanding import QueryUnderstandingEngine
from app.engines.small_talk import SmallTalkEngine
from app.engines.thanks import ThanksEngine
from app.engines.validation import ValidationEngine

PIPELINE = (
    ValidationEngine(),
    NormalizationEngine(),
    ProfanityEngine(),
    EmptyInputEngine(),
    AliasEngine(),
    ConversationalResolutionEngine(),
    ClarificationEngine(),
    QueryDecisionEngine(),
    GreetingEngine(),
    GoodbyeEngine(),
    ThanksEngine(),
    SmallTalkEngine(),
    QueryUnderstandingEngine(),
    KnowledgeEngine(),
    RAGEngine(),
    GibberishEngine(),
    FallbackEngine(),
)
