from app.db.connection import get_connection


def save_word_errors(attempt_id: int, error_list: list):
    """
    Stores word-level errors for a single attempt.
    error_list comes from `error_analysis`
    """
    if not error_list:
        return

    conn = get_connection()
    cur = conn.cursor()

    try:
        for idx, err in enumerate(error_list):
            cur.execute(
                """
                INSERT INTO pronounce.practice_errors (
                    attempt_id,
                    error_type,
                    expected_word,
                    spoken_word,
                    word_position
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    attempt_id,
                    err.get("type"),
                    err.get("expected"),
                    err.get("actual"),
                    idx
                )
            )

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()
