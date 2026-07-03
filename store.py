import sqlite3
from typing import List

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
                remote INTEGER DEFAULT 0,
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
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return new_count

    def get_all_jobs(self) -> List[Job]:
        cursor = self.conn.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        return [self._row_to_job(row) for row in cursor.fetchall()]

    def get_recent_jobs(self, days: int = 15) -> List[Job]:
        cursor = self.conn.execute(
            "SELECT * FROM jobs WHERE created_at >= datetime('now', ?) ORDER BY created_at DESC",
            (f"-{days} days",),
        )
        return [self._row_to_job(row) for row in cursor.fetchall()]

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
        cursor = self.conn.execute("SELECT COUNT(*) FROM jobs")
        return cursor.fetchone()[0]

    def close(self):
        self.conn.close()
