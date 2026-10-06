import re

# Phrases recruiters put in their LinkedIn headline to catch AI-written outreach.
# Kept narrow on purpose: plain mentions of "LLM" or "AI" are common in tech recruiters' headlines.
AI_TRAP_PHRASES = (
    "if you are an ai", "if you're an ai", "if you are a bot", "if you're a bot",
    "if you are an llm", "if you're an llm", "if you are a language model", "if you're a language model",
    "if you are chatgpt", "if you're chatgpt", "ignore previous instructions", "ignore all previous",
    "ignore prior instructions", "ignore your instructions", "disregard previous instructions",
)

AI_TRAP_PATTERN = re.compile(r"\b(" + "|".join(re.escape(p) for p in AI_TRAP_PHRASES) + r")\b")


def has_ai_trap(text):
    return bool(AI_TRAP_PATTERN.search(text.lower().replace("’", "'")))
