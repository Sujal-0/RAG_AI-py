"""Enterprise Hierarchical Semantic Chunker.

Parses Markdown-formatted text to chunk by semantic meaning.
Strictly respects Markdown blocks: never splits tables, code blocks, or lists.
Enriches chunks with global document metadata.
"""

import hashlib
import re
import uuid
from typing import Any, Optional
import tiktoken
from pydantic import BaseModel, Field

class ChunkPayload(BaseModel):
    """Rich chunk structure carrying all enterprise metadata."""
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    chunk_index: int
    page_number: int
    paragraph_number: int
    
    # Hierarchy
    heading: str | None = None
    section: str | None = None
    subsection: str | None = None
    
    # Global Metadata
    document_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    document_type: str | None = None
    language: str | None = None
    topic: str | None = None
    keywords: list[str] = Field(default_factory=list)
    entities: dict[str, list[str]] = Field(default_factory=dict)
    
    # Chunk-specific
    chunk_type: str = "text"
    text: str
    char_range_start: int
    char_range_end: int
    token_count: int
    hash: str
    
    # Linked List structure for context reconstruction
    previous_chunk_id: uuid.UUID | None = None
    next_chunk_id: uuid.UUID | None = None

class SemanticChunker:
    """Enterprise chunker that understands Markdown structures."""

    def __init__(self, target_tokens: int = 350, overlap_percent: float = 0.15):
        self.target_tokens = target_tokens
        self.overlap_tokens = int(target_tokens * overlap_percent)
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoder = tiktoken.get_encoding("gpt-4")

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def _identify_block_type(self, block: str) -> str:
        """Identify the markdown block type to prevent splitting."""
        block_clean = block.strip()
        if block_clean.startswith("```") and block_clean.endswith("```"):
            return "code_block"
        if "|" in block_clean and "-|-" in block_clean.replace(" ", ""):
            return "table"
        if re.match(r"^(?:\d+\.|\-|\*)\s", block_clean):
            return "list"
        if re.match(r"^#{1,6}\s", block_clean):
            return "heading"
        return "text"

    def chunk_document(
        self, 
        pages: list[str], 
        document_name: str = "",
        document_metadata: dict[str, Any] | None = None
    ) -> list[ChunkPayload]:
        """Parse pages into semantic chunks respecting Markdown blocks."""
        doc_meta = document_metadata or {}
        
        chunks = []
        full_doc_text = "\n\n".join(pages)
        
        current_heading = "General"
        current_section = "General"
        current_subsection = None
        
        chunk_idx = 0
        global_para_index = 0
        
        # We will split the entire document roughly by double newlines,
        # but we must ensure we don't split INSIDE a code block or table.
        # A safer approach is to regex split, then merge blocks that belong together.
        
        # For simplicity, we split by double newlines and classify each block
        raw_blocks = re.split(r'\n{2,}', full_doc_text)
        
        merged_blocks = []
        in_code_block = False
        temp_block = []
        
        for raw in raw_blocks:
            if not raw.strip():
                continue
                
            if "```" in raw:
                quotes_count = raw.count("```")
                if quotes_count % 2 != 0:
                    in_code_block = not in_code_block
                    
            if in_code_block:
                temp_block.append(raw)
            else:
                if temp_block:
                    temp_block.append(raw)
                    merged_blocks.append("\n\n".join(temp_block))
                    temp_block = []
                else:
                    merged_blocks.append(raw)

        # Now we process merged blocks
        current_chunk_text = []
        current_tokens = 0
        chunk_type_flag = "text"
        
        def flush_chunk():
            nonlocal chunk_idx, current_chunk_text, current_tokens, chunk_type_flag
            if not current_chunk_text:
                return
                
            text = "\n\n".join(current_chunk_text)
            chunk_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            char_start = full_doc_text.find(text)
            if char_start == -1: char_start = 0
            
            payload = ChunkPayload(
                chunk_index=chunk_idx,
                page_number=1, # Simplified for full-doc parsing
                paragraph_number=global_para_index,
                heading=current_heading,
                section=current_section,
                subsection=current_subsection,
                document_type=doc_meta.get("document_type", "General"),
                language=doc_meta.get("language", "en"),
                topic=doc_meta.get("topics", ["General"])[0] if doc_meta.get("topics") else "General",
                keywords=doc_meta.get("keywords", []),
                entities=doc_meta.get("entities", {}),
                chunk_type=chunk_type_flag,
                text=text,
                char_range_start=char_start,
                char_range_end=char_start + len(text),
                token_count=current_tokens,
                hash=chunk_hash
            )
            chunks.append(payload)
            chunk_idx += 1
            current_chunk_text = []
            current_tokens = 0
            chunk_type_flag = "text"

        for block in merged_blocks:
            b_type = self._identify_block_type(block)
            b_tokens = self.count_tokens(block)
            global_para_index += 1
            
            # Update hierarchy
            if b_type == "heading":
                flush_chunk() # Flush before new section
                h_level = len(block) - len(block.lstrip("#"))
                h_text = block.strip("# ").strip()
                if h_level == 1:
                    current_heading = h_text
                    current_section = h_text
                    current_subsection = None
                elif h_level == 2:
                    current_section = h_text
                    current_subsection = None
                else:
                    current_subsection = h_text
                # Don't make a chunk out of just a heading
                current_chunk_text.append(block)
                current_tokens += b_tokens
                continue

            # If the block itself is massive (e.g. huge table), we must flush existing,
            # then keep this block intact even if it exceeds target tokens.
            if b_tokens > self.target_tokens:
                if current_chunk_text:
                    flush_chunk()
                
                # If it's standard text, we can split it. If it's a table/code, we MUST keep it together.
                if b_type == "text":
                    # Fallback sentence splitter for massive paragraphs
                    sentences = re.split(r"(?<=[.!?])\s+", block)
                    for s in sentences:
                        s_tokens = self.count_tokens(s)
                        if current_tokens + s_tokens > self.target_tokens:
                            flush_chunk()
                        current_chunk_text.append(s)
                        current_tokens += s_tokens
                else:
                    # Unsplittable block (table/code/list)
                    current_chunk_text.append(block)
                    current_tokens += b_tokens
                    chunk_type_flag = b_type
                    flush_chunk()
                continue
                
            # If adding this block exceeds limit, flush first
            if current_tokens + b_tokens > self.target_tokens:
                flush_chunk()
                
            current_chunk_text.append(block)
            current_tokens += b_tokens
            if b_type != "text":
                chunk_type_flag = b_type
                
        flush_chunk()

        # Build Linked List relationships
        for idx in range(len(chunks)):
            if idx > 0:
                chunks[idx].previous_chunk_id = chunks[idx - 1].id
            if idx < len(chunks) - 1:
                chunks[idx].next_chunk_id = chunks[idx + 1].id

        return chunks
