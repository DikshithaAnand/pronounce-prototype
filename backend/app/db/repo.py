import logging
from collections import Counter
from backend.app.db.client import get_supabase_client

logger = logging.getLogger(__name__)

# ==========================================
#  WRITE OPERATIONS (Existing & Preserved)
# ==========================================

def save_attempt(user_name: str, target_text: str, metrics: dict, error_report: list,difficulty: str = "easy"):
    """
    Saves the attempt metadata AND the detailed error logs to Supabase.
    """
    client = get_supabase_client()
    if not client:
        logger.warning("⚠️ Database client unavailable. Skipping save.")
        return None

    try:
        attempt_data = {
            "user_name": user_name,
            "passage_text": target_text[:500],
            "difficulty": difficulty,  # <--- NEW FIELD
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

# ==========================================
#  READ OPERATIONS (New for Dashboard)
# ==========================================

def fetch_dashboard_stats(user_name: str):
    """
    Returns 'Big Number' cards: Avg WPM, Total Attempts, Best Accuracy.
    """
    client = get_supabase_client()
    if not client: return {}

    try:
        response = client.table("attempts")\
            .select("wpm, accuracy_score")\
            .eq("user_name", user_name)\
            .execute()
            
        data = response.data
        if not data:
            return {"avg_wpm": 0, "avg_accuracy": 0, "total_attempts": 0}

        total = len(data)
        avg_wpm = sum(d['wpm'] for d in data) / total
        avg_acc = sum(d['accuracy_score'] for d in data) / total

        return {
            "avg_wpm": round(avg_wpm, 1),
            "avg_accuracy": round(avg_acc, 1),
            "total_attempts": total
        }
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        return {"avg_wpm": 0, "avg_accuracy": 0, "total_attempts": 0}

def fetch_progress_history(user_name: str, limit: int = 10):
    """
    Returns data for the Line Chart (Timeline of improvement).
    """
    client = get_supabase_client()
    if not client: return []

    try:
        response = client.table("attempts")\
            .select("created_at, wpm, accuracy_score, fluency_score")\
            .eq("user_name", user_name)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        # Reverse so it flows Left (Old) -> Right (New) on the chart
        return response.data[::-1] if response.data else []
    except Exception as e:
        logger.error(f"Error fetching progress: {e}")
        return []

def fetch_error_distribution(user_name: str):
    """
    Returns data for the Pie Chart (Types of errors made).
    """
    client = get_supabase_client()
    if not client: return {}

    try:
        # 1. Get recent attempts by this user
        attempts_resp = client.table("attempts")\
            .select("id")\
            .eq("user_name", user_name)\
            .order("created_at", desc=True)\
            .limit(50)\
            .execute()
            
        if not attempts_resp.data:
            return {}

        attempt_ids = [a['id'] for a in attempts_resp.data]

        # 2. Get errors linked to those attempts
        errors_resp = client.table("attempt_errors")\
            .select("error_type")\
            .in_("attempt_id", attempt_ids)\
            .execute()

        # 3. Count them (e.g., {'mispronunciation': 12, 'stutter': 4})
        error_counts = Counter(item['error_type'] for item in errors_resp.data)
        return dict(error_counts)

    except Exception as e:
        logger.error(f"Error fetching error distribution: {e}")
        return {}