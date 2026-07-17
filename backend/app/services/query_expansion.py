"""Synonym expansion and canonicalization service for improving pgvector retrieval quality.

Contains domain-specific synonym and canonical maps to format query text before embedding generation.
"""

import re

def expand_query(query: str) -> str:
    """Canonicalize business terms and expand query with synonyms for pgvector search."""
    if not query:
        return ""

    q_low = query.lower()

    # Topic Canonicalization maps
    # We replace synonymous words with canonical terms while preserving other search qualifiers.
    canonical_topics = [
        (
            {"leave", "leaves", "vacation", "vacations", "pto", "paid leave", "paid time off", "holiday", "holidays"},
            "vacation leave policy"
        ),
        (
            {"office", "offices", "location", "locations", "branch", "branches", "address", "headquarters", "head office"},
            "office locations address"
        ),
        (
            {"review", "reviews", "promotion", "promotions", "appraisal", "appraisals", "evaluation", "evaluations"},
            "performance appraisal review"
        ),
        (
            {"hybrid", "wfh", "remote", "home", "telecommute", "work from home"},
            "hybrid work policy"
        ),
        (
            {"structure", "hierarchy", "organization chart", "org chart", "org structure"},
            "organization structure hierarchy"
        ),
        (
            {"travel", "reimbursement", "reimbursements", "allowance", "allowances", "expenses"},
            "travel reimbursement expense policy"
        ),
        (
            {"intern", "interns", "internship", "internships", "student training"},
            "internship training opportunities"
        ),
        (
            {"service", "services", "offering", "offerings", "solution", "solutions", "product", "products"},
            "services offerings solutions capabilities products business units"
        ),
        (
            {"recruit", "recruiting", "recruitment", "hire", "hiring", "interview", "interviews", "candidate", "candidates", "career", "careers", "job", "jobs"},
            "hiring interview recruitment career candidate"
        ),
        (
            {"benefit", "benefits", "perk", "perks", "insurance"},
            "leave travel reimbursement insurance HR policy employee benefits"
        ),
        (
            {"architecture", "system architecture", "backend", "microservices"},
            "system architecture microservices backend kubernetes software architecture"
        ),
        (
            {"security", "cybersecurity", "infosec", "iso27001"},
            "cybersecurity zero trust ISO27001 MFA"
        )
    ]

    words = q_low.split()
    matched_topics = []

    # Replace matched words with their canonical topic string, keeping other words
    cleaned_words = []
    for word in words:
        clean_w = word.strip("?,.!:;()\"'")
        matched = False
        for synonym_set, canonical_term in canonical_topics:
            if clean_w in synonym_set:
                if canonical_term not in matched_topics:
                    matched_topics.append(canonical_term)
                matched = True
                break
        if not matched:
            cleaned_words.append(clean_w)

    # Combine canonical topics and remaining query words
    if matched_topics:
        canonical_query = " ".join(matched_topics) + " " + " ".join(cleaned_words)
        return canonical_query.strip()

    return q_low
