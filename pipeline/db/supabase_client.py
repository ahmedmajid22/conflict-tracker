from supabase import create_client, Client
from loguru import logger
from pipeline.config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None


def get_client() -> Client:
    """
    Returns a singleton Supabase client.
    Raises ValueError if credentials are missing.
    """
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in your .env file"
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.debug("Supabase client initialised")
    return _client