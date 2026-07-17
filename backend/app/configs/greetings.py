"""Greetings engine configurations.

Defines canonical greeting groups, aliases, noise words, and responses.
"""

from app.configs.common import COMMON_NOISE_SUFFIXES

# Maps canonical greeting keys to lists of accepted alias patterns
GREETING_GROUPS: dict[str, list[str]] = {
    "hello": [
        "hello",
        "helo",
        "helloo",
        "hellooo",
        "helllo",
        "hellp",
        "heelo",
        "greetings",
        "welcome",
    ],
    "hi": [
        "hi",
        "hii",
        "hiii",
        "hiiii",
        "hiiie",
        "hiie",
        "hy",
        "hyy",
    ],
    "hey": [
        "hey",
        "heyy",
        "heyyy",
        "heya",
        "heyya",
        "hey there",
        "what's up",
        "whats up",
        "yo",
        "sup",
    ],
    "good morning": [
        "good morning",
        "goodmorning",
        "goodmorninggg",
        "gmng",
        "gudmorning",
        "gudmrng",
        "morning",
        "morninggg",
        "gm",
        "gud morning pineapple",
        "gud morning",
        "morning sujal",
    ],
    "good afternoon": ["good afternoon", "goodafternoon", "afternoon", "ga"],
    "good evening": ["good evening", "goodevening", "evening", "ge"],
    "good night": ["good night", "goodnight", "night", "nighttt", "gn"],
    "namaste": ["namaste", "namaskar", "pranam", "ram ram", "radhe radhe"],
    "vanakkam": ["vanakkam"],
    "satsriakal": ["satsriakal", "sat sri akal"],
    "adaab": ["adaab", "asalaam alaykum", "assalamualaikum", "salam"],
    "hola": ["hola"],
    "bonjour": ["bonjour", "salut"],
    "ciao": ["ciao"],
    "hallo": ["hallo", "guten tag"],
    "konnichiwa": ["konnichiwa", "konichiwa"],
}

# Removable greeting suffixes/names (all lowercase)
NOISE_TOKENS: set[str] = COMMON_NOISE_SUFFIXES | {
    "raj",
    "chandan",
    "sujal",
    "buddy",
    "friend",
    "john",
    "admin",
    "there",
    "folks",
}

# Timezone configurations
DEFAULT_TIMEZONE = "Asia/Kolkata"

# Configurable greeting time windows (start_hour, start_minute, end_hour, end_minute)
# 05:00 - 11:59 is morning
# 12:00 - 16:59 is afternoon
# 17:00 - 20:59 is evening
# 21:00 - 04:59 is night
GREETING_WINDOWS = {
    "good morning": {"start": (5, 0), "end": (11, 59)},
    "good afternoon": {"start": (12, 0), "end": (16, 59)},
    "good evening": {"start": (17, 0), "end": (20, 59)},
    "good night": {"start": (21, 0), "end": (4, 59)},
}

