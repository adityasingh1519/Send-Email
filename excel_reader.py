import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import openpyxl


@dataclass
class RecipientRecord:
    s_no: int
    email: str
    company: str
    subject: str
    body: str
    row_idx: int


def is_valid_email(email: str) -> bool:
    if not email:
        return False
    # Standard email regex check
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def load_recipients_from_excel(file_path: Path) -> Tuple[List[RecipientRecord], List[str]]:
    """
    Loads recipient records from the provided Excel file.
    Returns:
        tuple of (valid_records, warnings_list)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found at: {file_path}")

    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Excel file is completely empty.")

    header_row = rows[0]
    headers_clean = [str(h).strip().lower() if h is not None else "" for h in header_row]

    # Map column positions accurately
    col_sno = -1
    col_email = -1
    col_company = -1
    col_subject = -1
    col_body = -1

    for idx, h in enumerate(headers_clean):
        # Check body first because header might be 'email body'
        if any(term in h for term in ["body", "draft", "message", "content"]):
            col_body = idx
        elif any(term in h for term in ["s.no", "sno", "s no", "index", "id"]):
            col_sno = idx
        elif any(term in h for term in ["email", "e-mail", "mail address", "mail"]):
            col_email = idx
        elif any(term in h for term in ["company", "organization"]):
            col_company = idx
        elif any(term in h for term in ["subject", "title"]):
            col_subject = idx

    # Positional fallbacks if some couldn't be resolved
    if col_email == -1 and len(headers_clean) >= 2:
        col_email = 1
    if col_company == -1 and len(headers_clean) >= 3:
        col_company = 2
    if col_subject == -1 and len(headers_clean) >= 4:
        col_subject = 3
    if col_body == -1 and len(headers_clean) >= 5:
        col_body = 4

    if col_email == -1:
        raise ValueError(
            f"Could not identify an 'Email Address' column in sheet headers: {header_row}"
        )

    records: List[RecipientRecord] = []
    warnings: List[str] = []

    for row_idx, r in enumerate(rows[1:], start=2):
        if not r or all(cell is None or str(cell).strip() == "" for cell in r):
            continue  # skip completely blank rows

        raw_sno = r[col_sno] if col_sno != -1 and col_sno < len(r) else row_idx - 1
        raw_email = r[col_email] if col_email != -1 and col_email < len(r) else ""
        raw_company = r[col_company] if col_company != -1 and col_company < len(r) else ""
        raw_subject = r[col_subject] if col_subject != -1 and col_subject < len(r) else ""
        raw_body = r[col_body] if col_body != -1 and col_body < len(r) else ""

        email_str = str(raw_email or "").strip()
        company_str = str(raw_company or "").strip()
        subject_str = str(raw_subject or "").strip()
        body_str = str(raw_body or "").strip()

        try:
            s_no = int(float(raw_sno))
        except (ValueError, TypeError):
            s_no = row_idx - 1

        if not email_str:
            warnings.append(f"Row {row_idx}: Skipped because email address is blank.")
            continue

        if not is_valid_email(email_str):
            warnings.append(f"Row {row_idx}: Skipped invalid email format: '{email_str}'")
            continue

        if not subject_str:
            subject_str = "Application for Software Engineer / AI Systems"

        if not body_str:
            warnings.append(f"Row {row_idx}: Warning - email body for '{email_str}' is empty.")

        records.append(
            RecipientRecord(
                s_no=s_no,
                email=email_str,
                company=company_str,
                subject=subject_str,
                body=body_str,
                row_idx=row_idx,
            )
        )

    return records, warnings
