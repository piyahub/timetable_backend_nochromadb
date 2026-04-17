# Simple profanity checker — no external dependencies needed
# Add more words to the list as needed

PROFANITY_LIST = [
    "fuck", "shit", "bitch", "asshole", "bastard", "damn", "crap",
    "ass", "dick", "cock", "pussy", "whore", "slut", "nigger", "nigga",
    "faggot", "retard", "cunt", "motherfucker", "bullshit", "piss",
    "wtf", "stfu", "fck", "fuk", "fvck", "sh1t", "b1tch", "a$$",
    # Hindi profanity (romanized)
    "madarchod", "bhenchod", "chutiya", "gaandu", "harami", "sala",
    "saala", "randi", "mc", "bc", "mf",
]

def contains_profanity(text: str) -> bool:
    """
    Returns True if the text contains any profanity.
    Checks whole words and common letter substitutions.
    """
    text_lower = text.lower()

    # Remove common punctuation for checking
    cleaned = text_lower.replace("!", "").replace("@", "a").replace(
        "0", "o").replace("1", "i").replace("3", "e").replace(
        "$", "s").replace("4", "a")

    words = cleaned.split()

    for word in words:
        # Strip punctuation from word edges
        word = word.strip(".,!?;:\"'()-")
        if word in PROFANITY_LIST:
            return True

    # Also check if any profanity appears as substring (catches concatenated words)
    for profanity in PROFANITY_LIST:
        if profanity in cleaned:
            return True

    return False


PROFANITY_RESPONSE = (
    "I'm here to help with timetable questions only. "
    "Please use respectful language and I'll be happy to assist you. 🙏"
)