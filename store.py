import sqlite3
from typing import List, Optional

from models.job import Job


class Store:
    def __init__(self, db_path: str = "jobs.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
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
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self.conn.commit()

    def save_jobs(self, jobs: List[Job]) -> int:
        new_count = 0
        for job in jobs:
            try:
                self.conn.execute("""
                    INSERT OR IGNORE INTO jobs
                        (url, title, company, location, source, snippet, salary, date_posted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.url, job.title, job.company, job.location,
                    job.source, job.snippet, job.salary, job.date_posted,
                ))
                if self.conn.total_changes > 0:
                    new_count += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return new_count

    def get_all_jobs(self) -> List[Job]:
        cursor = self.conn.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [Job(
            title=row[1],
            company=row[2],
            location=row[3],
            url=row[0],
            source=row[4],
            snippet=row[5],
            salary=row[6],
            date_posted=row[7],
        ) for row in rows]

    def count(self) -> int:
        cursor = self.conn.execute("SELECT COUNT(*) FROM jobs")
        return cursor.fetchone()[0]

    def close(self):
        self.conn.close()
