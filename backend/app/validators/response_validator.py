"""Response Quality Validator.

Enforces enterprise-grade output constraints: no metadata leaks, no malformed markdown,
and no repetitive hallucinated text.
"""

import re

def validate_llm_output(text: str) -> bool:
    """Validate LLM output to ensure no leaks or hallucinations."""
    if not text.strip():
        return False
    
    text_lower = text.lower()

    # 1. Structural/Metadata Leaks
    leak_keywords = [
        "chunk_id", "similarity", "telemetry", "embedding", 
        "system prompt", "instruction", "rag_eligible", "confidence_tier",
        "retrievedchunks", "metadata", "fastpathmatched"
    ]
    for keyword in leak_keywords:
        if keyword in text_lower:
            return False
            
    # 2. Strict UUID Leak Detection
    # Protects document IDs, job IDs, and chunk IDs
    uuid_pattern = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)
    if uuid_pattern.search(text):
        return False
        
    # 3. Strict Score Leak Detection (e.g. 0.9421, [score: 0.88])
    if re.search(r'score[:=]\s*0\.\d+', text_lower) or re.search(r'similarity[:=]\s*0\.\d+', text_lower):
        return False
            
    # Check for malformed markdown
    if text.count("```") % 2 != 0:
        return False
        
    # Check for duplicate bullets or repeated paragraphs
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    bullets = [line for line in lines if line.startswith(('•', '-', '*'))]
    if len(bullets) > 0 and len(set(bullets)) < len(bullets):
        return False
        
    paragraphs = [line for line in lines if not line.startswith(('•', '-', '*')) and len(line) > 50]
    if len(paragraphs) > 0 and len(set(paragraphs)) < len(paragraphs):
        return False
        
    return True
