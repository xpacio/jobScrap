import os
from typing import List, Optional

from models.job import Job


class Store:
    @staticmethod
    def _clean_dsn(dsn: str) -> str:
        dsn = dsn.strip()
        for prefix in ("pgsql:", "postgresql://", "postgres://"):
            if dsn.startswith(prefix):
                dsn = dsn[len(prefix):]
                break
        return dsn

    def __init__(self, dsn: Optional[str] = None, db_path: str = "jobs.db"):
        raw = dsn or os.environ.get("JOBSCRAP_DSN") or ""
        if raw:
            self.dsn = self._clean_dsn(raw)
            import psycopg2
            self.conn = psycopg2.connect(self.dsn)
            self._pg = True
        else:
            import sqlite3
            self.conn = sqlite3.connect(db_path)
            self._pg = False
        self._create_table()
        if self._pg:
            self._create_keywords_table()

    def _create_table(self):
        if self._pg:
            cur = self.conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    url TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT DEFAULT '',
                    location TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    snippet TEXT DEFAULT '',
                    salary TEXT DEFAULT '',
                    date_posted TEXT DEFAULT '',
                    remote BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            self.conn.commit()
            cur.close()
        else:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    url TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT DEFAULT '',
                    location TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    snippet TEXT DEFAULT '',
                    salary TEXT DEFAULT '',
                    date_posted TEXT DEFAULT '',
                    remote INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            self.conn.commit()

    def _create_keywords_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id SERIAL PRIMARY KEY,
                word TEXT NOT NULL UNIQUE,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        self.conn.commit()
        cur.close()

    def get_keywords(self) -> List[str]:
        if not self._pg:
            return []
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT word FROM keywords WHERE active = TRUE ORDER BY id")
            rows = cur.fetchall()
            cur.close()
            return [r[0] for r in rows]
        except Exception:
            return []

    def add_keyword(self, word: str) -> bool:
        if not self._pg:
            return False
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO keywords (word) VALUES (%s) ON CONFLICT (word) DO UPDATE SET active = TRUE",
                (word.strip(),),
            )
            self.conn.commit()
            cur.close()
            return True
        except Exception:
            return False

    def delete_keyword(self, word_id: int) -> bool:
        if not self._pg:
            return False
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM keywords WHERE id = %s", (word_id,))
            self.conn.commit()
            cur.close()
            return True
        except Exception:
            return False

    def toggle_keyword(self, word_id: int, active: bool) -> bool:
        if not self._pg:
            return False
        try:
            cur = self.conn.cursor()
            cur.execute("UPDATE keywords SET active = %s WHERE id = %s", (active, word_id))
            self.conn.commit()
            cur.close()
            return True
        except Exception:
            return False

    def get_keywords_full(self) -> List[dict]:
        if not self._pg:
            return []
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id, word, active FROM keywords ORDER BY id")
            rows = cur.fetchall()
            cur.close()
            return [{"id": r[0], "word": r[1], "active": r[2]} for r in rows]
        except Exception:
            return []

    def save_jobs(self, jobs: List[Job]) -> int:
        new_count = 0
        for job in jobs:
            try:
                if self._pg:
                    cur = self.conn.cursor()
                    cur.execute("""
                        INSERT INTO jobs
                            (url, title, company, location, source,
                             snippet, salary, date_posted, remote)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (url) DO NOTHING
                    """, (
                        job.url, job.title, job.company, job.location,
                        job.source, job.snippet, job.salary, job.date_posted,
                        job.remote,
                    ))
                    self.conn.commit()
                    if cur.rowcount > 0:
                        new_count += 1
                    cur.close()
                else:
                    self.conn.execute("""
                        INSERT OR IGNORE INTO jobs
                            (url, title, company, location, source,
                             snippet, salary, date_posted, remote)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job.url, job.title, job.company, job.location,
                        job.source, job.snippet, job.salary, job.date_posted,
                        1 if job.remote else 0,
                    ))
                    if self.conn.total_changes > 0:
                        new_count += 1
            except Exception:
                pass
        self.conn.commit()
        return new_count

    def get_all_jobs(self) -> List[Job]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM jobs ORDER BY created_at DESC, (CASE WHEN COALESCE(salary, '') != '' THEN 0 ELSE 1 END), remote DESC")
        rows = cur.fetchall()
        cur.close()
        return [self._row_to_job(r) for r in rows]

    def get_recent_jobs(self, days: int = 15) -> List[Job]:
        cur = self.conn.cursor()
        if self._pg:
            cur.execute(
                "SELECT * FROM jobs WHERE created_at >= NOW() - make_interval(days => %s) ORDER BY created_at DESC, (CASE WHEN COALESCE(salary, '') != '' THEN 0 ELSE 1 END), remote DESC NULLS LAST",
                (days,),
            )
        else:
            cur.execute(
                "SELECT * FROM jobs WHERE created_at >= datetime('now', ?) ORDER BY created_at DESC, (CASE WHEN COALESCE(salary, '') != '' THEN 0 ELSE 1 END), remote DESC",
                (f"-{days} days",),
            )
        rows = cur.fetchall()
        cur.close()
        return [self._row_to_job(r) for r in rows]

    def _row_to_job(self, row) -> Job:
        return Job(
            title=row[1],
            company=row[2],
            location=row[3],
            url=row[0],
            source=row[4],
            snippet=row[5],
            salary=row[6],
            date_posted=row[7],
            remote=bool(row[8]),
        )

    def count(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM jobs")
        cnt = cur.fetchone()[0]
        cur.close()
        return cnt

    def close(self):
        self.conn.close()
