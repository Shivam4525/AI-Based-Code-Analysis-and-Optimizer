import mysql.connector
from mysql.connector import pooling, Error
from config import Config

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="ai_code_tester_pool",
            pool_size=5,
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=Config.DB_PORT,
        )
    return _pool


def get_connection():
    return get_pool().get_connection()


def fetch_one(query, params=None):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchone()
    finally:
        conn.close()


def execute(query, params=None):
    """For INSERT/UPDATE/DELETE. Returns the new row's id (for INSERT)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()