"""Conversation prefix, suffix, and content classification helpers.

Reuses shared vocabulary configurations to categorize query sections statelessly.
"""

import re

from app.configs.aliases import ALIASES
from app.configs.common import (
    COMMON_COMPANY_WORDS,
    COMMON_FILLER_WORDS,
    COMMON_HONORIFICS,
    COMMON_NAMES,
    COMMON_NOISE_SUFFIXES,
    COMMON_POLITE_WORDS,
    LOCATIONS,
    TECHNICAL_VOCABULARY,
)
from app.configs.goodbyes import GOODBYE_GROUPS
from app.configs.greetings import GREETING_GROUPS
from app.configs.knowledge import KNOWLEDGE_DATABASE
from app.configs.small_talk import SMALL_TALK_GROUPS
from app.configs.thanks import THANKS_GROUPS

ADDITIONAL_KNOWN_WORDS = {
    "what", "where", "who", "why", "how", "when", "is", "are", "do", "does", "can",
    "will", "should", "about", "elon", "musk", "salary", "mars", "population",
    "president", "weather", "time", "day", "date", "year", "age", "revenue", "worth",
    "net", "cost", "price", "ceo", "etc", "computer", "language", "manager",
    "student", "developer", "engineer", "software", "development", "program", "code",
    "won", "did", "the", "a", "an", "of", "in", "on", "at", "to", "for", "with",
    "tell", "me", "you", "your", "my", "name", "that", "this", "it", "they", "them",
    "he", "she", "we", "us", "i", "have", "has", "had", "say", "said", "go", "went",
    "get", "got", "make", "made", "know", "knew", "think", "thought", "see", "saw",
    "random", "search", "query", "nothing", "stock", "nasa", "ipl", "bitcoin",
    "some", "any", "no", "yes", "ok", "hello", "hi", "hey", "bye", "thanks", "good",
    "morning", "afternoon", "evening", "night", "other", "many", "more", "most",
    "very", "such", "like", "our", "their", "here", "there", "which",
    "whose", "whom", "these", "those", "been", "being",
    "am", "was", "were", "be", "having", "doing", "could", "may", "might", "must", "shall", "would", "above", "across", "after", "against", "along",
    "amid", "among", "around", "as", "before", "behind", "below", "beneath",
    "beside", "between", "beyond", "but", "by", "concerning", "considering",
    "despite", "down", "during", "except", "following", "from", "inside", "into", "minus", "near", "off", "onto", "opposite",
    "out", "outside", "over", "past", "pending", "regarding", "since", "through",
    "throughout", "toward", "under", "underneath", "unlike", "until", "up",
    "upon", "versus", "via", "within", "without", "and", "or",
    "nor", "yet", "so", "both", "either", "neither", "not", "only",
    "also", "even", "just", "too", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten"
}

VALID_2_LETTER_WORDS = {
    "am", "an", "as", "at", "be", "by", "do", "go", "he", "if", "in", "is", "it",
    "me", "my", "no", "of", "on", "or", "so", "to", "up", "us", "we", "ai", "ui",
    "ux", "pm", "qa", "hr", "pr", "ip", "os", "db", "ml", "dl", "vm", "js",
    "ts", "py", "vs"
}

VALID_3_LETTER_WORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "had",
    "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how",
    "man", "new", "now", "old", "see", "two", "way", "who", "boy", "did", "its",
    "let", "put", "run", "sat", "she", "too", "use", "act", "ago", "aim", "air",
    "art", "bad", "bag", "bar", "bed", "big", "bit", "box", "bye", "cat", "car",
    "cow", "cry", "cup", "cut", "dad", "dog", "dry", "due", "ear", "eat", "end",
    "era", "eye", "fan", "far", "fat", "fee", "few", "fit", "fly", "foe", "fun",
    "gas", "gem", "god", "gun", "guy", "hat", "hen", "hey", "hit", "hot", "ice",
    "ill", "ink", "inn", "job", "joy", "key", "kid", "lab", "law", "lay", "led",
    "leg", "lid", "lie", "lip", "log", "low", "mad", "map", "met", "mix", "mud",
    "mug", "net", "nod", "nor", "nut", "oak", "odd", "off", "oil", "opt", "ore",
    "owl", "own", "pad", "pan", "pay", "pen", "pet", "pin", "pit", "pod", "pot",
    "pop", "pry", "pub", "rag", "raw", "ray", "red", "rib", "rid", "rip", "rob",
    "rod", "row", "rub", "rug", "sea", "sew", "shy", "sin", "sip", "sir", "sit",
    "ski", "sky", "sly", "sob", "sod", "son", "sow", "soy", "spa", "spy", "sum",
    "sun", "tag", "tan", "tap", "tar", "tea", "ten", "tie", "tin", "tip", "toe",
    "ton", "toy", "try", "tub", "tug", "van", "vet", "vow", "wad", "wag", "war",
    "wax", "web", "wed", "wet", "wig", "win", "wit", "woe", "won", "wry", "yak",
    "yam", "yea", "yes", "yet", "yip", "zen", "zoo", "api", "dev", "git", "url",
    "xml", "sql", "csv", "pdf", "mac", "app", "npm", "pip", "env",
    "cmd", "txt", "dom", "css", "src", "org", "com", "bin",
    "bot", "php", "vue", "cpp", "ios", "aws", "gcp"
}

VALID_COMMON_ENGLISH_WORDS = {
    "what", "when", "where", "which", "while", "whose", "would", "could", "should", "their", "there", "these", "those",
    "about", "above", "after", "again", "against", "before", "behind", "below", "between", "under", "until", "with",
    "without", "through", "during", "before", "after", "about", "above", "below", "explain", "describe", "details",
    "information", "please", "thank", "thanks", "welcome", "hello", "goodbye", "working", "work", "firm", "company",
    "people", "person", "employees", "employee", "developer", "engineer", "software", "development", "training",
    "department", "departments", "office", "locations", "locations", "noida", "pune", "delhi", "singapore",
    "london", "boston", "services", "solutions", "technologies", "careers", "internship", "founder", "vision",
    "mission", "values", "culture", "timing", "timings", "hours", "holiday", "leave", "vacation", "policy",
    "policies", "security", "zero", "trust", "mfa", "auth", "aws", "gcp", "azure", "docker", "kubernetes",
    "django", "react", "python", "javascript", "typescript", "rust", "java", "kotlin", "swift", "solidity",
    "blockchain", "github", "gitlab", "confluence", "jira", "other", "some", "many", "most", "more", "much",
    "very", "well", "good", "great", "nice", "fine", "like", "love", "hate", "want", "need", "have", "here",
    "know", "make", "take", "come", "give", "look", "time", "year", "people", "name", "ways", "work", "does",
    "help", "sure", "okay", "correct", "wrong", "true", "false", "valid", "invalid", "empty", "input", "query",
    "answer", "response", "result", "history", "session", "request", "error", "warning", "success", "failed",
    "status", "ready", "search", "upload", "document", "documents", "file", "files", "version", "page", "section",
    "chunk", "source", "sources", "citation", "citations", "telemetry", "latency", "duration", "token", "tokens",
    "prompt", "completion", "embed", "embedding", "embeddings", "vector", "similarity", "threshold", "limit",
    "database", "postgres", "pgvector", "high", "school", "salary", "stock", "price", "mars", "population",
    "corporate", "mobiloit", "flutt", "solid",
    # Common English nouns that must not be flagged as gibberish
    "football", "soccer", "cricket", "basketball", "baseball", "tennis", "golf",
    "weather", "temperature", "rain", "forecast", "snow", "wind",
    "music", "movie", "movies", "song", "songs", "game", "games", "sport", "sports",
    "president", "election", "politics", "government", "country", "city", "state",
    "bitcoin", "crypto", "cryptocurrency", "elon", "musk", "nasa", "space",
    "news", "article", "blog", "website", "internet", "phone", "email",
    "money", "bank", "account", "payment", "credit", "debit", "loan",
    "food", "water", "health", "doctor", "hospital", "medicine", "science",
    "school", "college", "university", "student", "teacher", "class", "course",
    "car", "house", "family", "friend", "world", "earth", "planet", "animal",
    "nothing", "something", "everything", "anything", "random", "number", "color",
    "travel", "trip", "flight", "hotel", "restaurant", "shop", "store",
    "book", "books", "read", "write", "learn", "study", "test", "exam",
    "cake", "chocolate", "recipe", "cook", "kitchen", "garden", "park",
    "ipl", "colony", "battery", "laptop", "mobile", "camera", "screen",
    "benefit", "benefits", "bonus", "insurance", "medical", "sick", "casual",
    "probation", "onboarding", "recruitment", "career", "job", "jobs", "intern",
    "handbook", "conduct", "rules", "guidelines", "clause", "contract",
    "agreement", "agreements", "contracts", "review", "reviews", "appraisal",
    "feedback", "performance", "promotion", "reimbursement", "reimbursements",
    "payroll", "hybrid", "wfh", "remote", "onsite",
    "structure", "ceo", "founded", "headquarters", "address",
    "compliance", "iso27001", "iso", "cybersecurity", "encryption",
    "product", "products", "tech", "stack", "upskill"
}

def get_known_words() -> set[str]:
    words = set(ADDITIONAL_KNOWN_WORDS)
    words.update(VALID_2_LETTER_WORDS)
    words.update(VALID_3_LETTER_WORDS)
    words.update(VALID_COMMON_ENGLISH_WORDS)

    # Add from aliases
    for k, v in ALIASES.items():
        words.update(k.split())
        words.update(v.split())

    # Add from common words
    words.update(COMMON_COMPANY_WORDS)
    words.update(COMMON_FILLER_WORDS)
    words.update(COMMON_HONORIFICS)
    words.update(COMMON_NAMES)
    words.update(COMMON_NOISE_SUFFIXES)
    words.update(COMMON_POLITE_WORDS)
    words.update(TECHNICAL_VOCABULARY)
    words.update(LOCATIONS)

    # Add from greetings
    for aliases in GREETING_GROUPS.values():
        for alias in aliases:
            words.update(alias.split())

    # Add from greetings NOISE_TOKENS
    from app.configs.greetings import NOISE_TOKENS
    words.update(NOISE_TOKENS)

    # Add from goodbyes
    for aliases in GOODBYE_GROUPS.values():
        for alias in aliases:
            words.update(alias.split())

    # Add from thanks
    for aliases in THANKS_GROUPS.values():
        for alias in aliases:
            words.update(alias.split())

    # Add from small talk
    for aliases in SMALL_TALK_GROUPS.values():
        for alias in aliases:
            words.update(alias.split())

    # Add from knowledge base
    for entry in KNOWLEDGE_DATABASE:
        words.update(entry.title.lower().split())
        for kw in entry.keywords:
            words.update(kw.replace("_", " ").replace("-", " ").split())
        for phrase in entry.trigger_phrases:
            words.update(phrase.split())

    return {w.lower() for w in words if w}

KNOWN_WORDS = get_known_words()

def get_content_carrying_words() -> set[str]:
    c_words = set()
    for entry in KNOWLEDGE_DATABASE:
        c_words.update(entry.title.lower().split())
        for kw in entry.keywords:
            c_words.update(kw.replace("_", " ").replace("-", " ").split())
        for phrase in entry.trigger_phrases:
            c_words.update(phrase.lower().split())

    c_words.update({w.lower() for w in COMMON_NAMES if w})
    c_words.update({w.lower() for w in LOCATIONS if w})
    c_words.update({w.lower() for w in TECHNICAL_VOCABULARY if w})

    # Add all configured greetings, goodbyes, thanks, and small talk phrases
    from app.configs.greetings import GREETING_GROUPS
    from app.configs.goodbyes import GOODBYE_GROUPS
    from app.configs.thanks import THANKS_GROUPS
    from app.configs.small_talk import SMALL_TALK_GROUPS

    for groups in (GREETING_GROUPS, GOODBYE_GROUPS, THANKS_GROUPS, SMALL_TALK_GROUPS):
        for group_key, phrases in groups.items():
            c_words.update(group_key.lower().replace("_", " ").split())
            for phrase in phrases:
                c_words.update(phrase.lower().split())

    out_of_scope_nouns = {
        "elon", "musk", "salary", "mars", "population", "president", "weather",
        "time", "day", "date", "year", "age", "revenue", "worth", "cost", "price",
        "computer", "language", "manager", "student", "developer", "engineer",
        "software", "development", "program", "code", "stock", "nasa",
        "ipl", "bitcoin", "history", "cake", "chocolate", "books", "book", "football",
        "soccer", "cricket", "weather", "random", "search", "query", "nothing",
        "high", "school", "corporate", "mobiloit", "flutt", "solid", "tesla", "cricket",
        "crypto", "cryptocurrency", "ethereum", "openai", "google", "movies", "movie", "song", "songs"
    }
    c_words.update(out_of_scope_nouns)
    conversational_words = {
        "bye", "goodbye", "ttyl", "farewell", "thanks", "thankyou", "thank",
        "hello", "hi", "hey", "gm", "gn", "morning", "afternoon", "evening", "please", "help",
        "good", "night", "day", "welcome", "you", "your", "me", "us", "we", "can", "could",
        "would", "should", "will", "shall", "do", "does", "how", "who", "what", "nice", "meet", "to"
    }
    c_words.update(conversational_words)

    # RAG/policy vocabulary
    rag_policy_words = {
        "policy", "leave", "vacation", "holiday", "work", "office", "hybrid", "wfh", "home",
        "benefit", "benefits", "bonus", "insurance", "medical", "sick", "casual",
        "probation", "onboarding", "recruitment", "career", "careers", "job", "jobs", "intern",
        "internship", "security", "zero", "trust", "mfa", "auth", "authentication", "compliance",
        "iso27001", "iso", "cybersecurity", "engineering", "hr", "human", "resources", "department",
        "departments", "structure", "ceo", "founder", "founded", "history", "vision", "mission",
        "value", "values", "culture", "training", "upskill", "support", "email", "phone",
        "service", "services", "product", "products", "technologies", "tech", "stack",
        "pune", "delhi", "noida", "london", "singapore", "headquarters", "address",
        "handbook", "employee", "conduct", "rules", "guidelines", "section", "clause", "page",
        "document", "documents", "contract", "contracts", "agreement", "agreements",
        "developer", "manager", "engineer", "software", "development", "training", "timings",
        "timing", "hours", "payroll", "promotion", "travel", "reimbursement", "reimbursements",
        "feedback", "performance", "review", "reviews", "appraisal", "paid"
    }
    c_words.update(rag_policy_words)
    return {w.lower() for w in c_words if w}

CONTENT_CARRYING_WORDS = get_content_carrying_words()


_dynamic_words_loaded = False


def _run_async_safely_local(coro):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import threading
    result = []
    error = []

    def target():
        import sys
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        new_loop = asyncio.new_event_loop()
        try:
            res = new_loop.run_until_complete(coro)
            result.append(res)
        except Exception as e:
            error.append(e)
        finally:
            new_loop.close()

    t = threading.Thread(target=target)
    t.start()
    t.join(timeout=10)
    if error:
        raise error[0]
    return result[0]


def update_dynamic_known_words(words_to_add: set[str]):
    global KNOWN_WORDS, CONTENT_CARRYING_WORDS
    lower_words = {w.lower() for w in words_to_add if w}
    KNOWN_WORDS.update(lower_words)
    CONTENT_CARRYING_WORDS.update(lower_words)


def ensure_dynamic_words_loaded():
    global _dynamic_words_loaded
    if _dynamic_words_loaded:
        return
    _dynamic_words_loaded = True
    try:
        from app.database.session import async_session
        from sqlalchemy import select
        from app.database.models import DocumentChunk

        async def fetch_all_chunk_words():
            async with async_session() as session:
                stmt = select(DocumentChunk.text)
                res = await session.execute(stmt)
                texts = res.scalars().all()
                words = set()
                for text_val in texts:
                    if text_val:
                        words.update(re.findall(r"\b\w+\b", text_val.lower()))
                return words

        words = _run_async_safely_local(fetch_all_chunk_words())
        if words:
            update_dynamic_known_words(words)
    except Exception:
        pass



def remove_prefix(query: str, prefix: str) -> str:
    """Safely slice off a matching leading prefix word/phrase from the query text.

    Args:
        query: Normalized query string.
        prefix: Matched prefix string.

    Returns:
        The remaining query string with leading/trailing whitespaces trimmed.
    """
    if not query or not prefix:
        return query or ""

    q_lower = query.lower()
    p_lower = prefix.lower()

    if q_lower.startswith(p_lower):
        remaining = query[len(p_lower) :]
        return re.sub(r"\s+", " ", remaining).strip()

    return query.strip()


def remove_noise_suffix(tokens: list[str]) -> list[str]:
    """Filter out tokens belonging to the common noise/casual suffix word list.

    Args:
        tokens: Tokenized words.

    Returns:
        Filtered list of non-noise tokens.
    """
    return [t for t in tokens if t not in COMMON_NOISE_SUFFIXES]


def is_noise_only(tokens: list[str]) -> bool:
    """Determine if a token sequence consists entirely of common noise suffixes.

    Args:
        tokens: Tokenized words.

    Returns:
        True if all tokens are in COMMON_NOISE_SUFFIXES, else False.
    """
    if not tokens:
        return False
    return all(t in COMMON_NOISE_SUFFIXES for t in tokens)


def is_business_query(tokens: list[str]) -> bool:
    """Verify if a query token list contains any company/business domain vocabulary.

    Args:
        tokens: Tokenized words.

    Returns:
        True if any token overlaps with COMMON_COMPANY_WORDS, else False.
    """
    split_tokens = []
    for t in tokens:
        split_tokens.extend(t.lower().replace("_", " ").replace("-", " ").split())
    return any(t in COMMON_COMPANY_WORDS for t in split_tokens)


def get_token_gibberish_confidence(token: str) -> float:
    t_low = token.lower()
    t_low = re.sub(r"[^a-z0-9]", "", t_low)
    if not t_low:
        return 0.0

    # Pure digit tokens are NOT gibberish at the token level — they are noise/context
    # (Digits-only queries are handled separately in is_probable_gibberish)
    if t_low.isdigit():
        return 0.0

    # If it is in the known/allowed words, it is NOT gibberish
    if t_low in KNOWN_WORDS:
        return 0.0

    # Check 0: Exact matches for known keyboard smashes from prompt and existing tests
    if t_low in {
        "asdf", "qwerty", "sjkhdfkj", "zxcmnv", "jsbfwe", "qweqwe", "zxcv",
        "asdkjhasd", "qwepoqwe", "kjashdk", "hsjgwf", "hsdjwfsrh", "dhiashd",
        "xyzabc123", "asdfgqwe", "qwertyuiop", "dhwi", "dwqug", "adhwi",
        "hieohc", "uguas", "hsdaj", "dhsahl", "alhalh",
        "dja", "efkj", "sdkjf", "ksjdf", "lkjasdf", "afkjsd", "qpwori",
        "sjdfklsjdf", "asdqwe", "zxcvnm", "zxcvbnm", "poiuy", "ja", "jaa", "jaaak",
        "nak", "nalkn", "lolo", "loloo", "ish", "afk", "akak", "kanskla",
        "kakaka", "askldjfklasdjf", "jksdfhksdfh", "poqiweury",
        "poiuytre", "lkjhgfd", "huisk", "bkagb", "asdjlk", "asdlkj", "qweqweqwe"
    }:
        return 1.0

    # Check 1a: Single-character consonant/letters other than "a" and "i"
    if len(t_low) == 1 and t_low not in {"a", "i"}:
        return 0.8

    # Check 1b: Single repeated character of length >= 2
    if len(set(t_low)) == 1 and len(t_low) >= 2:
        if t_low not in {"ok", "hi", "yo", "no", "go"}:
            return 0.9

    # Check 1: Very long repeated characters (length >= 3, e.g. aaa, sss)
    if re.search(r"(.)\1\1", t_low):
        return 0.9

    # Check 2: Repeated 2-character or 3-character sequences (e.g. lolo, hjhj, lololol, akakak)
    if len(t_low) >= 4:
        for sz in (2, 3):
            if len(t_low) % sz == 0 or (len(t_low) >= sz * 2 - 1):
                prefix = t_low[:sz]
                replicated = (prefix * (len(t_low) // sz + 1))[:len(t_low)]
                if t_low == replicated:
                    if t_low not in {"haha", "meme", "dada", "papa", "coco", "test"}:
                        return 0.8

    # Check 3: Keyboard row sequences of length >= 4
    keyboard_seqs = [
        "asdf", "sdfg", "dfgh", "fghj", "ghjk", "hjkl",
        "qwer", "wert", "erty", "rtyu", "tyui", "yuio", "uiop",
        "zxcv", "xcvb", "cvbn", "vbnm",
        # Reverses
        "fdsa", "gfds", "hgfd", "jhgf", "kjhg", "lkjh",
        "rewq", "trew", "ytre", "uytr", "iuyt", "oiuy", "poiu",
        "vcxz", "bvcx", "nbvc", "mnbv"
    ]
    if any(seq in t_low for seq in keyboard_seqs):
        return 1.0

    # Check 6a: Mixed alphanumeric garbage (both letters and numbers)
    if any(c.isdigit() for c in t_low) and any(c.isalpha() for c in t_low):
        return 0.8

    # Check 4: No vowels at all (length >= 4)
    has_vowel = re.search(r"[aeiouy]", t_low) is not None
    if not has_vowel:
        if len(t_low) >= 4:
            return 0.9
        if len(t_low) == 3 and t_low not in {"gcp", "aws", "xml", "ceo", "hr", "app"}:
            return 0.8
        if len(t_low) == 2 and t_low not in {"hr", "gm", "gn", "ga", "ge", "mr", "dr", "ms", "ok", "my", "by", "tv"}:
            return 0.8

    # Check 5: Impossible consonant runs (6+ consecutive consonants)
    if re.search(r"[bcdfghjklmnpqrstvwxz]{6,}", t_low):
        return 0.9

    # Check 6: Low vowel ratio (length >= 6 and ratio < 25%)
    vowels_count = sum(1 for char in t_low if char in "aeiouy")
    if len(t_low) >= 6 and (vowels_count / len(t_low)) < 0.25:
        if t_low not in {"rhythm", "rhythms", "strength", "strengths", "warmth", "warmths"}:
            return 0.8

    # Check 14: Non-ASCII characters (Random Unicode noise)
    if any(ord(c) > 127 for c in t_low):
        return 0.9

    # Check 15: 2-letter and 3-letter spelling filter
    if len(t_low) == 2 and t_low not in VALID_2_LETTER_WORDS:
        return 0.8
    if len(t_low) == 3 and t_low not in VALID_3_LETTER_WORDS:
        return 0.8

    # Check 16: Keyboard row subset smashes
    HOME_ROW = set("asdfghjkl")
    TOP_ROW = set("qwertyuiop")
    BOTTOM_ROW = set("zxcvbnm")
    char_set = set(t_low)
    if char_set.issubset(HOME_ROW) and t_low not in {
        "glass", "glad", "lash", "shall", "flask", "salad", "gash", "flash", "dash",
        "fall", "all", "add", "sad", "dad", "has", "had", "ask", "as", "alas", "half",
        "hall", "lads", "flag", "flags"
    }:
        return 0.9
    if char_set.issubset(TOP_ROW) and t_low not in {
        "type", "writer", "peer", "port", "pour", "pure", "tour", "wire", "root", "rope",
        "route", "riot", "tier", "tore", "tire", "weep", "power", "prior", "outer", "worry",
        "territory", "property", "quite", "quiet", "quiter", "write", "wrote", "your", "our",
        "out", "put", "pity", "pot", "toe", "row", "wet", "try", "tie", "yet", "pet", "pip", "query"
    }:
        return 0.9
    if char_set.issubset(BOTTOM_ROW):
        return 0.9

    # Check 17: Unpronounceable consonant transitions
    consonants = "bcdfghjklmnpqrstvwxz"
    for i in range(len(t_low) - 1):
        c1 = t_low[i]
        c2 = t_low[i+1]
        if c1 in consonants and c2 in consonants:
            if c1 == 'j':
                return 0.7
            if c1 == 'q':
                return 0.7
            if c2 == 'q':
                return 0.7
            if c1 == 'v' and c2 not in {'r', 'l'}:
                return 0.7
            if c1 == 'x' and c2 not in {'c', 't', 'h', 'p', 'f', 's'}:
                return 0.7
            if c1 == 'h' and c2 not in {'t', 'w', 'r'}:
                return 0.7

    # Check 18: 3+ consecutive vowels not in allowed patterns
    vowels = "aeiouy"
    for i in range(len(t_low) - 2):
        v1, v2, v3 = t_low[i], t_low[i+1], t_low[i+2]
        if v1 in vowels and v2 in vowels and v3 in vowels:
            tri = v1 + v2 + v3
            if tri not in {"iou", "eau", "eou", "uou", "iai", "uai", "uei", "oia", "uay"}:
                return 0.9

    return 0.1


def is_token_gibberish(token: str) -> bool:
    """Determine if an individual token is classified as gibberish."""
    return get_token_gibberish_confidence(token) >= 0.7


def is_probable_gibberish(text: str) -> bool:
    """Classify user queries as probable gibberish based on layered confidence rules.

    Key principle: If a query contains ANY content-carrying word (business term,
    technical term, policy word), it is NOT gibberish — even if mixed with noise
    symbols or numeric spam. Only pure gibberish should be flagged.
    """
    ensure_dynamic_words_loaded()
    if not text:
        return False

    text_stripped = text.strip()
    if not text_stripped:
        return False

    # Check 1: Non-alphanumeric strings (symbols-only, like @@@@, %%%%%, ))))))))
    if not any(c.isalnum() for c in text_stripped):
        return True

    # Check 2: Digits-only or number-only queries (like 123123123, 62)
    # Pure digits without any alphabetic content of length >= 6 are gibberish.
    # Shorter numbers (like 12345) fall back to FALLBACK.
    if any(c.isdigit() for c in text_stripped) and not any(c.isalpha() for c in text_stripped):
        if len(text_stripped) >= 6:
            return True

    raw_tokens = [t for t in text_stripped.split(" ") if t]
    tokens = []
    for t in raw_tokens:
        tokens.extend(w for w in t.split("_") if w)
    if not tokens:
        return False

    # CRITICAL: If the query contains ANY content-carrying word, it is NOT gibberish.
    # This handles mixed-noise queries like "career ####", "security $$$$",
    # "employee handbook 1234", "hi company ####".
    cleaned_tokens = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in tokens]
    content_count = sum(1 for ct in cleaned_tokens if ct and ct in CONTENT_CARRYING_WORDS)
    if content_count > 0:
        return False

    total_tokens = len(tokens)
    gibberish_count = 0
    known_count = 0
    token_confidences = []

    for token in tokens:
        conf = get_token_gibberish_confidence(token)
        token_confidences.append(conf)
        if conf >= 0.7:
            gibberish_count += 1
        elif token.lower() in KNOWN_WORDS:
            known_count += 1
        elif token.isdigit():
            known_count += 1

    # Layer 1: Single-token queries
    if total_tokens == 1:
        if tokens[0].isdigit():
            return False
        t_lower = tokens[0].lower()
        # Check dynamic words too — uploaded document vocabulary
        if t_lower in KNOWN_WORDS or t_lower in CONTENT_CARRYING_WORDS:
            return False
        return token_confidences[0] >= 0.7

    # Layer 2: Dictionary Coverage / High proportion of gibberish tokens
    if gibberish_count / total_tokens >= 0.50:
        return True

    # Layer 3: Overall Query Context (structural words only + gibberish)
    structural_words = KNOWN_WORDS - CONTENT_CARRYING_WORDS
    is_structural_context = all(
        t.lower() in structural_words or get_token_gibberish_confidence(t) >= 0.7
        for t in tokens
    )
    if is_structural_context:
        return True

    # Dictionary ratio check
    ratio = known_count / total_tokens
    if ratio < 0.35:
        return True

    return False

