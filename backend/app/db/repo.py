import logging
from backend.app.db.client import get_supabase_client

logger = logging.getLogger(__name__)

def save_attempt(user_name: str, target_text: str, metrics: dict, error_report: list):
    """
    Saves the attempt metadata AND the detailed error logs to Supabase.
    """
    client = get_supabase_client()
    if not client:
        logger.warning("⚠️ Database client unavailable. Skipping save.")
        return None

    try:
        # 1. Insert the Main Attempt (The "Header")
        attempt_data = {
            "user_name": user_name,
            "passage_text": target_text[:500],  # Store snippet
            "wpm": metrics.get("wpm", 0),
            "accuracy_score": metrics.get("accuracy", 0),
            "fluency_score": metrics.get("fluency", 0),
            "mispronounced_count": metrics.get("mispronunciation_count", 0)
        }
        
        # 'data' returns a list of inserted rows (we need the ID)
        response = client.table("attempts").insert(attempt_data).execute()
        
        if not response.data:
            logger.error("❌ Inserted attempt but got no ID back.")
            return None
            
        attempt_id = response.data[0]['id']
        logger.info(f"✅ Saved Attempt ID: {attempt_id}")

        # 2. Insert the Detailed Errors (The "Rows")
        if error_report:
            error_rows = []
            for err in error_report:
                # We only save specific error types to keep DB clean
                if err.get("type") in ["mispronunciation", "substitution", "deletion", "stutter"]:
                    error_rows.append({
                        "attempt_id": attempt_id,
                        "word": err.get("expected") or err.get("actual") or "?",
                        "error_type": err.get("type"),
                        "confidence_score": err.get("similarity", 0)
                    })
            
            if error_rows:
                client.table("attempt_errors").insert(error_rows).execute()
                logger.info(f"✅ Saved {len(error_rows)} error details.")

        return attempt_id

    except Exception as e:
        logger.error(f"🔥 Database Save Error: {e}")
        return None