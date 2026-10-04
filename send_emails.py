import argparse
import os
import random
import sys
import time
from pathlib import Path
from typing import List

# Force UTF-8 stdout/stderr on Windows to avoid charmap / cp1252 UnicodeEncodeErrors
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import config, BASE_DIR
from excel_reader import load_recipients_from_excel, RecipientRecord
from mailer import EmailSender
from tracker import SentTracker


def print_banner():
    tracker = SentTracker(config.log_path)
    total_recs = 0
    if config.excel_path.exists():
        try:
            records, _ = load_recipients_from_excel(config.excel_path)
            total_recs = len(records)
        except Exception:
            total_recs = 0

    stats = tracker.get_stats(total_recs)
    auth_status = "CONFIGURED" if config.is_configured() else "NOT CONFIGURED (Needs App Password)"

    print("=" * 72)
    print("               BULK JOB APPLICATION EMAIL SENDER")
    print("=" * 72)
    print(f" Sender:      {config.sender_name} <{config.sender_email}>")
    print(f" Status:      [{auth_status}]")
    print(f" Excel Data:  {config.excel_file} ({total_recs} recipients loaded)")
    attach_status = "Found" if config.attachment_path.exists() else "MISSING!"
    size_kb = f" ({config.attachment_path.stat().st_size / 1024:.1f} KB)" if config.attachment_path.exists() else ""
    print(f" Attachment:  {config.attachment_file} [{attach_status}{size_kb}]")
    print(f" Progress:    {stats['success']} Sent | {stats['failed']} Failed | {stats['pending']} Pending")
    print("=" * 72)


def run_setup_wizard():
    print("\n--- SENDER ACCOUNT SETUP ---")
    print("This program uses SMTP to send emails directly from your account.")
    print("For Gmail:")
    print("  1. Enable 2-Step Verification on your Google Account: https://myaccount.google.com/security")
    print("  2. Generate a 16-character App Password at: https://myaccount.google.com/apppasswords")
    print("  (App Passwords are 16 letters like: abcd efgh ijkl mnop)\n")

    current_name = config.sender_name or "Your Name"
    current_email = config.sender_email or "your_email@gmail.com"

    name = input(f"Enter your full name [{current_name}]: ").strip() or current_name
    email = input(f"Enter your Gmail address [{current_email}]: ").strip() or current_email
    
    password = input("Enter your 16-character Google App Password: ").strip()
    if not password:
        print("[!] No password entered. Setup cancelled.")
        return

    config.save_settings(email=email, password=password, name=name)
    print("[OK] Settings saved to .env!")

    # Test connection
    print("\nTesting SMTP connection...")
    sender = EmailSender()
    success, msg = sender.connect()
    if success:
        print(f"[OK] Connection successful: {msg}")
        sender.close()
    else:
        print(f"[FAILED] Connection failed: {msg}")


def run_dry_run():
    print("\n--- DRY RUN PREVIEW ---")
    if not config.excel_path.exists():
        print(f"[FAILED] Excel file not found: {config.excel_path}")
        return

    records, warnings = load_recipients_from_excel(config.excel_path)
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    tracker = SentTracker(config.log_path)
    sent_emails = tracker.get_successful_emails()

    print(f"\nTotal recipients found: {len(records)}")
    print(f"Already sent:           {len(sent_emails)}")
    print(f"Pending to send:        {len(records) - len([r for r in records if r.email.lower() in sent_emails])}")
    print(f"Resume attachment:      {config.attachment_path} ({'Found' if config.attachment_path.exists() else 'NOT FOUND'})")

    print("\nSample Preview (First 3 recipients):")
    print("-" * 72)
    for r in records[:3]:
        status_tag = "[ALREADY SENT]" if r.email.lower() in sent_emails else "[READY]"
        print(f"#{r.s_no} {status_tag}")
        print(f"To:      {r.email}")
        print(f"Company: {r.company}")
        print(f"Subject: {r.subject}")
        print(f"Body snippet:\n  " + r.body[:120].replace("\n", "\n  ") + "...")
        print("-" * 72)


def run_test_email(target_email: str = None):
    print("\n--- SEND TEST EMAIL ---")
    if not config.is_configured():
        print("[!] Please configure your sender email and Google App Password first.")
        run_setup_wizard()
        if not config.is_configured():
            return

    if not config.attachment_path.exists():
        print(f"[FAILED] Error: Attachment file not found at: {config.attachment_path}")
        return

    default_test = config.sender_email or "your_email@gmail.com"
    if not target_email:
        target_email = input(f"Enter the email address to receive the test email [{default_test}]: ").strip() or default_test

    # Load 1 sample draft from excel or standard sample
    subject = f"TEST EMAIL: Job Application - {config.sender_name}"
    body = (
        "Hello,\n\n"
        "This is a test email sent from your Bulk Job Application script to verify email delivery, "
        "HTML rendering, and the resume PDF attachment.\n\n"
        f"Please check if the attached resume ({config.attachment_display_name}) opens properly.\n\n"
        "Best regards,\n"
        f"{config.sender_name}\n"
        f"{config.sender_email}"
    )

    if config.excel_path.exists():
        try:
            records, _ = load_recipients_from_excel(config.excel_path)
            if records:
                sample = records[0]
                subject = f"[TEST] {sample.subject}"
                body = f"[TEST PREVIEW FOR {sample.company}]\n\n" + sample.body
        except Exception:
            pass

    print(f"\nSending test email to: {target_email}...")
    sender = EmailSender()
    success, msg = sender.connect()
    if not success:
        print(f"[FAILED] SMTP Connection Failed:\n{msg}")
        return

    ok, send_msg = sender.send_email(
        recipient_email=target_email,
        subject=subject,
        body_text=body,
        attachment_filename=config.attachment_display_name
    )
    sender.close()

    if ok:
        print(f"\n[OK] SUCCESS: Test email sent to {target_email}!")
        print("    Check your inbox and spam folder to inspect the formatting and attachment.")
    else:
        print(f"\n[FAILED]: Could not send test email: {send_msg}")


def run_bulk_send(skip_confirm: bool = False):
    print("\n--- START BULK SENDING ---")
    if not config.is_configured():
        print("[!] Email credentials not configured.")
        run_setup_wizard()
        if not config.is_configured():
            return

    if not config.attachment_path.exists():
        print(f"[FAILED] Error: Resume PDF file not found at: {config.attachment_path}")
        return

    if not config.excel_path.exists():
        print(f"[FAILED] Error: Excel file not found at: {config.excel_path}")
        return

    records, warnings = load_recipients_from_excel(config.excel_path)
    if not records:
        print("[FAILED] No valid recipient rows found in Excel.")
        return

    tracker = SentTracker(config.log_path)
    sent_emails = tracker.get_successful_emails()

    pending_records = [r for r in records if r.email.lower() not in sent_emails]
    total_found = len(records)
    total_sent = len(sent_emails)
    total_pending = len(pending_records)

    print(f"Total recipients in Excel: {total_found}")
    print(f"Already sent previously:   {total_sent}")
    print(f"Pending to send now:       {total_pending}")

    if total_pending == 0:
        print("\n[!] All recipients have already been sent emails according to sent_log.csv.")
        print("    If you want to re-send to everyone, choose Option 6 to reset the log.")
        return

    print("\nAnti-Spam Safety Settings:")
    print(f"  Delay between emails: {config.delay_min} to {config.delay_max} seconds")
    print(f"  Estimated completion time: {total_pending * (config.delay_min + config.delay_max) // 120} to {total_pending * config.delay_max // 60} minutes")
    print(f"  Attachment: {config.attachment_file} -> {config.attachment_display_name}")

    if not skip_confirm:
        confirm = input(f"\nAre you ready to send {total_pending} emails? (type 'yes' to proceed): ").strip().lower()
        if confirm not in ("yes", "y"):
            print("Bulk send cancelled.")
            return

    print("\nConnecting to SMTP server...")
    sender = EmailSender()
    success, msg = sender.connect()
    if not success:
        print(f"[FAILED] Could not connect to SMTP server:\n{msg}")
        return
    print("[OK] Connected successfully! Starting delivery...\n")

    success_count = 0
    fail_count = 0

    try:
        for idx, rec in enumerate(pending_records, start=1):
            prefix = f"[{idx}/{total_pending}] (#{rec.s_no} {rec.company})"
            print(f"{prefix} Sending to {rec.email}...", end=" ", flush=True)

            sent_ok, detail = sender.send_email(
                recipient_email=rec.email,
                subject=rec.subject,
                body_text=rec.body,
                attachment_filename=config.attachment_display_name
            )

            if sent_ok:
                print("[OK] DELIVERED")
                tracker.record_result(
                    s_no=rec.s_no,
                    email=rec.email,
                    company=rec.company,
                    subject=rec.subject,
                    status="SUCCESS",
                    details="Delivered"
                )
                success_count += 1
            else:
                print(f"[FAILED]: {detail}")
                tracker.record_result(
                    s_no=rec.s_no,
                    email=rec.email,
                    company=rec.company,
                    subject=rec.subject,
                    status="FAILED",
                    details=detail
                )
                fail_count += 1

            # Sleep delay between emails (except after the last one)
            if idx < total_pending:
                sleep_sec = random.randint(config.delay_min, config.delay_max)
                for sec_left in range(sleep_sec, 0, -1):
                    sys.stdout.write(f"\r  -> Throttling delay: {sec_left}s remaining... ")
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write("\r" + " " * 45 + "\r")
                sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n\n[!] Sending paused by user (Ctrl+C).")
        print("    All emails sent so far have been recorded in sent_log.csv.")
        print("    You can resume anytime without duplicate sends.")

    finally:
        sender.close()

    print("\n" + "=" * 60)
    print("                     BATCH SUMMARY")
    print("=" * 60)
    print(f" Successfully Sent:  {success_count}")
    print(f" Failed:             {fail_count}")
    print(f" Remaining Pending:  {total_pending - (success_count + fail_count)}")
    print(f" Log File:           {config.log_path.name}")
    print("=" * 60)


def run_view_history():
    print("\n--- SENT HISTORY & STATS ---")
    tracker = SentTracker(config.log_path)
    total_recs = 0
    if config.excel_path.exists():
        try:
            records, _ = load_recipients_from_excel(config.excel_path)
            total_recs = len(records)
        except Exception:
            pass

    stats = tracker.get_stats(total_recs)
    print(f"Total in Excel:  {stats['total']}")
    print(f"Total Sent:      {stats['success']}")
    print(f"Total Failed:    {stats['failed']}")
    print(f"Total Pending:   {stats['pending']}")

    if config.log_path.exists() and config.log_path.stat().st_size > 0:
        print(f"\nDetailed log is saved in: {config.log_path}")
        print("Showing last 10 entries:")
        print("-" * 72)
        try:
            import csv
            with open(config.log_path, "r", newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
                if len(rows) > 1:
                    header = rows[0]
                    for r in rows[-10:]:
                        print(" | ".join(r[:6]))
                else:
                    print("Log is currently empty.")
        except Exception as e:
            print(f"Error reading log: {e}")
    else:
        print("No sent history yet.")


def run_reset_log():
    tracker = SentTracker(config.log_path)
    confirm = input("\nAre you sure you want to reset the sent log? (yes/no): ").strip().lower()
    if confirm in ("yes", "y"):
        backup = tracker.reset_log()
        if backup:
            print(f"[OK] Sent log archived to: {Path(backup).name}")
        print("[OK] Sent log reset. Next run will send to all recipients from the start.")
    else:
        print("Reset cancelled.")


def interactive_menu():
    while True:
        print()
        print_banner()
        print("\nSelect an action:")
        print("  1. Send Test Email (Recommended first: send 1 email to yourself)")
        print("  2. Dry Run / Preview Recipient List (Verify 60 drafts & attachment)")
        print("  3. Start Bulk Sending (Send to all pending recipients with delays)")
        print("  4. View Sent History / Summary")
        print("  5. Configure / Update Email Credentials & App Password")
        print("  6. Reset Sent Log (Start from beginning)")
        print("  0. Exit")
        
        choice = input("\nEnter choice [0-6]: ").strip()
        if choice == "1":
            run_test_email()
        elif choice == "2":
            run_dry_run()
        elif choice == "3":
            run_bulk_send()
        elif choice == "4":
            run_view_history()
        elif choice == "5":
            run_setup_wizard()
        elif choice == "6":
            run_reset_log()
        elif choice in ("0", "q", "exit"):
            print("\nExiting. Good luck with your job applications!")
            break
        else:
            print("[!] Invalid option. Please choose between 0 and 6.")


def main():
    parser = argparse.ArgumentParser(description="Bulk Email Sender for Job Applications")
    parser.add_argument("--test", nargs="?", const="default", help="Send a test email to verify credentials and attachment")
    parser.add_argument("--dry-run", action="store_true", help="Preview recipients and attachments without sending")
    parser.add_argument("--send", action="store_true", help="Start sending bulk emails")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt when sending")
    parser.add_argument("--setup", action="store_true", help="Configure sender email and Google App Password")
    parser.add_argument("--status", action="store_true", help="Display sent statistics")
    parser.add_argument("--reset-log", action="store_true", help="Reset sent log")

    args = parser.parse_args()

    if args.setup:
        run_setup_wizard()
    elif args.test:
        target = None if args.test == "default" else args.test
        run_test_email(target)
    elif args.dry_run:
        run_dry_run()
    elif args.send:
        run_bulk_send(skip_confirm=args.yes)
    elif args.status:
        run_view_history()
    elif args.reset_log:
        run_reset_log()
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
