import base64
import json
import os
import re
import secrets
import smtplib
from datetime import datetime
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import mysql.connector

# Load environment variables at the very start
BASE_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

PUBLIC_DIR = BASE_DIR / "public"
DB_DIR = BASE_DIR / "db"
SCHEMA_PATH = DB_DIR / "schema.sql"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


EMAIL_ENABLED = _parse_bool(os.environ.get("EMAIL_ENABLED"), False)


def _get_smtp_settings():
    return {
        "host": os.environ.get("SMTP_HOST"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER"),
        "password": os.environ.get("SMTP_PASSWORD"),
        "from": os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER"),
        "use_tls": _parse_bool(os.environ.get("SMTP_USE_TLS"), True),
    }


def _validate_smtp_settings(settings):
    missing = []
    if not settings["host"]:
        missing.append("SMTP_HOST")
    if not settings["port"]:
        missing.append("SMTP_PORT")
    if not settings["user"]:
        missing.append("SMTP_USER")
    if not settings["password"]:
        missing.append("SMTP_PASSWORD")
    if not settings["from"]:
        missing.append("SMTP_FROM")
    return missing


def send_invite_emails(invitees_with_tokens, meeting_payload, base_url="http://localhost:3000"):
    """Send meeting invite emails via SMTP with action buttons.
    
    Args:
        invitees_with_tokens: Dict mapping email -> response_token
        meeting_payload: Dict with meeting details
        base_url: Base URL for action links
        
    Returns:
        Tuple (success: bool, message: str)
    """
    settings = _get_smtp_settings()
    missing = _validate_smtp_settings(settings)
    if missing:
        return False, f"Missing SMTP settings: {', '.join(missing)}"

    try:
        for invitee_email, token in invitees_with_tokens.items():
            # Create action links
            accept_link = f"{base_url}/api/respond-to-meeting/{token}?action=accept"
            decline_link = f"{base_url}/api/respond-to-meeting/{token}?action=decline"
            tentative_link = f"{base_url}/api/respond-to-meeting/{token}?action=tentative"
            
            msg = EmailMessage()
            msg["Subject"] = f"Meeting Invite: {meeting_payload['name']}"
            msg["From"] = settings["from"]
            msg["To"] = invitee_email
            
            # Plain text version (fallback)
            plain_text = f"""You are invited to a meeting.

Meeting: {meeting_payload['name']}
Meeting ID: {meeting_payload['id']}
Date: {meeting_payload['startsAt']}
Time: {meeting_payload['startTime']} - {meeting_payload['endTime']} ({meeting_payload['timezone']})
Schedule: {meeting_payload['scheduleType']}
Recurrence: {meeting_payload.get('recurrenceRule') or 'N/A'}
Recurrence End: {meeting_payload.get('recurrenceEndDate') or 'N/A'}

--- RESPOND TO THIS INVITATION ---

ACCEPT:    {accept_link}
DECLINE:   {decline_link}
TENTATIVE: {tentative_link}

---
Please click the appropriate link or button to respond to this meeting invitation.
"""
            
            # HTML version with styled buttons
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #ffffff;
            padding: 30px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .meeting-details {{
            background-color: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .detail-row {{
            margin: 8px 0;
            padding: 5px 0;
        }}
        .detail-label {{
            font-weight: bold;
            color: #2c3e50;
            min-width: 120px;
            display: inline-block;
        }}
        .button-container {{
            display: flex;
            gap: 15px;
            margin: 30px 0;
            flex-wrap: wrap;
            justify-content: center;
        }}
        .button {{
            display: inline-block;
            padding: 14px 28px;
            margin: 10px 5px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            border: none;
            transition: all 0.3s ease;
            text-align: center;
            min-width: 140px;
        }}
        .button-accept {{
            background-color: #27ae60;
            color: white;
        }}
        .button-accept:hover {{
            background-color: #229954;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        .button-decline {{
            background-color: #e74c3c;
            color: white;
        }}
        .button-decline:hover {{
            background-color: #c0392b;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        .button-tentative {{
            background-color: #f39c12;
            color: white;
        }}
        .button-tentative:hover {{
            background-color: #d68910;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        .status-legend {{
            background-color: #f0f8ff;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
            border-left: 4px solid #3498db;
        }}
        .status-legend-item {{
            margin: 8px 0;
            font-size: 14px;
        }}
        .footer {{
            text-align: center;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #7f8c8d;
            font-size: 12px;
            margin-top: 30px;
        }}
        .icon {{
            margin-right: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>You Have Been Invited to a Meeting</h1>
        
        <div class="meeting-details">
            <div class="detail-row">
                <span class="detail-label">Meeting Name:</span> {meeting_payload['name']}
            </div>
            <div class="detail-row">
                <span class="detail-label">Meeting ID:</span> {meeting_payload['id']}
            </div>
            <div class="detail-row">
                <span class="detail-label">Date:</span> {meeting_payload['startsAt']}
            </div>
            <div class="detail-row">
                <span class="detail-label">Time:</span> {meeting_payload['startTime']} - {meeting_payload['endTime']} ({meeting_payload['timezone']})
            </div>
            <div class="detail-row">
                <span class="detail-label">Schedule:</span> {meeting_payload['scheduleType']}
            </div>
            <div class="detail-row">
                <span class="detail-label">Recurrence:</span> {meeting_payload.get('recurrenceRule') or 'N/A'}
            </div>
            <div class="detail-row">
                <span class="detail-label">Ends:</span> {meeting_payload.get('recurrenceEndDate') or 'N/A'}
            </div>
        </div>

        <h2 style="color: #2c3e50; margin-top: 30px;">Please Respond to this Invitation</h2>
        
        <p style="text-align: center; color: #555; margin: 20px 0;">
            Click the appropriate button below to let us know if you can attend:
        </p>
        
        <div class="button-container">
            <a href="{accept_link}" class="button button-accept" style="color: white;">
                <span class="icon">✓</span> Accept
            </a>
            <a href="{tentative_link}" class="button button-tentative" style="color: white;">
                <span class="icon">?</span> Tentative
            </a>
            <a href="{decline_link}" class="button button-decline" style="color: white;">
                <span class="icon">✕</span> Decline
            </a>
        </div>

        <div class="status-legend">
            <strong>Your Response Options:</strong>
            <div class="status-legend-item"><span class="icon">✓</span> <strong>Accept</strong> - I can attend this meeting</div>
            <div class="status-legend-item"><span class="icon">?</span> <strong>Tentative</strong> - I might be able to attend</div>
            <div class="status-legend-item"><span class="icon">✕</span> <strong>Decline</strong> - I cannot attend this meeting</div>
        </div>

        <p style="color: #7f8c8d; font-size: 14px; text-align: center; margin-top: 20px;">
            Your response will be automatically recorded and displayed in the calendar.
        </p>

        <div class="footer">
            <p>This is an automated message from Meeting Planner Pro.</p>
            <p>If you have questions about this meeting, please contact the organizer.</p>
        </div>
    </div>
</body>
</html>
"""
            
            msg.set_content(plain_text)
            msg.add_alternative(html_content, subtype='html')

            # Try SSL first (port 465), then TLS (port 587)
            port = settings["port"]
            if port == 465:
                # Use implicit SSL
                with smtplib.SMTP_SSL(settings["host"], port, timeout=10) as server:
                    server.login(settings["user"], settings["password"])
                    server.send_message(msg)
            else:
                # Use explicit TLS (port 587 or others)
                with smtplib.SMTP(settings["host"], port, timeout=10) as server:
                    if settings["use_tls"]:
                        server.starttls()
                    server.login(settings["user"], settings["password"])
                    server.send_message(msg)
        
        return True, "Emails sent successfully"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Failed to send emails: {str(e)}"


def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "12345678"),
        database=os.environ.get("DB_NAME", "General_meetings_db"),
    )


def initialize_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
        for statement in statements:
            cursor.execute(statement)
        conn.commit()
    finally:
        conn.close()


class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        payload = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))
    
    def _get_query_param(self, param_name, default=""):
        """Extract query parameter from URL."""
        parsed = urlparse(self.path)
        params = {}
        if parsed.query:
            for part in parsed.query.split("&"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    params[key] = value
        return params.get(param_name, default)

    def _serve_static(self, path):
        path = "/index.html" if path == "/" else path
        file_path = (PUBLIC_DIR / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(PUBLIC_DIR.resolve())) or not file_path.exists():
            self.send_error(404, "File not found")
            return

        content_type = "text/html"
        if file_path.suffix == ".css":
            content_type = "text/css"
        elif file_path.suffix == ".js":
            content_type = "application/javascript"

        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)

        # Handle meeting response links (accept/decline/tentative)
        if parsed.path.startswith("/api/respond-to-meeting/"):
            token = parsed.path.replace("/api/respond-to-meeting/", "").strip("/")
            action = self._get_query_param("action", "").lower()
            
            if action not in ["accept", "decline", "tentative"]:
                self._send_json({"error": "Invalid action. Must be accept, decline, or tentative."}, 400)
                return
            
            # Map action to database ENUM values
            status_map = {
                "accept": "Accept",
                "decline": "Decline",
                "tentative": "Tentative"
            }
            db_status = status_map[action]
            
            conn = get_db_connection()
            try:
                cursor = conn.cursor(dictionary=True)
                
                # Find the invitee response record
                cursor.execute(
                    "SELECT id, meeting_id, invitee_email, status FROM meeting_invitee_responses WHERE response_token = %s",
                    (token,)
                )
                response_record = cursor.fetchone()
                
                if not response_record:
                    self._send_json({"error": "Invalid or expired response token."}, 404)
                    return
                
                # Update the response status
                cursor.execute(
                    "UPDATE meeting_invitee_responses SET status = %s, responded_at = %s WHERE response_token = %s",
                    (db_status, datetime.now(), token)
                )
                
                # Get meeting details
                cursor.execute(
                    "SELECT name FROM meetings WHERE id = %s",
                    (response_record['meeting_id'],)
                )
                meeting = cursor.fetchone()
                
                conn.commit()
                
                self._send_json({
                    "success": True,
                    "message": f"Your response ({action}) has been recorded successfully!",
                    "meeting": meeting['name'] if meeting else "Unknown Meeting",
                    "invitee_email": response_record['invitee_email'],
                    "action": action
                }, 200)
            except Exception as e:
                self._send_json({"error": f"Error processing response: {str(e)}"}, 500)
            finally:
                conn.close()
            return

        if parsed.path == "/api/teams":
            conn = get_db_connection()
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id, name FROM teams ORDER BY name")
                rows = cursor.fetchall()
            finally:
                conn.close()
            self._send_json([dict(row) for row in rows])
            return

        if parsed.path == "/api/members":
            query = """
                SELECT m.id, m.full_name AS fullName, m.email,
                       COALESCE(GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ', '), '') AS teams
                FROM members m
                LEFT JOIN team_members tm ON tm.member_id = m.id
                LEFT JOIN teams t ON t.id = tm.team_id
                GROUP BY m.id, m.full_name, m.email
                ORDER BY m.full_name
            """
            conn = get_db_connection()
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query)
                rows = cursor.fetchall()
            finally:
                conn.close()
            self._send_json([dict(row) for row in rows])
            return

        if parsed.path == "/api/meetings":
            query = """
                SELECT me.id, me.name,
                       GROUP_CONCAT(DISTINCT CONCAT(mpd.id, '|', mpd.patient_name, '|', mpd.medical_record_number, '|',
                                    mpd.patient_date_of_birth, '|', mpd.doctor_name, '|', mpd.department_name, '|',
                                    COALESCE(mpd.meeting_agenda_note, ''), '|', COALESCE(mpd.patient_description, ''))
                                    ORDER BY mpd.patient_name SEPARATOR '||') AS patientsData,
                       COUNT(DISTINCT ma.id) AS attachmentCount,
                       GROUP_CONCAT(DISTINCT ma.file_name ORDER BY ma.file_name SEPARATOR ', ') AS attachmentNames,
                       GROUP_CONCAT(DISTINCT mi.emails SEPARATOR '; ') AS invitees,
                       GROUP_CONCAT(DISTINCT CONCAT(mir.invitee_email, '|', mir.status) ORDER BY mir.invitee_email SEPARATOR '||') AS inviteeResponses,
                       ms.starts_at AS startsAt,
                       ms.start_time AS startTime,
                       ms.end_time AS endTime,
                       ms.timezone,
                       ms.schedule_type AS scheduleType,
                       ms.recurrence_rule AS recurrenceRule,
                       ms.recurrence_end_date AS recurrenceEndDate
                FROM meetings me
                JOIN meeting_schedules ms ON ms.meeting_id = me.id
                LEFT JOIN meeting_patient_details mpd ON mpd.meeting_id = me.id
                LEFT JOIN meeting_attachments ma ON ma.meeting_id = me.id
                LEFT JOIN meeting_invites mi ON mi.meeting_id = me.id
                LEFT JOIN meeting_invitee_responses mir ON mir.meeting_id = me.id
                GROUP BY me.id, me.name, ms.starts_at, ms.start_time, ms.end_time, ms.timezone,
                         ms.schedule_type, ms.recurrence_rule, ms.recurrence_end_date
                ORDER BY ms.starts_at DESC, ms.start_time DESC
            """
            conn = get_db_connection()
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query)
                rows = cursor.fetchall()
                # Parse patients data
                processed_rows = []
                for row in rows:
                    processed_row = dict(row)
                    patients = []
                    if row['patientsData']:
                        for patient_str in row['patientsData'].split('||'):
                            parts = patient_str.split('|')
                            if len(parts) >= 8:
                                patients.append({
                                    'patientDetailId': int(parts[0]),
                                    'patientName': parts[1],
                                    'medicalRecordNumber': parts[2],
                                    'patientDateOfBirth': parts[3],
                                    'doctorName': parts[4],
                                    'departmentName': parts[5],
                                    'meetingAgendaNote': parts[6] if parts[6] else None,
                                    'patientDescription': parts[7] if parts[7] else None
                                })
                    processed_row['patients'] = patients
                    del processed_row['patientsData']
                    
                    # Parse invitee responses
                    invitee_responses = {}
                    if row['inviteeResponses']:
                        for response_str in row['inviteeResponses'].split('||'):
                            if '|' in response_str:
                                email, status = response_str.rsplit('|', 1)
                                if email not in invitee_responses:
                                    invitee_responses[email] = status
                    processed_row['responses'] = invitee_responses
                    if 'inviteeResponses' in processed_row:
                        del processed_row['inviteeResponses']
                    
                    processed_rows.append(processed_row)
            finally:
                conn.close()
            self._send_json(processed_rows)
            return

        if parsed.path == "/api/patient-details":
            query = """
                SELECT mpd.id,
                       mpd.meeting_id AS meetingId,
                       me.name AS meetingName,
                       mpd.medical_record_number AS medicalRecordNumber,
                       mpd.patient_name AS patientName,
                       mpd.patient_date_of_birth AS patientDateOfBirth,
                       mpd.patient_description AS patientDescription,
                       mpd.doctor_name AS doctorName,
                       mpd.department_name AS departmentName,
                       mpd.meeting_agenda_note AS meetingAgendaNote
                FROM meeting_patient_details mpd
                LEFT JOIN meetings me ON mpd.meeting_id = me.id
                ORDER BY mpd.created_at DESC, mpd.id DESC
            """
            conn = get_db_connection()
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query)
                rows = cursor.fetchall()
            finally:
                conn.close()
            self._send_json([dict(row) for row in rows])
            return

        self._serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self._read_json()

            if parsed.path == "/api/teams":
                name = (data.get("name") or "").strip()
                if not name:
                    self._send_json({"error": "Team name is required."}, 400)
                    return

                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO teams (name) VALUES (%s)", (name,))
                    conn.commit()
                    team_id = cursor.lastrowid
                finally:
                    conn.close()

                self._send_json({"id": team_id, "name": name}, 201)
                return

            if parsed.path == "/api/members":
                full_name = (data.get("fullName") or "").strip()
                email = (data.get("email") or "").strip().lower()
                team_ids = data.get("teamIds") or []
                if not full_name or not email:
                    self._send_json({"error": "Member full name and email are required."}, 400)
                    return

                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO members (full_name, email) VALUES (%s, %s)",
                        (full_name, email),
                    )
                    member_id = cursor.lastrowid
                    for team_id in team_ids:
                        cursor.execute(
                            "INSERT INTO team_members (team_id, member_id) VALUES (%s, %s)",
                            (int(team_id), member_id),
                        )
                    conn.commit()
                finally:
                    conn.close()

                self._send_json({"id": member_id, "fullName": full_name, "email": email}, 201)
                return

            if parsed.path == "/api/meetings":
                name = (data.get("name") or "").strip()
                starts_at = data.get("startsAt")
                start_time = data.get("startTime")
                end_time = data.get("endTime")
                timezone = (data.get("timezone") or "UTC").strip()
                schedule_type = data.get("scheduleType")
                recurrence_rule = (data.get("recurrenceRule") or "").strip() or None
                recurrence_end = data.get("recurrenceEndDate") or None
                invitee_email = (data.get("inviteeEmail") or "").strip() or None

                invitee_emails = None
                if invitee_email:
                    raw_emails = [email.strip().lower() for email in invitee_email.split(",") if email.strip()]
                    unique_emails = []
                    seen = set()
                    for email in raw_emails:
                        if email not in seen:
                            seen.add(email)
                            unique_emails.append(email)
                    invalid_emails = [email for email in unique_emails if not EMAIL_RE.match(email)]
                    if invalid_emails:
                        self._send_json({"error": f"Invalid invitee email(s): {', '.join(invalid_emails)}"}, 400)
                        return
                    invitee_emails = ", ".join(unique_emails) if unique_emails else None

                if not name or not starts_at or not schedule_type or not start_time or not end_time:
                    self._send_json(
                        {
                            "error": "Meeting name, start date/time, start time, end time and schedule type are required."
                        },
                        400,
                    )
                    return
                if schedule_type not in ["one-time", "recurring"]:
                    self._send_json({"error": "Schedule type must be one-time or recurring."}, 400)
                    return
                if schedule_type == "recurring" and not recurrence_rule:
                    self._send_json({"error": "Recurrence rule is required for recurring meetings."}, 400)
                    return

                if EMAIL_ENABLED and invitee_email:
                    settings = _get_smtp_settings()
                    missing = _validate_smtp_settings(settings)
                    if missing:
                        self._send_json({"error": f"Email enabled but missing SMTP settings: {', '.join(missing)}"}, 500)
                        return

                datetime.fromisoformat(starts_at)
                parsed_start_time = datetime.strptime(start_time, "%H:%M")
                parsed_end_time = datetime.strptime(end_time, "%H:%M")
                if parsed_end_time <= parsed_start_time:
                    self._send_json({"error": "Meeting end time must be after start time."}, 400)
                    return

                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO meetings (name) VALUES (%s)", (name,))
                    meeting_id = cursor.lastrowid
                    cursor.execute(
                        """
                        INSERT INTO meeting_schedules
                        (meeting_id, starts_at, start_time, end_time, timezone, schedule_type, recurrence_rule, recurrence_end_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            meeting_id,
                            starts_at,
                            start_time,
                            end_time,
                            timezone,
                            schedule_type,
                            recurrence_rule if schedule_type == "recurring" else None,
                            recurrence_end if schedule_type == "recurring" else None,
                        ),
                    )

                    if invitee_emails:
                        cursor.execute(
                            "INSERT INTO meeting_invites (meeting_id, emails) VALUES (%s, %s)",
                            (meeting_id, invitee_emails),
                        )

                    # Send invite emails if enabled
                    email_error = None
                    email_success = False
                    if EMAIL_ENABLED and invitee_emails:
                        # Parse email list (handle both ", " and "," separators)
                        email_list = [e.strip() for e in invitee_emails.replace(", ", ",").split(",") if e.strip()]
                        print(f"[EMAIL DEBUG] Sending invites to: {email_list}")
                        
                        # Generate tokens and store invitee responses
                        invitees_with_tokens = {}
                        for invitee_email in email_list:
                            token = secrets.token_urlsafe(32)
                            invitees_with_tokens[invitee_email] = token
                            cursor.execute(
                                "INSERT INTO meeting_invitee_responses (meeting_id, invitee_email, response_token) VALUES (%s, %s, %s)",
                                (meeting_id, invitee_email, token),
                            )
                        
                        # Send emails with action links
                        success, msg = send_invite_emails(
                            invitees_with_tokens,
                            {
                                "id": meeting_id,
                                "name": name,
                                "startsAt": starts_at,
                                "startTime": start_time,
                                "endTime": end_time,
                                "timezone": timezone,
                                "scheduleType": schedule_type,
                                "recurrenceRule": recurrence_rule,
                                "recurrenceEndDate": recurrence_end,
                            },
                        )
                        if success:
                            print(f"[EMAIL SUCCESS] Emails sent successfully: {msg}")
                            email_success = True
                        else:
                            print(f"[EMAIL ERROR] {msg}")
                            email_error = msg
                    elif not EMAIL_ENABLED:
                        print("[EMAIL DEBUG] EMAIL_ENABLED is False, skipping email")
                    else:
                        print("[EMAIL DEBUG] No invitee emails provided")

                    conn.commit()
                    
                    # Warn if email failed but meeting was created
                    response = {"id": meeting_id, "name": name}
                    if email_success:
                        response["email_status"] = "Invitation emails sent successfully"
                    elif email_error:
                        response["warning"] = f"Meeting created but email sending failed: {email_error}"
                    elif EMAIL_ENABLED and not invitee_emails:
                        response["note"] = "No invitee emails provided, no invitations sent"
                    elif not EMAIL_ENABLED:
                        response["note"] = "EMAIL_ENABLED is false, invitations were not sent"
                    
                    self._send_json(response, 201)
                finally:
                    conn.close()
                return

            if parsed.path == "/api/patient-details":
                meeting_id = data.get("meetingId")
                medical_record_number = (data.get("medicalRecordNumber") or "").strip()
                patient_name = (data.get("patientName") or "").strip()
                patient_date_of_birth = data.get("patientDateOfBirth")
                patient_description = (data.get("patientDescription") or "").strip() or None
                doctor_name = (data.get("doctorName") or "").strip()
                department_name = (data.get("departmentName") or "").strip()
                meeting_agenda_note = (data.get("meetingAgendaNote") or "").strip() or None
                attachments = data.get("attachments") or []

                # Convert meeting_id to int
                try:
                    meeting_id = int(meeting_id) if meeting_id else None
                except (ValueError, TypeError):
                    meeting_id = None

                # Meeting ID is required
                if not meeting_id:
                    self._send_json({"error": "Meeting ID is required."}, 400)
                    return

                if (
                    not medical_record_number
                    or not patient_name
                    or not patient_date_of_birth
                    or not doctor_name
                    or not department_name
                ):
                    self._send_json(
                        {
                            "error": "Medical record number, patient name/date of birth, doctor name and department are required."
                        },
                        400,
                    )
                    return

                datetime.fromisoformat(patient_date_of_birth)

                conn = get_db_connection()
                try:
                    cursor = conn.cursor(dictionary=True)
                    
                    # Validate meeting exists
                    cursor.execute("SELECT id FROM meetings WHERE id = %s", (meeting_id,))
                    meeting = cursor.fetchone()
                    if not meeting:
                        self._send_json({"error": "Meeting ID not found."}, 400)
                        return

                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO meeting_patient_details
                        (meeting_id, medical_record_number, patient_name, patient_date_of_birth, patient_description, doctor_name, department_name, meeting_agenda_note)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            meeting_id,
                            medical_record_number,
                            patient_name,
                            patient_date_of_birth,
                            patient_description,
                            doctor_name,
                            department_name,
                            meeting_agenda_note,
                        ),
                    )
                    patient_detail_id = cursor.lastrowid

                    for attachment in attachments:
                        file_name = (attachment.get("fileName") or "").strip()
                        file_type = (attachment.get("fileType") or "").strip() or None
                        file_data = attachment.get("fileData")
                        if not file_name or not file_data:
                            continue
                        blob_data = base64.b64decode(file_data, validate=True)
                        cursor.execute(
                            """
                            INSERT INTO meeting_attachments 
                            (meeting_id, medical_record_number, doctor_name, department_name, file_name, file_type, file_size, file_data)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                meeting_id,
                                medical_record_number,
                                doctor_name,
                                department_name,
                                file_name,
                                file_type,
                                len(blob_data),
                                blob_data,
                            ),
                        )

                    conn.commit()
                finally:
                    conn.close()

                self._send_json(
                    {
                        "id": patient_detail_id,
                        "meetingId": meeting_id,
                        "patientName": patient_name,
                    },
                    201,
                )
                return

            self._send_json({"error": "Not found"}, 404)
        except mysql.connector.IntegrityError as error:
            self._send_json({"error": str(error)}, 400)
        except ValueError as error:
            self._send_json({"error": f"Invalid date/time: {error}"}, 400)
        except Exception as error:
            self._send_json({"error": str(error)}, 500)


if __name__ == "__main__":
    initialize_db()
    port = int(os.environ.get("PORT", "3000"))
    server = HTTPServer(("0.0.0.0", port), AppHandler)
    print(f"Server running at http://localhost:{port}")
    server.serve_forever()
