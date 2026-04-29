import os
from dotenv import load_dotenv

load_dotenv()

# ── Supabase ─────────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# ── External APIs ────────────────────────────────────────
HF_API_TOKEN: str  = os.getenv("HF_API_TOKEN", "")
NEWSAPI_KEY: str   = os.getenv("NEWSAPI_KEY", "")
OPENCAGE_KEY: str  = os.getenv("OPENCAGE_KEY", "")
ACLED_KEY: str     = os.getenv("ACLED_KEY", "")

# ── Pipeline behaviour ───────────────────────────────────
PIPELINE_INTERVAL_MINUTES: int = int(os.getenv("PIPELINE_INTERVAL_MINUTES", "15"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── HuggingFace model ────────────────────────────────────
HF_MODEL = "cardiffnlp/twitter-roberta-base-sentiment"

HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

# ── RSS feeds (source_name, url) ─────────────────────────
RSS_FEEDS = [
    ("bbc",         "http://feeds.bbci.co.uk/news/world/middle_east/rss.xml"),
    ("bbc_world",   "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("reuters",     "https://feeds.reuters.com/reuters/worldNews"),
    ("al_jazeera",  "https://www.aljazeera.com/xml/rss/all.xml"),
    ("france24",    "https://www.france24.com/en/rss"),
    ("guardian",    "https://www.theguardian.com/world/rss"),
]

# ── Keywords to filter events (keep geopolitical/conflict topics) ─
CONFLICT_KEYWORDS = [
    "war", "conflict", "military", "attack", "strike", "missile",
    "sanction", "ceasefire", "troops", "invasion", "offensive",
    "bomb", "explosion", "casualties", "killed", "wounded",
    "diplomatic", "treaty", "nuclear", "siege", "blockade",
    "insurgent", "rebel", "protest", "coup", "crisis", "tension",
    "iran", "israel", "ukraine", "russia", "gaza", "sudan",
    "nato", "un", "pentagon", "irgc", "hamas", "hezbollah",
    "refugee", "humanitarian", "embargo", "sanctions",
    "china", "taiwan", "north korea", "south china sea",
]

# ── Named entities to track ──────────────────────────────
TRACKED_ENTITIES = {
    "Iran", "Islamic Republic", "IRGC", "Quds Force",
    "USA", "United States", "Pentagon", "US Army", "US Navy",
    "Russia", "Kremlin", "Putin", "FSB",
    "Ukraine", "Zelensky", "AFU",
    "Israel", "IDF", "Netanyahu", "Mossad",
    "Hamas", "Hezbollah", "Houthi", "ISIS", "ISIL",
    "NATO", "UN", "UNSC", "EU", "Arab League",
    "China", "PLA", "Xi Jinping",
    "Saudi Arabia", "MBS",
    "Gaza", "West Bank", "Kyiv", "Moscow",
    "Taliban", "Al-Qaeda",
}

# ── Category keyword mapping ─────────────────────────────
CATEGORY_KEYWORDS = {
    "military": [
        "attack", "strike", "missile", "troops", "military", "bomb",
        "explosion", "airstrike", "naval", "fighter", "soldier",
        "casualties", "killed", "wounded", "battle", "offensive",
        "ceasefire", "blockade", "siege", "invasion",
    ],
    "diplomatic": [
        "diplomatic", "talks", "negotiation", "treaty", "agreement",
        "summit", "meeting", "minister", "ambassador", "envoy",
        "embassy", "sanction", "resolution", "veto",
    ],
    "economic": [
        "sanction", "embargo", "oil", "gas", "trade", "economic",
        "currency", "inflation", "supply chain", "energy",
        "export", "import", "tariff",
    ],
    "humanitarian": [
        "refugee", "humanitarian", "aid", "civilian", "hospital",
        "food", "water", "shelter", "displaced", "crisis",
        "famine", "starvation",
    ],
    "social": [
        "protest", "demonstration", "riot", "election", "vote",
        "political", "opposition", "government", "parliament",
        "coup", "revolution",
    ],
}

# ── Request timeouts ─────────────────────────────────────
REQUEST_TIMEOUT = 15   # seconds
HF_TIMEOUT      = 20   # HuggingFace can be slow on free tier

# ── Geocoding cache TTL (seconds) ────────────────────────
GEOCODE_CACHE_TTL = 86400  # 24 hours — save API quota