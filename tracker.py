import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Set


LOG_HEADERS = ["Timestamp", "S.No.", "Email Address", "Company Name", "Subject", "Status", "Details"]


class SentTracker:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self._ensure_file()

    def _ensure_file(self):
        if not self.log_path.exists():
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(LOG_HEADERS)

    def get_successful_emails(self) -> Set[str]:
        """Returns lowercase set of email addresses that have successfully been sent."""
        if not self.log_path.exists():
            return set()

        sent = set()
        with open(self.log_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Status", "").strip().upper() in ("SENT", "SUCCESS"):
                    email = row.get("Email Address", "").strip().lower()
                    if email:
                        sent.add(email)
        return sent

    def record_result(self, s_no: int, email: str, company: str, subject: str, status: str, details: str = ""):
        """Appends a new result record into the log CSV."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                s_no,
                email,
                company,
                subject,
                status.upper(),
                details.replace("\n", " ").strip()
            ])

    def get_stats(self, total_count: int) -> Dict[str, int]:
        success_count = 0
        failure_count = 0

        if self.log_path.exists():
            with open(self.log_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = row.get("Status", "").strip().upper()
                    if status in ("SENT", "SUCCESS"):
                        success_count += 1
                    elif status in ("FAILED", "ERROR"):
                        failure_count += 1

        pending_count = max(0, total_count - success_count)
        return {
            "total": total_count,
            "success": success_count,
            "failed": failure_count,
            "pending": pending_count,
        }

    def reset_log(self) -> str:
        """Backs up existing log file if not empty and initializes fresh log."""
        if self.log_path.exists() and self.log_path.stat().st_size > 0:
            backup_name = f"{self.log_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            backup_path = self.log_path.parent / backup_name
            self.log_path.rename(backup_path)
            self._ensure_file()
            return str(backup_path)
        self._ensure_file()
        return ""
