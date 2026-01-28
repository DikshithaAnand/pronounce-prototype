from supabase import create_client, Client
from backend.app.config import SUPABASE_URL, SUPABASE_KEY

_supabase_client: Client = None

def get_supabase_client() -> Client:
    """
    Returns a singleton Supabase client instance.
    """
    global _supabase_client
    if _supabase_client is None:
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"🔥 Failed to connect to Supabase: {e}")
            return None
    return _supabase_client