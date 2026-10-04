@echo off
title Bulk Job Application Email Sender
cd /d "%~dp0"

echo ===================================================
echo     Launching Bulk Email Sender...
echo ===================================================

python send_emails.py

pause
