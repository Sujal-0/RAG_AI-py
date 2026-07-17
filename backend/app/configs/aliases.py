"""Alias configurations.

Defines synonym mappings to normalize query terms into canonical tokens.
"""

ALIASES: dict[str, str] = {
    "human resources": "human_resources",
    "human resource": "human_resources",
    "hr": "human_resources",
    "vacancy": "careers",
    "vacancies": "careers",
    "opening": "careers",
    "openings": "careers",
    "career": "careers",
    "job": "careers",
    "jobs": "careers",
    "office": "office_locations",
    "branch": "office_locations",
    "location": "office_locations",
    "address": "office_locations",
    "mail": "contact_details",
    "email": "contact_details",
    "phone": "contact_details",
    "contact": "contact_details",
    "artificial intelligence": "artificial_intelligence",
    "ai": "artificial_intelligence",
    "machine learning": "machine_learning",
    "ml": "machine_learning",
    "cloud": "cloud",
    "aws": "cloud",
    "azure": "cloud",
    "gcp": "cloud",
    "technology": "technologies",
    "tech": "technologies",
}
