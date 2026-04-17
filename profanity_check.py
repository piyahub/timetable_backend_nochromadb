# Profanity checker — uses whole-word matching only to avoid false positives
# "mf" inside "EMF", "ass" inside "class", "dick" inside "Frederick" etc.

PROFANITY_LIST = {
    "fuck", "shit", "bitch", "asshole", "bastard", "crap",
    "cock", "pussy", "whore", "slut", "nigger", "nigga",
    "faggot", "retard", "cunt", "motherfucker", "bullshit", "piss",
    "fck", "fuk", "fvck", "sh1t", "b1tch",
    # Hindi profanity (romanized)
    "madarchod", "bhenchod", "chutiya", "gaandu", "harami", "randi",
}

# These are checked as whole words only (not substrings)
# to avoid false positives like EMF, classic, assess, etc.

import re

def contains_profanity(text: str) -> bool:
    """
    Returns True only if a profanity word appears as a complete word.
    Uses word boundary matching to avoid false positives.
    """
    # Normalize: lowercase, replace common substitutions
    cleaned = text.lower()
    cleaned = cleaned.replace("@", "a").replace("0", "o").replace(
        "1", "i").replace("3", "e").replace("$", "s").replace("4", "a")

    # Extract words only (split on non-alphanumeric)
    words = set(re.findall(r'\b[a-z]+\b', cleaned))

    return bool(words & PROFANITY_LIST)


PROFANITY_RESPONSE = (
    "I'm here to help with timetable questions only. "
    "Please use respectful language and I'll be happy to assist you. 🙏"
)