import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Load existing .env if present
load_dotenv(dotenv_path=ENV_PATH)


class Config:
    def __init__(self):
        self.reload()

    def reload(self):
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        self.sender_name = os.getenv("SENDER_NAME", "Your Name").strip()
        self.sender_email = os.getenv("SENDER_EMAIL", "").strip()
        self.sender_password = os.getenv("SENDER_PASSWORD", "").strip()

        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
        self.smtp_port = int(os.getenv("SMTP_PORT", "465").strip())
        self.smtp_use_ssl = os.getenv("SMTP_USE_SSL", "true").strip().lower() in ("true", "1", "yes")

        self.excel_file = os.getenv("EXCEL_FILE", "recipients.xlsx").strip()
        self.attachment_file = os.getenv("ATTACHMENT_FILE", "resume.pdf").strip()
        self.attachment_display_name = os.getenv("ATTACHMENT_DISPLAY_NAME", "Resume.pdf").strip()

        self.delay_min = int(os.getenv("DELAY_MIN", "5").strip())
        self.delay_max = int(os.getenv("DELAY_MAX", "10").strip())
        self.log_file = os.getenv("LOG_FILE", "sent_log.csv").strip()

    @property
    def excel_path(self) -> Path:
        target = BASE_DIR / self.excel_file
        if not target.exists():
            # Auto-detect another .xlsx file in directory (e.g. sample or custom)
            candidates = [p for p in BASE_DIR.glob("*.xlsx") if p.name != "sample_recipients.xlsx"]
            if candidates:
                return candidates[0]
            sample = BASE_DIR / "sample_recipients.xlsx"
            if sample.exists():
                return sample
        return target

    @property
    def attachment_path(self) -> Path:
        target = BASE_DIR / self.attachment_file
        if not target.exists():
            # Auto-detect any available .pdf in directory
            candidates = list(BASE_DIR.glob("*.pdf"))
            if candidates:
                return candidates[0]
        return target

    @property
    def log_path(self) -> Path:
        return BASE_DIR / self.log_file

    def is_configured(self) -> bool:
        return bool(self.sender_email and self.sender_password and len(self.sender_password) >= 8)

    def save_settings(self, email: str, password: str, name: str = None, min_delay: int = None, max_delay: int = None):
        if name is not None:
            self.sender_name = name
        if email is not None:
            self.sender_email = email
        if password is not None:
            self.sender_password = password.replace(" ", "")  # Clean Google App Password spaces
        if min_delay is not None:
            self.delay_min = min_delay
        if max_delay is not None:
            self.delay_max = max_delay

        env_lines = [
            f"# Sender Configuration",
            f"SENDER_NAME={self.sender_name}",
            f"SENDER_EMAIL={self.sender_email}",
            f"SENDER_PASSWORD={self.sender_password}",
            f"",
            f"# SMTP Settings",
            f"SMTP_SERVER={self.smtp_server}",
            f"SMTP_PORT={self.smtp_port}",
            f"SMTP_USE_SSL={'true' if self.smtp_use_ssl else 'false'}",
            f"",
            f"# File Paths",
            f"EXCEL_FILE={self.excel_file}",
            f"ATTACHMENT_FILE={self.attachment_file}",
            f"ATTACHMENT_DISPLAY_NAME={self.attachment_display_name}",
            f"",
            f"# Delay Range in Seconds (Anti-Spam Throttling)",
            f"DELAY_MIN={self.delay_min}",
            f"DELAY_MAX={self.delay_max}",
            f"",
            f"# Tracking",
            f"LOG_FILE={self.log_file}",
        ]
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(env_lines) + "\n")
        self.reload()


config = Config()
