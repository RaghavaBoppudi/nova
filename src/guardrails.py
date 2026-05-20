import re

# Crisis response — always spoken verbatim, never modified
CRISIS_RESPONSE = (
    "I'm concerned about what you just said. "
    "Please reach out to the 988 Suicide and Crisis Lifeline by calling or texting 988. "
    "They're available 24 hours a day, 7 days a week, and they want to help."
)

DISTRESS_RESPONSE = (
    "I hear you, and I want you to know that what you're feeling is real and it matters. "
    "You are not alone. "
    "If you ever need someone to talk to, the 988 Suicide and Crisis Lifeline is available "
    "by calling or texting 988, any time of day."
)

# Tier 1 — Crisis and self-harm triggers
# These are checked first. Any match stops routing entirely.
CRISIS_PATTERNS = [
    r'\b(kill|hurt|harm)\s+(my)?self\b',
    r'\bsuicid(e|al|ally)\b',
    r'\bwant\s+to\s+(die|end\s+it|end\s+my\s+life)\b',
    r'\b(no\s+)?reason\s+to\s+(live|go\s+on)\b',
    r'\bcut(ting)?\s+(my)?self\b',
    r'\boverdos(e|ing)\b',
    r'\bself.harm\b',
    r'\bend\s+my\s+life\b',
    r'\bnot\s+worth\s+living\b',
    r'\bbetter\s+off\s+(dead|without\s+me)\b',
    r'\bdon.t\s+want\s+to\s+(be\s+here|exist|live)\b',
    r'\bgoodbye\s+(forever|for\s+good|cruel\s+world)\b',
    r'\b(pills?|medication)\s+(to\s+)?(kill|end|overdose)\b',

    # Softer distress signals
    r'\bno\s+point\s+in\s+(living|life|going\s+on|trying)\b',
    r'\blife\s+(feels?\s+)?(pointless|meaningless|worthless|hopeless)\b',
    r'\bcan.t\s+(go\s+on|do\s+this\s+anymore|take\s+it\s+anymore|keep\s+living)\b',
    r'\bI\s+wish\s+I\s+(was|were)\s+(never\s+born|dead|gone)\b',
    r'\bwish\s+I\s+(was|were)\s+(never\s+born|dead|gone)\b',
    r'\b(never\s+should\s+have\s+been\s+born)\b',
    r'\bhate\s+myself\b',
    r'\bwant\s+to\s+disappear\b',
    r'\btired\s+of\s+(living|life|everything|being\s+alive)\b',
    r'\bdon.t\s+want\s+to\s+wake\s+up\b',
    r'\bsee\s+no\s+(point|reason|purpose)\s+in\s+(living|life|going\s+on)\b',
    r'\bI\s+give\s+up\s+on\s+(life|everything|living)\b',
]

DISTRESS_PATTERNS = [
    r'\b(feel|feeling|felt)\s+(hopeless|worthless|like\s+a\s+burden|like\s+nothing\s+matters)\b',
    r'\bnobody\s+(cares?|loves?|needs?|wants?)\s*(about\s+me|for\s+me|me)\b',
    r'\beveryone\s+(would\s+be\s+better|is\s+better)\s+off\s+without\s+me\b',
    r'\bI\s+feel\s+(so\s+)?(alone|lonely|lost|empty|broken|invisible)\b',
    r'\bno\s+one\s+(understands?|cares?|loves?\s+me)\b',
    r'\bI\s+am\s+(so\s+)?(alone|lost|broken|invisible)\b',
]

# Tier 2 — Child safety blocks
# These are checked second. Any match returns a soft refusal.
CHILD_SAFETY_PATTERNS = [
    # Adult/sexual content
    r'\bporn(ography)?\b',
    r'\bsex(ual|ually)?\b',
    r'\bnude(s|ity)?\b',
    r'\bexplicit\s+content\b',
    r'\berotic\b',
    r'\bfetish\b',
    r'\bonlyfans\b',
    r'\bstrip(per|club|tease)?\b',

    # Violence
    r'\bhow\s+to\s+(kill|murder|assault|attack)\s+(a\s+)?(person|someone|people|man|woman|child|kid)\b',
    r'\bhow\s+(to|do\s+I|can\s+I)\s+make\s+(a\s+)?(bomb|weapon|explosive)\b',
    r'\bhow\s+to\s+(build|make|create)\s+(a\s+)?(gun|knife|weapon)\b',
    r'\btorture\b',
    r'\bbeheading\b',

    # Drugs and alcohol
    r'\bhow\s+to\s+(make|cook|produce|synthesize)\s+(meth|heroin|cocaine|fentanyl|crack|lsd|mdma)\b',
    r'\bhow\s+to\s+get\s+(drunk|high|wasted|stoned)\b',
    r'\bshow\s+me\s+(porn|nude|naked|explicit)\b',
    r'\bwhere\s+(can\s+I|do\s+I|to)?\s*(buy|get|find)\s+(drugs?|weed|cocaine|heroin|meth|pills?)\b',
    r'\bhow\s+to\s+get\s+(drugs?|weed|cocaine|heroin|meth)\b',

    # Hate speech
    r'\b(racial|ethnic)\s+slur\b',
    r'\bhate\s+speech\b',
]

# Tier 3 — Groq API error patterns (matched against LLM responses)
GROQ_ERROR_PATTERNS = [
    r'rate.limit',
    r'429',
    r'too\s+many\s+requests',
    r'context.length',
    r'maximum\s+context',
    r'i\s+cannot\s+provide',
    r'as\s+an\s+ai\s+language\s+model',
    r'i\s+am\s+unable\s+to\s+access',
]

CHILD_SAFETY_RESPONSE = "I can't help with that."
GROQ_ERROR_RESPONSE = "I'm having trouble with that right now. Please try again."

def check_input(text: str) -> tuple[str, str | None]:
    """
    Check user input against all guardrail tiers.

    Returns:
        ("pass", None) — safe to route normally
        ("crisis", CRISIS_RESPONSE) — active crisis, speak 988 immediately
        ("distress", DISTRESS_RESPONSE) — emotional distress, speak warm response
        ("block", CHILD_SAFETY_RESPONSE) — blocked content, speak soft refusal
    """
    text_lower = text.lower().strip()

    # Tier 1a — active crisis (highest priority)
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            _log_trigger("crisis", text)
            return "crisis", CRISIS_RESPONSE

    # Tier 1b — emotional distress
    for pattern in DISTRESS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            _log_trigger("distress", text)
            return "distress", DISTRESS_RESPONSE

    # Tier 2 — child safety
    for pattern in CHILD_SAFETY_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            _log_trigger("blocked", text)
            return "block", CHILD_SAFETY_RESPONSE

    return "pass", None

def check_output(text: str) -> tuple[str, str | None]:
    """
    Check LLM output for error responses or policy violations.

    Returns:
        ("pass", None) — output is fine
        ("error", GROQ_ERROR_RESPONSE) — LLM returned an error or refusal
    """
    text_lower = text.lower().strip()

    for pattern in GROQ_ERROR_PATTERNS:
        if re.search(pattern, text_lower):
            return "error", GROQ_ERROR_RESPONSE

    return "pass", None


def _log_trigger(trigger_type: str, text: str):
    """Log guardrail triggers locally for awareness. Never sent anywhere."""
    import os
    from datetime import datetime
    log_path = "nova_guardrail_log.txt"
    try:
        with open(log_path, "a") as f:
            f.write(f"{datetime.now().isoformat()} [{trigger_type.upper()}] {text[:100]}\n")
    except Exception:
        pass