from fastapi import APIRouter, HTTPException
import psycopg2

# --------------------
# INTERNAL IMPORTS (FIXED ✅)
# --------------------

from backend.app.schemas.user import UserCreate
from backend.app.db.connection import get_connection

# --------------------
# ROUTER
# --------------------

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# --------------------
# CREATE USER
# --------------------

@router.post("/", summary="Create a new user")
def create_user(user: UserCreate):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO pronounce.users (username)
            VALUES (%s)
            RETURNING id, username, created_at;
            """,
            (user.username,)
        )

        row = cur.fetchone()
        conn.commit()

        return {
            "id": row[0],
            "username": row[1],
            "created_at": row[2]
        }

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(
            status_code=409,
            detail="Username already exists"
        )

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cur.close()
        conn.close()

# --------------------
# DELETE USER
# --------------------

@router.delete("/{user_id}", summary="Delete user by ID")
def delete_user(user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            DELETE FROM pronounce.users
            WHERE id = %s
            RETURNING id;
            """,
            (user_id,)
        )

        row = cur.fetchone()
        if not row:
            conn.rollback()
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        conn.commit()
        return {
            "message": "User deleted successfully",
            "user_id": user_id
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cur.close()
        conn.close()
