"""Consolidated response registries.

Stores standard approved response arrays for greetings, goodbyes, gratitude,
silent inputs, and casual small talk intents.
"""

# Approved responses for Greetings (from greetings.py key mappings)
GREETING_RESPONSES: dict[str, list[str]] = {
    "hello": [
        "Hello! How can I assist you today?",
        "Hi there! What can I help you with?",
        "Greetings! How may I be of service?",
    ],
    "hi": [
        "Hi there! What can I help you with?",
        "Hello! How can I assist you today?",
    ],
    "hey": [
        "Hi there! What can I help you with?",
        "Hello! How can I assist you today?",
    ],
    "good morning": [
        "Good morning! Hope you have a wonderful start to your day. How can I help you today?",
        "Good morning! What can I assist you with this morning?",
    ],
    "good afternoon": [
        "Good afternoon! How is your day going? How can I help you today?",
        "Good afternoon! What can I do for you today?",
    ],
    "good evening": [
        "Good evening! How can I help you tonight?",
        "Good evening! What can I assist you with this evening?",
    ],
    "good night": [
        "Good night! Take care. If you need anything before you head off, I'm here to help.",
        "Good night! Sleep well and take care.",
        "Good night! Have a peaceful rest.",
    ],
    "namaste": [
        "Namaste! How can I assist you today?",
        "Namaste! Greetings to you.",
    ],
    "vanakkam": [
        "Vanakkam! How can I help you today?",
    ],
    "satsriakal": [
        "Sat Sri Akal! How can I assist you today?",
    ],
    "adaab": [
        "Adaab! How can I assist you today?",
        "Adaab! Hope you are doing well.",
    ],
    "hola": [
        "Hola! How can I assist you today?",
    ],
    "bonjour": [
        "Bonjour! How can I assist you today?",
    ],
    "ciao": [
        "Ciao! How can I assist you today?",
    ],
    "hallo": [
        "Hallo! How can I assist you today?",
    ],
    "konnichiwa": [
        "Konnichiwa! How can I assist you today?",
    ],
}

# Approved responses for Goodbye intents
GOODBYE_RESPONSES: dict[str, list[str]] = {
    "goodbye": [
        "Goodbye! Have a great day ahead.",
        "Bye! Take care and have a wonderful day.",
        "Goodbye! Hope to chat with you again soon.",
    ],
    "good night": [
        "Good night! Sleep well and take care.",
        "Good night! Have a peaceful rest.",
    ],
    "later": [
        "See you later! Take care.",
        "Catch you later! Have a good one.",
    ],
}

# Approved responses for Thanks intents
THANKS_RESPONSES: dict[str, list[str]] = {
    "thanks": [
        "You're very welcome! I'm happy to help.",
        "Anytime! Let me know if you need anything else.",
        "My pleasure! Glad I could assist.",
    ],
}

# Approved responses for EmptyInput intents
EMPTY_INPUT_RESPONSES: list[str] = [
    "I didn't catch that. Could you please type something?",
    "It seems you didn't type anything. How can I help you?",
    "Please type a query so I can assist you with Mobiloitte.",
]

# Approved responses for Gibberish intents
GIBBERISH_RESPONSES: list[str] = [
    "I'm not sure what you meant. Could you rephrase your question? I'm here to help with anything related to Mobiloitte.",
]

# Approved responses for SmallTalk sub-intents
SMALL_TALK_RESPONSES: dict[str, list[str]] = {
    "how are you": [
        "I am doing great, thank you! How can I assist you today?",
        "I'm up and running perfectly. How can I help you?",
    ],
    "who are you": [
        "I am the Mobiloitte AI assistant. I can answer questions about our services, offices, and careers.",
        "I'm the virtual assistant for Mobiloitte. How can I help you today?",
    ],
    "who built you": [
        "I was developed by the engineering team at Mobiloitte Technologies.",
        "I am built by Mobiloitte. We specialize in digital transformation and AI solutions.",
    ],
    "what can you do": [
        "I can help you learn about Mobiloitte's services, office locations, careers, and general details.",
        "Ask me about Mobiloitte's capabilities, jobs, addresses, or timings, and I will guide you.",
    ],
    "help": [
        "Sure, I'm here to assist! Ask me about Mobiloitte's services, office locations, or career opportunities.",
        "How can I help you? You can ask about our branches, tech solutions, or jobs.",
    ],
    "praise": [
        "Thank you! Glad you think so.",
        "Thanks! I appreciate the positive feedback.",
        "Awesome! Let me know if there's anything else you need.",
    ],
    "acknowledgement": [
        "Understood. Let me know if you have any questions.",
        "Okay. How can I help you next?",
        "Alright. What else can I assist you with?",
    ],
    "lol": [
        "Haha! Glad I could bring a smile.",
        "Haha! Let me know if you have any other questions.",
    ],
    "expression": [
        "Wow! Indeed.",
        "Oh! Understood. Let me know what you'd like to ask.",
    ],
}
