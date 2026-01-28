from collections import defaultdict

from backend.app.db.client import get_supabase_client
supabase=get_supabase_client()
# --- NEW HELPER FUNCTION FOR ROW 4 ---
def fetch_word_analysis(user_id: str):
    """
    Fetches raw errors from 'attempt_errors' table and aggregates them 
    by word and error type (mispronounced, stuttered, wrong) for the dashboard.
    """
    

    try:
        # 1. Get all attempt IDs for this user
        
        
        # --- FIX: Query 'user_name' instead of 'user_id' ---
        attempts_response = supabase.table("attempts") \
            .select("id") \
            .eq("user_name", user_id) \
            .execute()
        
        

        attempt_ids = [a['id'] for a in attempts_response.data]
        

        
        
        errors_response = supabase.table("attempt_errors") \
            .select("word, error_type") \
            .in_("attempt_id", attempt_ids) \
            .execute()
        
        raw_errors = errors_response.data
        
        

        # 3. Aggregate Data (Group by Word)
        word_stats = defaultdict(lambda: {"mispronounced": 0, "stuttered": 0, "wrong": 0})

        for row in raw_errors:
            raw_word = row.get('word')
            if not raw_word:
                continue

            word = raw_word.lower().strip()
            error_type = row.get('error_type', '')

            # --- MAPPING LOGIC ---
            if error_type == 'substitution':
                word_stats[word]['mispronounced'] += 1
            elif error_type == 'deletion':
                word_stats[word]['wrong'] += 1
            elif error_type == 'insertion':
                word_stats[word]['stuttered'] += 1
            else:
                # Default fallback
                word_stats[word]['mispronounced'] += 1

        # 4. Format into Lists for Frontend
        result = {
            "word": [],
            "mispronounced": [],
            "stuttered": [],
            "wrong": []
        }

        for w, counts in word_stats.items():
            result["word"].append(w)
            result["mispronounced"].append(counts["mispronounced"])
            result["stuttered"].append(counts["stuttered"])
            result["wrong"].append(counts["wrong"])

        
        return result

    except Exception as e:
        
        return {}