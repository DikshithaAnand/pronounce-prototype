from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.passage import PassageCreate
from backend.app.db.connection import get_connection
import random

router = APIRouter(prefix="/passages", tags=["Passages"])

@router.post("/")
def create_passage(passage: PassageCreate):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO pronounce.reading_passages (title, content, difficulty_level)
            VALUES (%s, %s, %s)
            RETURNING id, title, difficulty_level, created_at;
            """,
            (passage.title, passage.content, passage.difficulty_level)
        )

        row = cur.fetchone()
        conn.commit()

        return {
            "id": row[0],
            "title": row[1],
            "difficulty_level": row[2],
            "created_at": row[3]
        }

    finally:
        cur.close()
        conn.close()

@router.get("/random")
def get_random_passage(
    difficulty: str | None = Query(default=None)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        if difficulty:
            cur.execute(
                """
                SELECT id, title, content, difficulty_level
                FROM pronounce.reading_passages
                WHERE difficulty_level = %s
                ORDER BY RANDOM()
                LIMIT 1;
                """,
                (difficulty,)
            )
        else:
            cur.execute(
                """
                SELECT id, title, content, difficulty_level
                FROM pronounce.reading_passages
                ORDER BY RANDOM()
                LIMIT 1;
                """
            )

        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No passages found")

        return {
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "difficulty_level": row[3]
        }

    finally:
        cur.close()
        conn.close()
