"""Deterministic Formatter Engine.

Transforms Extractive Drafts into clean, production-ready Markdown layouts
(Tables, Lists, Procedures, FAQs, Policies) without invoking an LLM.
"""

from typing import Any, Dict, List
from app.engines.response_planner import ResponsePlan

class FormatterEngine:
    @staticmethod
    def format(draft_data: Dict[str, Any], response_plan: ResponsePlan) -> str:
        if isinstance(draft_data, str):
            return draft_data
            
        grouped_by_section = draft_data.get("grouped_by_section", {})
        if not grouped_by_section:
            return "I couldn't find enough information in the uploaded documents."

        format_type = getattr(response_plan, "format_type", "Paragraph")
        formatted_answer = ""

        if format_type == "Markdown table":
            formatted_answer = "| Section | Detail |\n|---------|--------|\n"
            for sec, sents in grouped_by_section.items():
                content = " ".join(s["text"] for s in sents)
                formatted_answer += f"| **{sec}** | {content} |\n"
        
        elif format_type == "Numbered steps":
            formatted_answer = "Based on the documents, here is the procedure:\n\n"
            step = 1
            for sec, sents in grouped_by_section.items():
                if sec != "General":
                    formatted_answer += f"### {sec}\n"
                for s in sents:
                    formatted_answer += f"{step}. {s['text']}\n"
                    step += 1
                if sec != "General":
                    formatted_answer += "\n"
                    
        elif format_type == "Bullet list":
            formatted_answer = "Based on the documents, here are the key points:\n\n"
            for sec, sents in grouped_by_section.items():
                if sec != "General":
                    formatted_answer += f"### {sec}\n"
                for s in sents:
                    formatted_answer += f"- {s['text']}\n"
                if sec != "General":
                    formatted_answer += "\n"
                    
        elif format_type == "FAQ":
            formatted_answer = "Here are the relevant details:\n\n"
            for sec, sents in grouped_by_section.items():
                if sec != "General":
                    formatted_answer += f"**Q: What about {sec}?**\n"
                content = " ".join(s["text"] for s in sents)
                formatted_answer += f"A: {content}\n\n"
                
        elif format_type == "Policy":
            formatted_answer = "### Policy Details\n\n"
            for sec, sents in grouped_by_section.items():
                if sec != "General":
                    formatted_answer += f"#### {sec}\n"
                content = " ".join(s["text"] for s in sents)
                formatted_answer += f"{content}\n\n"
                
        else:
            # Paragraphs
            for sec, sents in grouped_by_section.items():
                if sec != "General":
                    formatted_answer += f"### {sec}\n"
                formatted_answer += " ".join(s["text"] for s in sents) + "\n\n"

        citations = draft_data.get("citations", [])
        if citations:
            citations_str = "\n".join(citations)
            formatted_answer += f"\n**Sources:**\n{citations_str}"

        return formatted_answer.strip()
