# OpenAI-Codex-Meeting_WebInteraction_Application

A lightweight web app to:
1. Create multiple teams.
2. Add members and map them to teams.
3. Create one-time or recurring meetings and invite members.
4. Persist all data in normalized MySQL tables.

## Setup
1. Install MySQL server and ensure it is running.
2. Install the Python MySQL driver:
```bash
pip install mysql-connector-python
```
Optional: load `.env` automatically.
```bash
pip install python-dotenv
```
Or install everything at once:
```bash
pip install -r requirements.txt
```
3. Create the database and run the schema:
```bash
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -h 127.0.0.1 -P 3306 -u root -p12345678 -e "CREATE DATABASE IF NOT EXISTS General_meetings_db;"
Get-Content db\schema.sql | "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -h 127.0.0.1 -P 3306 -u root -p12345678 General_meetings_db
```
4. Update database settings in `.env` if needed.

## Run
```bash
python app.py
```

Then open `http://localhost:3000`.

## Email Invites (SMTP)
To send meeting invite emails, configure these environment variables (e.g., in `.env`):

```bash
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=niraj.k.vishwakarma@gmail.com
SMTP_PASSWORD=ynqv ocdz zauh iirc
SMTP_FROM=niraj.k.vishwakarma@gmail.com
SMTP_USE_TLS=true
```

Notes:
- Gmail requires an app password if 2FA is enabled.
- If `EMAIL_ENABLED` is true and SMTP settings are missing, meeting creation will return an error.
