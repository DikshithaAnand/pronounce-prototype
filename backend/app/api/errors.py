from fastapi import APIRouter, HTTPException
from backend.app.schemas.error import ErrorCreate
from backend.app.db.connection import get_connection

router = APIRouter(prefix="/errors", tags=["Errors"])

@router.post("/")
def create_error(error: ErrorCreate):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO pronounce.attempt_errors (
                attempt_id,
                word_expected,
                word_spoken,
                error_type
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (
                error.attempt_id,
                error.word_expected,
                error.word_spoken,
                error.error_type
            )
        )

        error_id = cur.fetchone()[0]
        conn.commit()

        return {"error_id": error_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()
        conn.close()
