import difflib

def test_fuzzy():
    query = "comapny overview"
    phrases = ["company overview", "about mobiloitte", "company history"]
    close = difflib.get_close_matches(query, phrases, n=1, cutoff=0.85)
    print("Phrase fuzzy:", close)
    
    query = "mision"
    phrases = ["mission", "vision", "overview"]
    close = difflib.get_close_matches(query, phrases, n=1, cutoff=0.8)
    print("Keyword fuzzy:", close)

test_fuzzy()
