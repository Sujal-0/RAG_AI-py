"""Text normalization configurations.

Contains static dictionary maps for correcting misspelled greetings
and normalizing text queries.
"""

SPELLING_CORRECTIONS: dict[str, str] = {
    "helo": "hello",
    "hlo": "hello",
    "hlw": "hello",
    "helloo": "hello",
    "hellooo": "hello",
    "helllo": "hello",
    "hellp": "hello",
    "goodmorning": "good morning",
    "goodmorninggg": "good morning",
    "gmng": "good morning",
    "gudmorning": "good morning",
    "gudmrng": "good morning",
    "goodafternoon": "good afternoon",
    "goodevening": "good evening",
    "goodnight": "good night",
    "hiiii": "hi",
    "hii": "hi",
    "hiiie": "hi",
    "hiie": "hi",
    "hy": "hi",
    "hyy": "hi",
    "hithere": "hi there",
    "heyyy": "hey",
    "heyy": "hey",
    "heya": "hey",
    "heyya": "hey",
}
