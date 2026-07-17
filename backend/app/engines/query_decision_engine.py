"""Query Decision Engine.

Classifies incoming normalized and resolved queries into a single routing action
and extracts prefix metadata flags for mixed-query parsing.

Routing priority:
1. EMPTY
2. GIBBERISH (symbol-only)
3. Mixed query parsing (greeting/goodbye/thanks/small_talk prefix stripping)
4. Pure conversational (greeting/goodbye/thanks/small_talk only)
5. RAG (dynamic vocabulary match + static keyword match) — BEFORE FastPath
6. FASTPATH (deterministic company knowledge)
7. FALLBACK
"""

import re
import time
import logging
import difflib
from app.configs.knowledge import KNOWLEDGE_DATABASE
from app.configs.greetings import GREETING_GROUPS
from app.configs.goodbyes import GOODBYE_GROUPS
from app.configs.thanks import THANKS_GROUPS
from app.configs.small_talk import SMALL_TALK_GROUPS
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult
from app.utils.conversation import is_probable_gibberish

logger = logging.getLogger("app")

# Words that represent dynamic policies and MUST ALWAYS go to RAG, never FastPath
DYNAMIC_POLICY_WORDS = {
    "leave", "vacation", "paid", "hybrid", "wfh", "home", "security",
    "hr", "benefits", "hours", "timings", "timing", "working", "payroll",
    "promotion", "travel", "reimbursement", "reimbursements", "handbook",
    "conduct", "rules", "guidelines", "appraisal", "bonus", "salary",
    "cybersecurity", "zero", "trust", "mfa", "performance", "review",
    "recruitment", "onboarding", "probation", "sick", "casual", "medical",
    "insurance", "compliance", "iso27001", "encryption", "architecture",
    "microservices", "kafka", "rabbitmq", "oauth", "jwt", "devops",
    "api", "documentation", "swagger", "rest", "graphql",
}

# Cache for indexed document vocabulary
_indexed_vocab_cache: dict[str, set[str]] | None = None
_indexed_vocab_timestamp: float = 0.0


_vocab_refreshing = False

def _get_indexed_vocabulary() -> dict[str, set[str]]:
    """Fetch indexed document vocabulary from the database (cached, background refreshed)."""
    global _indexed_vocab_cache, _indexed_vocab_timestamp, _vocab_refreshing
    import time as time_mod
    import asyncio
    import threading

    def bg_refresh():
        global _vocab_refreshing, _indexed_vocab_cache, _indexed_vocab_timestamp
        try:
            from app.database.session import async_session
            from app.repositories.document_repository import DocumentRepository
            
            async def fetch():
                async with async_session() as session:
                    return await DocumentRepository.get_indexed_vocabulary(session)

            import sys
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            new_loop = asyncio.new_event_loop()
            vocab = new_loop.run_until_complete(fetch())
            new_loop.close()
            
            _indexed_vocab_cache = vocab
            _indexed_vocab_timestamp = time_mod.time()
        except Exception as e:
            logger.debug("Background vocab refresh failed: %s", e)
        finally:
            _vocab_refreshing = False

    def trigger_refresh():
        global _vocab_refreshing
        if not _vocab_refreshing:
            _vocab_refreshing = True
            t = threading.Thread(target=bg_refresh)
            t.daemon = True
            t.start()

    from app.database.session import db_is_available
    if not db_is_available:
        return {"filenames": set(), "headings": set(), "sections": set()}

    # If we have cache, return it immediately. Trigger refresh if > 50s old.
    if _indexed_vocab_cache is not None:
        if (time_mod.time() - _indexed_vocab_timestamp) > 50:
            trigger_refresh()
        return _indexed_vocab_cache

    # First time fetch - we MUST block to get initial data
    try:
        try:
            asyncio.get_running_loop()
            # On event loop - spawn thread and wait
            trigger_refresh()
            # We can't block easily, so we just return empty temporarily while it fetches
            # Wait, at startup we'll warm this up. If it happens here, just return empty and let it fetch.
            return {"filenames": set(), "headings": set(), "sections": set()}
        except RuntimeError:
            # Not on event loop, run directly
            from app.database.session import async_session
            from app.repositories.document_repository import DocumentRepository
            async def fetch_direct():
                async with async_session() as session:
                    return await DocumentRepository.get_indexed_vocabulary(session)
            _indexed_vocab_cache = asyncio.run(fetch_direct())
            _indexed_vocab_timestamp = time_mod.time()
            return _indexed_vocab_cache
    except Exception as e:
        logger.debug("Initial vocab fetch skipped: %s", e)

    return {"filenames": set(), "headings": set(), "sections": set()}


def _query_matches_indexed_docs(query_words: set[str]) -> bool:
    """Check if any query words match indexed document filenames, headings, or sections."""
    vocab = _get_indexed_vocabulary()
    if not any(vocab.values()):
        return False

    # Check each query word against filenames, headings, sections
    for word in query_words:
        if len(word) < 3:
            continue
        for category in ("filenames", "headings", "sections"):
            for entry in vocab.get(category, set()):
                # Check if the word appears in the entry or vice versa
                if word in entry or entry in word:
                    return True
                # Check if entry words overlap with query words
                entry_words = set(entry.split())
                if word in entry_words:
                    return True
    return False


def is_rag_candidate(query: str) -> bool:
    """Determine if a query is a candidate for document-based retrieval."""
    from app.utils.conversation import ensure_dynamic_words_loaded
    ensure_dynamic_words_loaded()
    query_lower = query.lower()
    words = set(re.findall(r"\b\w+\b", query_lower))

    # Out of scope terms which should route to Fallback naturally
    out_of_scope = {
        "bitcoin", "btc", "crypto", "cryptocurrency", "mars", "colony", "space", "nasa",
        "football", "soccer", "cricket", "ipl", "weather", "temperature", "rain", "forecast",
        "president", "election", "politics", "revenue", "worth", "net",
        "news", "sports", "movie", "movies", "music", "song", "songs", "game", "games",
        "elon", "musk", "population", "tesla", "ethereum", "openai", "google"
    }
    if words.intersection(out_of_scope):
        return False

    # Check against dynamic policy words (always RAG)
    if words.intersection(DYNAMIC_POLICY_WORDS):
        return True

    # Check against indexed document vocabulary (dynamic)
    if _query_matches_indexed_docs(words):
        return True

    # Corporate/Policy/Document keywords (static)
    rag_keywords = {
        "policy", "leave", "vacation", "holiday", "work", "office", "hybrid", "wfh", "home",
        "benefit", "benefits", "salary", "bonus", "insurance", "medical", "sick", "casual",
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
        "feedback", "performance", "review", "reviews", "appraisal",
        "architecture", "microservices", "kafka", "rabbitmq", "oauth", "jwt",
        "devops", "api", "documentation", "swagger", "rest", "graphql",
    }
    if words.intersection(rag_keywords):
        return True

    # Also support general business query contexts containing question indicators
    question_indicators = {
        "what", "where", "who", "why", "how", "when", "tell", "about", "info",
        "details", "information", "find", "explain", "summarize", "list", "show"
    }
    from app.configs.common import COMMON_COMPANY_WORDS, LOCATIONS, TECHNICAL_VOCABULARY
    if words.intersection(question_indicators):
        if (
            words.intersection(COMMON_COMPANY_WORDS)
            or words.intersection(LOCATIONS)
            or words.intersection(TECHNICAL_VOCABULARY)
        ):
            return True

    return False


def clean_term(s: str) -> str:
    """Helper to clean query term for matching."""
    s_clean = s.lower().replace("_", " ")
    s_clean = re.sub(r"[''']", "", s_clean)
    s_clean = re.sub(r"[?,.!;:()\-+=\[\]{}@#$%^&*~_/\\|<>]", " ", s_clean)
    return re.sub(r"\s+", " ", s_clean).strip()


def find_longest_match_phrase(query: str, group_dict: dict[str, list[str]]) -> tuple[str, str, list[int]] | None:
    """Find the longest matching phrase in a group dictionary."""
    query_clean = clean_term(query)
    tokens = query_clean.split()

    all_phrases = []
    for group_key, phrases in group_dict.items():
        for phrase in phrases:
            all_phrases.append((phrase, group_key))

    # Sort descending by word count, then char length
    all_phrases.sort(key=lambda x: (len(x[0].split()), len(x[0])), reverse=True)

    for phrase, group_key in all_phrases:
        p_clean = clean_term(phrase)
        p_words = p_clean.split()
        p_len = len(p_words)

        # Check boundary-safe match
        pattern = rf"\b{re.escape(p_clean)}\b"
        if re.search(pattern, query_clean):
            # Find indices
            matched_indices = []
            for i in range(len(tokens) - p_len + 1):
                if tokens[i:i+p_len] == p_words:
                    matched_indices = list(range(i, i+p_len))
                    break
            return phrase, group_key, matched_indices

    return None


class QueryDecisionEngine(BaseEngine):
    """Early-stage classifier routing queries to specific pipeline stages.

    Key routing principle: RAG eligibility is checked BEFORE FastPath matching.
    This ensures that document-related queries always reach the retrieval pipeline,
    even if they partially match a FastPath intent.
    """

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()

        raw_query = context.original_query or ""
        query = context.resolved_query or context.normalized_query or ""

        routing_audit_log = ["Normalization"]
        if context.metadata.get("matched_aliases"):
            routing_audit_log.append("Alias Resolution")

        # 1. Empty Check
        cleaned_raw = re.sub(r"[\s\u200b\u200c\u200d\ufeff]+", "", raw_query)
        if not cleaned_raw:
            decision = "EMPTY"
            routing_audit_log.append("Empty Check → EMPTY")
            context.metadata["decision"] = decision
            context.metadata["routing_audit_log"] = routing_audit_log
            return EngineResult(
                handled=False,
                reason_code="DECISION_EMPTY",
                metadata={"decision": decision, "why_chosen": "Input query is empty"}
            )

        # 2. Symbol-only Check (Cleaned to empty string after normalizer)
        if not query.strip():
            decision = "GIBBERISH"
            routing_audit_log.append("Symbol Check → GIBBERISH")
            context.metadata["decision"] = decision
            context.metadata["routing_audit_log"] = routing_audit_log
            return EngineResult(
                handled=False,
                reason_code="DECISION_GIBBERISH",
                metadata={"decision": decision, "why_chosen": "Input consists only of symbols or noise"}
            )

        # 3. Prefix Intent Resolution (Mixed query parsing)
        working_query = query
        has_greeting = False
        has_goodbye = False
        has_thanks = False
        has_small_talk = False

        # Greeting detection
        greet_match = find_longest_match_phrase(working_query, GREETING_GROUPS)
        if greet_match:
            has_greeting = True
            context.metadata["has_greeting"] = True
            phrase, canonical_greeting, matched_indices = greet_match
            words = clean_term(working_query).split()
            remaining_words = [words[i] for i in range(len(words)) if i not in matched_indices]
            working_query = " ".join(remaining_words)

        # Goodbye detection
        goodbye_match = find_longest_match_phrase(working_query, GOODBYE_GROUPS)
        if goodbye_match:
            has_goodbye = True
            context.metadata["has_goodbye"] = True
            phrase, canonical_goodbye, matched_indices = goodbye_match
            words = clean_term(working_query).split()
            remaining_words = [words[i] for i in range(len(words)) if i not in matched_indices]
            working_query = " ".join(remaining_words)

        # Thanks detection
        thanks_match = find_longest_match_phrase(working_query, THANKS_GROUPS)
        if thanks_match:
            has_thanks = True
            context.metadata["has_thanks"] = True
            phrase, canonical_thanks, matched_indices = thanks_match
            words = clean_term(working_query).split()
            remaining_words = [words[i] for i in range(len(words)) if i not in matched_indices]
            working_query = " ".join(remaining_words)

        # Small Talk detection
        small_talk_match = find_longest_match_phrase(working_query, SMALL_TALK_GROUPS)
        if small_talk_match:
            has_small_talk = True
            context.metadata["has_small_talk"] = True
            phrase, canonical_small_talk, matched_indices = small_talk_match
            words = clean_term(working_query).split()
            remaining_words = [words[i] for i in range(len(words)) if i not in matched_indices]
            working_query = " ".join(remaining_words)

        # Check if query remaining is just noise or names or empty
        remaining_clean = clean_term(working_query)
        ignorable_noise = {"sir", "bro", "team", "everyone", "mate", "guys", "madam", "boss", "dear", "all", "buddy", "friend", "there", "folks"}

        from app.configs.common import COMMON_NAMES
        names_and_noise = set(re.sub(r"[^a-z0-9]", "", n.lower()) for n in COMMON_NAMES if n)
        names_and_noise.update(ignorable_noise)
        names_and_noise.update({"raj", "chandan", "sujal", "john", "admin", "amit", "rohit", "priyanshu"})

        remaining_tokens = [t for t in remaining_clean.split() if t]
        remaining_cleaned_tokens = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in remaining_tokens]

        if all(ct in names_and_noise for ct in remaining_cleaned_tokens if ct):
            remaining_tokens = []

        # Extract parallel query_clean_raw (non-alias resolved query)
        working_query_raw = context.normalized_query or ""
        greet_match_raw = find_longest_match_phrase(working_query_raw, GREETING_GROUPS)
        if greet_match_raw:
            phrase, canonical_greeting, matched_indices = greet_match_raw
            words_raw = clean_term(working_query_raw).split()
            remaining_words_raw = [words_raw[i] for i in range(len(words_raw)) if i not in matched_indices]
            working_query_raw = " ".join(remaining_words_raw)

        goodbye_match_raw = find_longest_match_phrase(working_query_raw, GOODBYE_GROUPS)
        if goodbye_match_raw:
            phrase, canonical_goodbye, matched_indices = goodbye_match_raw
            words_raw = clean_term(working_query_raw).split()
            remaining_words_raw = [words_raw[i] for i in range(len(words_raw)) if i not in matched_indices]
            working_query_raw = " ".join(remaining_words_raw)

        thanks_match_raw = find_longest_match_phrase(working_query_raw, THANKS_GROUPS)
        if thanks_match_raw:
            phrase, canonical_thanks, matched_indices = thanks_match_raw
            words_raw = clean_term(working_query_raw).split()
            remaining_words_raw = [words_raw[i] for i in range(len(words_raw)) if i not in matched_indices]
            working_query_raw = " ".join(remaining_words_raw)

        small_talk_match_raw = find_longest_match_phrase(working_query_raw, SMALL_TALK_GROUPS)
        if small_talk_match_raw:
            phrase, canonical_small_talk, matched_indices = small_talk_match_raw
            words_raw = clean_term(working_query_raw).split()
            remaining_words_raw = [words_raw[i] for i in range(len(words_raw)) if i not in matched_indices]
            working_query_raw = " ".join(remaining_words_raw)

        remaining_clean_raw = clean_term(working_query_raw)
        remaining_tokens_raw = [t for t in remaining_clean_raw.split() if t not in ignorable_noise]

        # Strip name/noise from raw remaining tokens too
        remaining_cleaned_tokens_raw = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in remaining_tokens_raw]
        if all(ct in names_and_noise for ct in remaining_cleaned_tokens_raw if ct):
            remaining_tokens_raw = []
        query_clean_raw = " ".join(remaining_tokens_raw)

        if not remaining_tokens:
            # It was a pure conversational query (no core query left)
            if has_greeting:
                decision = "GREETING"
            elif has_goodbye:
                decision = "GOODBYE"
            elif has_thanks:
                decision = "THANKS"
            elif has_small_talk:
                decision = "SMALL_TALK"
            else:
                decision = "FALLBACK"

            context.metadata["decision"] = decision
            context.metadata["routing_audit_log"] = routing_audit_log
            return EngineResult(
                handled=False,
                reason_code=f"DECISION_{decision}",
                metadata={"decision": decision, "why_chosen": f"Conversational query resolved to {decision}"}
            )

        # Check if remainder is gibberish
        remainder_str = " ".join(remaining_tokens)
        if is_probable_gibberish(remainder_str):
            if has_greeting:
                decision = "GREETING"
            elif has_goodbye:
                decision = "GOODBYE"
            elif has_thanks:
                decision = "THANKS"
            elif has_small_talk:
                decision = "SMALL_TALK"
            else:
                decision = "GIBBERISH"

            context.metadata["decision"] = decision
            context.metadata["routing_audit_log"] = routing_audit_log
            return EngineResult(
                handled=False,
                reason_code=f"DECISION_{decision}",
                metadata={"decision": decision, "why_chosen": f"Query remainder resolved to {decision}"}
            )

        # 5. FastPath Intent Classification
        best_entry = None
        best_score = 0.0
        second_best_score = 0.0

        query_clean = " ".join(remaining_tokens)
        query_to_check = query_clean
        query_words = set(remaining_tokens)
        query_words_combined = query_words.union(set(remaining_tokens_raw))
        has_policy_words = bool(query_words.intersection(DYNAMIC_POLICY_WORDS))

        for entry in KNOWLEDGE_DATABASE:
            score = 0.0
            title_clean = clean_term(entry.title)
            intent_clean = clean_term(entry.intent_id)

            # Exact match check
            if query_clean in (title_clean, intent_clean) or query_clean_raw in (title_clean, intent_clean) or any(query_clean == clean_term(p) or query_clean_raw == clean_term(p) for p in entry.trigger_phrases):
                score = 1.00
            else:
                # Phrase match check
                for phrase in entry.trigger_phrases:
                    p_clean = clean_term(phrase)
                    if len(p_clean.split()) > 1:
                        if re.search(rf"\b{re.escape(p_clean)}\b", query_clean) or re.search(rf"\b{re.escape(p_clean)}\b", query_clean_raw):
                            score = 0.99
                            break

                if score == 0.0:
                    # Fuzzy Phrase check
                    if len(query_clean) > 4:
                        phrases = [clean_term(p) for p in entry.trigger_phrases]
                        for p in phrases:
                            p_words = set(p.split())
                            # Only run difflib if there's at least one word overlap
                            if p_words.intersection(query_words_combined):
                                if difflib.get_close_matches(query_clean, [p], n=1, cutoff=0.85):
                                    score = 0.90
                                    break

                if score == 0.0:
                    # Keyword overlap check
                    entry_kw_set = set(k.lower() for k in entry.keywords)
                    overlap = query_words_combined.intersection(entry_kw_set)
                    
                    if not overlap:
                        # Fuzzy keyword match - Optimized
                        for word in query_words_combined:
                            if len(word) > 4:
                                for kw in entry_kw_set:
                                    if abs(len(word) - len(kw)) <= 2:
                                        if word.startswith(kw[:3]) or kw.startswith(word[:3]):
                                            if difflib.get_close_matches(word, [kw], n=1, cutoff=0.80):
                                                overlap.add(kw)
                                                break
                                if overlap:
                                    break

                    if overlap:
                        if len(overlap) >= 2:
                            score = 0.95
                        elif len(overlap) == 1:
                            if len(query_words_combined) == 1 and len(entry.keywords) > 1:
                                score = 0.0
                            else:
                                score = 0.82

            if score >= entry.threshold:
                if score > best_score:
                    second_best_score = best_score
                    best_score = score
                    best_entry = entry
                elif score > second_best_score:
                    second_best_score = score

        # Ambiguity Handling
        if best_entry and 0.80 <= best_score < 0.99:
            if best_score - second_best_score < 0.15 and second_best_score > 0.0:
                best_entry = None
                routing_audit_log.append("FastPath match is ambiguous (score gap < 0.15) → FALLBACK")

        # 6. Routing Decision Logic (Smart FastPath)
        is_rag = has_policy_words or is_rag_candidate(query_to_check)

        if best_entry and best_score >= 0.82:
            # If it's explicitly document aware OR it's a RAG candidate but NOT an exact FastPath match
            if getattr(best_entry, "is_document_aware", False) or (is_rag and best_score < 1.0):
                decision = "RAG"
                routing_audit_log.append("RAG candidate overrides partial FastPath match → DELEGATED TO RAG")
                context.metadata["decision"] = decision
                context.metadata["routing_audit_log"] = routing_audit_log
                return EngineResult(
                    handled=False,
                    reason_code="DECISION_RAG",
                    metadata={"decision": decision, "why_chosen": "Query is a strong RAG candidate, bypassing partial FastPath"}
                )
            
            # Not a document query or it's an exact FastPath match
            decision = "FASTPATH"
            context.intent = best_entry.intent_id
            routing_audit_log.append(f"FastPath Intent Matched ({best_entry.intent_id}) → FASTPATH")
            context.metadata["decision"] = decision
            context.metadata["routing_audit_log"] = routing_audit_log
            return EngineResult(
                handled=False,
                reason_code="DECISION_FASTPATH",
                metadata={
                    "decision": decision,
                    "why_chosen": f"Input matches FastPath intent '{best_entry.intent_id}' with confidence {best_score}",
                    "fastpath_intent": best_entry.intent_id
                }
            )

        # 7. Fallback or RAG Check
        # Even if FastPath didn't match, we still route to RAG if it's a document query
        if is_rag:
            decision = "RAG"
            routing_audit_log.append("Eligible for RAG search → RAG")
            context.metadata["decision"] = decision
            context.metadata["routing_audit_log"] = routing_audit_log
            return EngineResult(
                handled=False,
                reason_code="DECISION_RAG",
                metadata={"decision": decision, "why_chosen": "Query is eligible for knowledge base document search"}
            )

        decision = "FALLBACK"
        routing_audit_log.append("No matches → FALLBACK")
        context.metadata["decision"] = decision
        context.metadata["routing_audit_log"] = routing_audit_log
        return EngineResult(
            handled=False,
            reason_code="DECISION_FALLBACK",
            metadata={"decision": decision, "why_chosen": "Query does not match any known intent or policy keywords"}
        )

    @property
    def name(self) -> str:
        return "QueryDecision"
