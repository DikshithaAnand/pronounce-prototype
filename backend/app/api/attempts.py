from fastapi import APIRouter, HTTPException
from backend.app.schemas.attempt import AttemptCreate
from backend.app.db.connection import get_connection

router = APIRouter(
    prefix="/attempts",
    tags=["Attempts"]
)

@router.post("/")
def create_attempt(attempt: AttemptCreate):
    """
    Store one reading attempt summary.

    This stores:
    - passage user read
    - overall metrics (accuracy, fluency, wpm, etc.)

    It does NOT store:
    - word-level errors
    - mispronounced word list
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO practice_attempts (
                user_id,
                passage_id,
                wpm,
                accuracy_score,
                fluency_score,
                mispronounced_count,
                skipped_count,
                stutter_count
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id, attempt_timestamp;
            """,
            (
                attempt.user_id,
                attempt.passage_id,
                attempt.wpm,
                attempt.accuracy_score,
                attempt.fluency_score,
                attempt.mispronounced_count,
                attempt.skipped_count,
                attempt.stutter_count,
            )
        )

        row = cur.fetchone()
        conn.commit()

        return {
            "attempt_id": row[0],
            "attempt_timestamp": row[1]
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store attempt: {str(e)}"
        )

    finally:
        cur.close()
        conn.close()
