"""Intents enumeration.

Defines the central categories of conversation intents resolved by engines.
"""

from enum import StrEnum


class Intent(StrEnum):
    """Categorized conversation intents returned by pipeline engines."""

    # Conversational Intents
    GREETING = "GREETING"
    GOODBYE = "GOODBYE"
    THANKS = "THANKS"
    SMALL_TALK = "SMALL_TALK"
    EMPTY_INPUT = "EMPTY_INPUT"
    GIBBERISH = "GIBBERISH"
    FALLBACK = "FALLBACK"
    UNKNOWN = "UNKNOWN"

    # Business/Knowledge base Intents
    COMPANY_OVERVIEW = "COMPANY_OVERVIEW"
    SERVICES = "SERVICES"
    AI_SERVICES = "AI_SERVICES"
    CLOUD_SERVICES = "CLOUD_SERVICES"
    WEB_DEVELOPMENT = "WEB_DEVELOPMENT"
    MOBILE_DEVELOPMENT = "MOBILE_DEVELOPMENT"
    BLOCKCHAIN = "BLOCKCHAIN"
    IOT = "IOT"
    CAREERS = "CAREERS"
    INTERNSHIP = "INTERNSHIP"
    OFFICE_LOCATIONS = "OFFICE_LOCATIONS"
    CONTACT_DETAILS = "CONTACT_DETAILS"
    COMPANY_VISION = "COMPANY_VISION"
    MISSION = "MISSION"
    VALUES = "VALUES"
    CULTURE = "CULTURE"
    TECHNOLOGIES = "TECHNOLOGIES"
    TRAINING = "TRAINING"
    SUPPORT = "SUPPORT"
    VISION_MISSION = "VISION_MISSION"
