from app.db.connection import get_connection


def save_practice_attempt(user_id: int, passage_text: str, metrics: dict, components: dict):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO pronounce.practice_attempts (
                user_id,
                passage_text,
                accuracy_score,
                fluency_score,
                wpm,
                skipped_count,
                mispronounced_count,
                stutter_count,
                substitution_count
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id;
            """,
            (
                user_id,
                passage_text,
                metrics.get("accuracy"),
                metrics.get("fluency"),
                metrics.get("wpm"),
                metrics.get("deletion_count"),
                metrics.get("mispronunciation_count"),
                metrics.get("stutter_count"),
                metrics.get("substitution_count"),
            )
        )

        attempt_id = cur.fetchone()[0]
        conn.commit()
        return attempt_id

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()
