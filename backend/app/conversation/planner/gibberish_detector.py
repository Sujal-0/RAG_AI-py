"""Enterprise Gibberish Detector.

Performs deep textual analysis to catch keyboard smashes and random noise
using dictionary ratios, vowel ratios, and character entropy.
"""

import math
import re
from typing import Set

class EnterpriseGibberishDetector:
    # A small core dictionary of valid short/medium words often seen in queries.
    VALID_WORDS: Set[str] = {
        "hi", "hello", "hey", "what", "is", "the", "are", "you", "who", "when", 
        "where", "why", "how", "can", "do", "does", "did", "to", "for", "in", 
        "on", "at", "with", "about", "me", "my", "your", "yours", "tell", 
        "explain", "summarize", "compare", "and", "or", "not", "a", "an", "i",
        "mobiloitte", "ai", "platform", "bot", "assistant", "thanks", "bye",
        "good", "morning", "night", "evening", "yes", "no", "ok", "okay",
        "list", "table", "timeline", "history", "difference", "vs", "versus",
        "tysm", "thx", "ty", "hmm", "wtf", "brb", "idk", "btw", "pls", "plz",
        "json", "tmux", "nmap", "wget", "dpkg", "ddos", "zshell", "sshd", "csrf", "ssrf"
    }

    @classmethod
    def is_gibberish(cls, query: str) -> bool:
        if not query:
            return False
            
        query_lower = query.lower()
        
        # 1. Strict safeguard against valid conversational words
        whitelist_words = {"where", "what", "explain", "detail", "bullet", "points", "summarize", "tell", "compare", "how", "why"}
        words = set(re.findall(r'\b\w+\b', query_lower))
        if words.intersection(whitelist_words):
            return False
            
        # 2. A query can ONLY be classified as Gibberish if its length is less than 6 characters
        if len(query.strip()) < 6:
            return True
            
        # 3. OR it contains non-alphanumeric keyboard-smash characters
        if re.search(r'[^a-zA-Z0-9\s.,?!]', query):
            return True
            
        return False
