# Bulk Job Application Email Sender 🚀

A production-ready, automated Python tool designed to send personalized job applications and resumes in bulk with anti-spam rate limiting, delivery tracking, and auto-resume capabilities.

---

## ✨ Features

- 🎯 **Personalized per Company**: Dynamically delivers tailored subject lines, custom company greetings, and individualized email bodies from an Excel spreadsheet.
- 📎 **Automatic Resume Attachment**: Automatically attaches your PDF resume (with custom display filename) with proper MIME formatting.
- 🎨 **Clean HTML & Plain-Text Dual Delivery**: Generates crisp, modern HTML styling for mobile/desktop mail clients with clean plain-text fallback.
- 🛡️ **Anti-Spam Throttling**: Randomized delays (5–10 seconds) between sends to protect your email domain reputation and avoid hitting SMTP rate limits.
- 🔄 **Smart Deduplication & Pause/Resume**: Keeps track of every delivery in `sent_log.csv`. If stopped (`Ctrl+C`) or interrupted, you can resume anytime without sending duplicate emails.
- 🧪 **Safety Test & Dry Run**: Send 1 test email to your own inbox to inspect formatting and verify the PDF attachment before sending to recruiters.
- 💻 **Interactive Menu & CLI Flags**: Works via an interactive menu, one-click Windows launcher (`run.bat`), or direct command-line flags.
- 🔒 **Privacy & Security**: Credentials and personal files (resumes, recipient spreadsheets, logs) are protected and excluded via `.gitignore`.

---

## 📁 Repository Structure

```text
├── config.py                 # Configuration loader and environment manager
├── excel_reader.py           # Excel spreadsheet parser and validation engine
├── mailer.py                 # SMTP engine with SSL/TLS and PDF attachment handler
├── tracker.py                # CSV-based sent logger and deduplication tracker
├── send_emails.py            # Main CLI runner and interactive terminal UI
├── run.bat                   # Double-click Windows launcher script
├── requirements.txt          # Python dependencies
├── .env.example              # Configuration template
├── sample_recipients.xlsx    # Sample spreadsheet template with example drafts
└── README.md                 # Project documentation
```

---

## 🛠️ Prerequisites

- **Python 3.8+** installed ([python.org](https://www.python.org/downloads/))
- A **Gmail account** (or any custom SMTP server) with 2-Step Verification enabled.

---

## 🔑 Getting Your Gmail App Password (Takes 60 Seconds)

Google requires a dedicated **16-character App Password** for secure SMTP sending:

1. Enable **2-Step Verification** on your Google Account:  
   👉 [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Go directly to **App Passwords**:  
   👉 [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. In the **App name** field, type `Bulk Emailer` (or any name) and click **Create**.
4. Copy the generated **16-character password** (example: `abcd efgh ijkl mnop`).

---

## 🚀 Quick Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/bulk-job-email-sender.git
cd bulk-job-email-sender
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure credentials
Copy `.env.example` to `.env`:
```bash
# On Windows PowerShell:
Copy-Item .env.example .env

# On Linux / macOS / Bash:
cp .env.example .env
```

Open `.env` and fill in your details:
```env
SENDER_NAME=Your Full Name
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_16_char_app_password

# File paths in the project folder
EXCEL_FILE=recipients.xlsx
ATTACHMENT_FILE=resume.pdf
ATTACHMENT_DISPLAY_NAME=Your_Name_Resume.pdf

# Anti-spam delay between emails (seconds)
DELAY_MIN=5
DELAY_MAX=10
```

> 💡 **Tip:** You can also run `python send_emails.py --setup` to configure your credentials interactively!

### 4. Add your files
1. Place your **Resume PDF** in the folder (e.g. `resume.pdf`).
2. Place your **Excel spreadsheet** in the folder (e.g. `recipients.xlsx`).

---

## 📊 Excel File Format

Your Excel spreadsheet (`recipients.xlsx` or custom name) should have the following columns in the first sheet:

| S.No. | Email Address | Company Name | Subject | Email Body |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `recruiter@company.com` | `Company Name` | `Software Engineer Application - Your Name` | `Dear Company Team,\n\nI am applying for...` |
| 2 | `careers@startup.io` | `StartupIO` | `Full Stack Developer - Your Name` | `Dear StartupIO Team,\n\nI am excited to...` |

*(A ready-to-use template is provided in `sample_recipients.xlsx`)*

---

## 🖥️ Usage

### Interactive Menu
Run the script or double-click `run.bat` on Windows:
```bash
python send_emails.py
```

You will see:
```text
========================================================================
               BULK JOB APPLICATION EMAIL SENDER
========================================================================
 Sender:      Your Name <your_email@gmail.com>
 Status:      [CONFIGURED]
 Excel Data:  recipients.xlsx (60 recipients loaded)
 Attachment:  resume.pdf [Found (72.0 KB)]
 Progress:    0 Sent | 0 Failed | 60 Pending
========================================================================

Select an action:
  1. Send Test Email (Send 1 email to yourself to verify layout & PDF)
  2. Dry Run / Preview Recipient List (Verify drafts & attachment)
  3. Start Bulk Sending (Send to all pending recipients with delays)
  4. View Sent History / Summary
  5. Configure / Update Email Credentials & App Password
  6. Reset Sent Log (Start from beginning)
  0. Exit
```

### Command Line Flags
For automation or fast runs, you can also use CLI flags:

- **Send a Test Email to yourself:**
  ```bash
  python send_emails.py --test
  # or specify an address:
  python send_emails.py --test mytest@example.com
  ```
- **Dry Run Preview:**
  ```bash
  python send_emails.py --dry-run
  ```
- **Start Bulk Sending:**
  ```bash
  python send_emails.py --send
  # Skip confirmation prompt:
  python send_emails.py --send -y
  ```
- **Check Delivery Stats:**
  ```bash
  python send_emails.py --status
  ```
- **Reset Delivery History:**
  ```bash
  python send_emails.py --reset-log
  ```

---

## 🛡️ Anti-Spam & Delivery Safeguards

1. **Always Send a Test Email First**: Use Option 1 to check how your email renders on both desktop and mobile email apps and verify that your resume PDF opens properly.
2. **Built-in Random Delay**: Automatically waits 5 to 10 seconds between emails.
3. **Daily Limit Awareness**: Standard personal Gmail accounts have a sending limit of ~500 emails/day. For optimal deliverability and inbox placement, we recommend keeping batches to 50–100 applications per day.
4. **Pause Anytime**: Hit `Ctrl+C` at any time to pause. Sent rows are saved in real-time to `sent_log.csv`. Running the tool again will resume from the remaining pending emails.

---

## 🔒 Security & Privacy

This repository includes a `.gitignore` configured to ensure:
- Your `.env` credentials are **never committed**.
- Your real `.pdf` resume files are **never committed**.
- Your real `.xlsx` and `.csv` recipient databases and sent logs are **never committed**.

---

## 📄 License

MIT License. Feel free to customize and use it for your job search!
