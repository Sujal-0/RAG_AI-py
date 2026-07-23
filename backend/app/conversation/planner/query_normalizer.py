"""Enterprise Query Normalizer.

Provides deterministic text normalization for the FastPath pipeline.
Handles case, spaces, unicode, punctuation, emojis, and repeated characters.
"""

import re
import unicodedata

class QueryNormalizer:
    @classmethod
    def normalize(cls, query: str) -> str:
        if not query or not str(query).strip():
            return ""
            
        # 1. Unicode normalization (handles smart quotes, special spaces, etc.)
        query = unicodedata.normalize("NFKC", str(query))
        
        # 2. Emoji stripping (remove anything outside basic multilingual plane that isn't word/space/punctuation)
        query = query.encode("ascii", "ignore").decode("ascii")
        
        # 3. Lowercase and strip whitespace
        query = query.lower().strip()
        
        # 4. Remove meaningless punctuation (everything except alphanumeric and whitespace)
        query = re.sub(r'[^\w\s]', '', query)
        
        # 5. Normalize duplicate characters specifically for common words
        # hii -> hi, heya -> hey, helloooo -> hello, thankssss -> thanks, byeeee -> bye
        query = re.sub(r"\b(h)(i+)\b", "hi", query)
        query = re.sub(r"\b(h)(i+)(y+)(a*)\b", "hiya", query)
        query = re.sub(r"\b(h)(e+)(y+)(a*)\b", "hey", query)
        query = re.sub(r"\b(h)(e+)(l+)(o+)\b", "hello", query)
        query = re.sub(r"\b(b)(y+)(e+)\b", "bye", query)
        query = re.sub(r"\b(t)(h)(a)(n)(k)(s+)\b", "thanks", query)
        
        # 6. General deduplication for >= 3 same characters (e.g. keyboard spam like "asdfgh")
        query = re.sub(r'(.)\1{2,}', r'\1', query)
        
        # 7. Add specific abbreviations (gm, goodmorning)
        query = re.sub(r'\b(gm)\b', 'good morning', query)
        query = re.sub(r'\bgoodmorning\b', 'good morning', query)
        query = re.sub(r'\bgoodnight\b', 'good night', query)
        query = re.sub(r'\bgood evening\b', 'good evening', query)
        
        # 8. Normalize whitespace (tabs, newlines, multiple spaces)
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query
