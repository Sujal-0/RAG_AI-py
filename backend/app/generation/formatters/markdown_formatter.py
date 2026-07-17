"""Response Formatter Engine.

Applies ChatGPT-quality markdown presentation to the polished response.
Supports Tables, Callouts, Lists, and specific architectural layouts.
"""

import logging
from abc import ABC, abstractmethod
from app.generation.dto.dtos import ResponsePlan, FormattedResponse

logger = logging.getLogger("app")


class BaseFormatter(ABC):
    @abstractmethod
    def format(self, content: str, plan: ResponsePlan) -> FormattedResponse:
        pass


class MarkdownFormatter(BaseFormatter):
    """Applies beautiful markdown formatting."""
    
    def format(self, content: str, plan: ResponsePlan) -> FormattedResponse:
        logger.info("Formatting Markdown", extra={"structured_log": True, "stage": "MarkdownFormatter"})
        
        formatted_content = content
        
        # Inject Callouts
        if plan.requires_safety_disclaimer:
            formatted_content = f"> [!WARNING]\n> This response involves sensitive policy/security matters. Please verify internally.\n\n{formatted_content}"
            
        # Basic structural checks
        has_broken_formatting = False
        if plan.format_type == "Markdown Table" and "|" not in formatted_content:
            has_broken_formatting = True
            
        return FormattedResponse(
            markdown_content=formatted_content,
            has_broken_formatting=has_broken_formatting
        )


class FormatterProviderFactory:
    """Dynamically loads the formatter."""
    
    _instance: BaseFormatter | None = None
    
    @classmethod
    def get_provider(cls, provider_name: str) -> BaseFormatter:
        if cls._instance is None:
            cls._instance = MarkdownFormatter()
        return cls._instance
