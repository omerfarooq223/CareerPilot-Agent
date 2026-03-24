"""Database utilities with connection pooling for SQLite."""

import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Optional
from loguru import logger
from config.config import Config

DB_PATH = Config.DB_PATH
DEFAULT_POOL_SIZE = Config.DB_POOL_SIZE


class ConnectionPool:
    """
    A simple connection pool for SQLite databases.
    Manages a pool of connections to reduce overhead of opening/closing connections.
    """

    def __init__(self, db_path: str, max_connections: int = 5, timeout: float = 30.0):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool = []
        self._used = {}
        self._lock = threading.Lock()
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool with fresh connections."""
        for _ in range(self.max_connections):
            conn = self._create_connection()
            if conn:
                self._pool.append(conn)

    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create a new database connection."""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            return conn
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            return None

    def get_connection(self, timeout: Optional[float] = None) -> Optional[sqlite3.Connection]:
        """
        Get a connection from the pool.

        Args:
            timeout: Override the default timeout

        Returns:
            Database connection or None if timeout occurs
        """
        if timeout is None:
            timeout = self.timeout

        start_time = time.time()
        while time.time() - start_time < timeout:
            with self._lock:
                if self._pool:
                    conn = self._pool.pop()
                    thread_id = threading.get_ident()
                    self._used[thread_id] = conn
                    return conn

            time.sleep(0.1)  # Small delay before retrying

        logger.error(f"Timeout getting connection from pool after {timeout}s")
        return None

    def return_connection(self, conn: sqlite3.Connection) -> bool:
        """
        Return a connection to the pool.

        Args:
            conn: Connection to return to pool

        Returns:
            True if connection was returned successfully, False otherwise
        """
        with self._lock:
            thread_id = threading.get_ident()

            # Remove from used connections
            if self._used.get(thread_id) == conn:
                del self._used[thread_id]

            # Add back to pool if there's space
            if len(self._pool) < self.max_connections:
                # Reset connection state
                try:
                    conn.rollback()
                    self._pool.append(conn)
                    return True
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")
                    try:
                        conn.close()
                    except:
                        pass
                    return False
            else:
                # Pool is full, close the connection
                try:
                    conn.close()
                    return True
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
                    return False

    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._pool:
                try:
                    conn.close()
                except:
                    pass
            self._pool.clear()

            for conn in self._used.values():
                try:
                    conn.close()
                except:
                    pass
            self._used.clear()

    @contextmanager
    def get_conn(self):
        """
        Context manager for getting and automatically returning a connection.

        Usage:
            with pool.get_conn() as conn:
                cursor = conn.cursor()
                # ... use connection ...
                conn.commit()
        """
        conn = self.get_connection()
        if conn is None:
            raise Exception("Could not acquire database connection from pool")

        try:
            yield conn
        finally:
            self.return_connection(conn)


# Global connection pool instance
_pool_instance: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_db_pool() -> ConnectionPool:
    """Get the global connection pool instance, creating it if necessary."""
    global _pool_instance

    with _pool_lock:
        if _pool_instance is None:
            _pool_instance = ConnectionPool(DB_PATH, max_connections=DEFAULT_POOL_SIZE)
        return _pool_instance


def close_db_pool():
    """Close the global connection pool."""
    global _pool_instance

    with _pool_lock:
        if _pool_instance:
            _pool_instance.close_all()
            _pool_instance = None


def init_db_with_pool():
    """Initialize the database schema using the connection pool."""
    from skills.github_observer.github_observer import GitHubProfile
    from skills.gap_analyzer.gap_analyzer import GapReport
    import json
    from datetime import datetime

    pool = get_db_pool()

    with pool.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                overall_score INTEGER,
                strengths TEXT,
                critical_gaps TEXT,
                top_3_actions TEXT,
                portfolio_ready_repos TEXT,
                verdict TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actions_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_type TEXT,
                description TEXT
            )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS linkedin_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            post_type TEXT,
            repo_name TEXT,
            post_content TEXT,
            status TEXT        -- 'approved', 'discarded', 'regenerated'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                skill_name TEXT,
                output_file TEXT,
                rating INTEGER,
                comment TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                score_at_time INTEGER,
                applied_date TEXT,
                notes TEXT
            )
        """)

        conn.commit()
        logger.info("Database initialized with connection pool")