"""Deterministic text cleaners for document preprocessing.

Removes headers, footers, duplicate whitespace, repairs line hyphenation,
and cleans Unicode artifacts.
"""

import re
from collections import Counter


class TextCleaner:
    """Performs deterministic cleaning operations on extracted document text."""

    @staticmethod
    def clean_unicode(text: str) -> str:
        """Purge invisible unicode characters, BOMs, and zero-width artifacts."""
        # Remove Byte Order Mark (BOM)
        text = text.replace("\ufeff", "")
        # Remove zero-width spaces, joiners, non-joiners
        text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
        return text

    @classmethod
    def repair_hyphenation(cls, text: str) -> str:
        """Join words split by hyphenation at line breaks (e.g., de-\nvelopment -> development)."""
        return re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

    @classmethod
    def clean_whitespace(cls, text: str) -> str:
        """Collapse multiple spaces, tabs, and duplicate blank lines."""
        text = text.replace("\r", "")
        # Collapse multiple spaces on each line and strip trailing whitespace on each line
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # Collapse three or more newlines to exactly two newlines (keeps paragraph separation clean)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
        
    @classmethod
    def merge_wrapped_paragraphs(cls, text: str) -> str:
        """Merge lines that were wrapped inside a paragraph, preserving real paragraph breaks."""
        # Replace single newlines that are surrounded by text (not newlines) with a space
        # A single newline followed by a lowercase letter is usually a wrapped line
        text = re.sub(r"(?<=[a-zA-Z,])\n(?=[a-z])", " ", text)
        return text

    @classmethod
    def normalize_punctuation(cls, text: str) -> str:
        """Standardize smart quotes, dashes, and ellipses."""
        text = text.replace("’", "'").replace("‘", "'")
        text = text.replace("”", '"').replace("“", '"')
        text = text.replace("–", "-").replace("—", "-") # En/Em dash to hyphen
        text = re.sub(r"\.{4,}", "...", text) # Too many dots
        return text

    @classmethod
    def remove_ocr_artifacts(cls, text: str) -> str:
        """Remove common OCR garbage like floating single characters and special symbols."""
        # Remove floating random single characters (excluding I, A, a, i, and numbers) surrounded by spaces
        # Be careful not to destroy math equations or list items
        # Usually OCR noise looks like: ` a b # % z `
        text = re.sub(r"(?<= )[b-hj-zB-HJ-Z](?= )", "", text)
        return text

    @classmethod
    def remove_headers_footers(cls, pages: list[str]) -> list[str]:
        """Detect and remove repetitive headers and footers across pages.

        Compares lines at the very top (first 2 lines) and bottom (last 2 lines)
        across all pages. If a line appears in the header/footer zones on >= 50%
        of the pages (minimum of 2 pages), it is identified as a template header/footer.
        """
        if len(pages) < 3:
            return pages

        header_lines = []
        footer_lines = []

        for page in pages:
            lines = [line.strip() for line in page.split("\n") if line.strip()]
            if len(lines) >= 1:
                header_lines.append(lines[0])
            if len(lines) >= 2:
                header_lines.append(lines[1])
            if len(lines) >= 1:
                footer_lines.append(lines[-1])
            if len(lines) >= 2:
                footer_lines.append(lines[-2])

        # Require repeating on at least 50% of pages, but minimum 2 pages
        threshold = max(2, len(pages) // 2)
        header_counts = Counter(header_lines)
        footer_counts = Counter(footer_lines)

        bad_headers = {line for line, count in header_counts.items() if count >= threshold}
        bad_footers = {line for line, count in footer_counts.items() if count >= threshold}

        cleaned_pages = []
        for page in pages:
            lines = page.split("\n")
            cleaned_lines = []
            for line in lines:
                line_stripped = line.strip()
                if line_stripped in bad_headers or line_stripped in bad_footers:
                    continue
                cleaned_lines.append(line)
            cleaned_pages.append("\n".join(cleaned_lines))

        return cleaned_pages

    @classmethod
    def clean_document_text(cls, pages: list[str]) -> list[str]:
        """Orchestrates complete cleaning lifecycle on a list of document pages."""
        cleaned_pages = cls.remove_headers_footers(pages)

        final_pages = []
        for page in cleaned_pages:
            text = cls.clean_unicode(page)
            text = cls.normalize_punctuation(text)
            text = cls.repair_hyphenation(text)
            text = cls.merge_wrapped_paragraphs(text)
            text = cls.remove_ocr_artifacts(text)
            text = cls.clean_whitespace(text)
            final_pages.append(text)

        return final_pages
