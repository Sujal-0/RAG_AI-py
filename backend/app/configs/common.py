"""Common configurations.

Consolidates ignorable suffixes, honorifics, common names, company words,
filler words, and polite tokens across all conversational engines.
"""

# Ignorable suffixes and casual address terms
COMMON_NOISE_SUFFIXES: set[str] = {
    "sir",
    "bro",
    "team",
    "everyone",
    "mate",
    "guys",
    "madam",
    "boss",
    "dear",
    "all",
    "mobiloitte",
    "buddy",
}

# Standard formal address titles
COMMON_HONORIFICS: set[str] = {"sir", "madam", "boss", "mr", "ms", "dr"}

# Names that might appear as address tokens
COMMON_NAMES: set[str] = {
    "raj",
    "chandan",
    "sujal",
    "amit",
    "rohit",
    "priyanshu",
    "khalid",
    "john",
    "smith",
    "david",
    "robert",
    "mary",
    "james",
    "michael",
    "william",
    "emily",
    "sarah",
    "karan",
    "aarav",
    "sam",
    "bob",
    "alice",
}

# Technical terms, frameworks, and tools whitelist
TECHNICAL_VOCABULARY: set[str] = {
    "react", "angular", "vue", "svelte", "django", "flask", "fastapi", "node", "nodejs",
    "spring", "laravel", "jquery", "nextjs", "nuxt", "python", "java", "javascript",
    "typescript", "rust", "kotlin", "scala", "swift", "html", "css", "sql", "php", "cpp",
    "solidity", "aws", "gcp", "azure", "devops", "docker", "kubernetes", "jenkins",
    "terraform", "github", "gitlab", "jira", "confluence", "blockchain", "ai", "ml",
    "iot", "cloud", "database", "server", "frontend", "backend", "fullstack", "mobile",
    "android", "ios", "app", "web", "website", "software", "hardware", "network",
    "security", "data", "analytics", "microservices", "api", "graphql", "rest", "soap",
    "git", "bitbucket", "vscode", "npm", "pip", "yarn", "composer", "maven", "gradle"
}

# Supported branch or region locations
LOCATIONS: set[str] = {
    "delhi", "pune", "noida", "india", "boston", "london", "singapore", "dubai",
    "sydney", "germany", "usa", "uk", "new york", "san francisco", "california"
}

# Domain vocabulary referencing the firm or business information queries
COMMON_COMPANY_WORDS: set[str] = {
    "mobiloitte",
    "office",
    "address",
    "branches",
    "location",
    "locations",
    "located",
    "branch",
    "careers",
    "career",
    "jobs",
    "solutions",
    "technologies",
    "recruitment",
    "hiring",
    "services",
    "internship",
    "timings",
    "timing",
    "company",
}

# Casual helper words used to frame queries
COMMON_FILLER_WORDS: set[str] = {
    "tell",
    "please",
    "can",
    "you",
    "me",
    "about",
    "info",
    "details",
    "information",
}

# Polite conversational expressions
COMMON_POLITE_WORDS: set[str] = {"please", "kindly", "thank", "thanks"}
