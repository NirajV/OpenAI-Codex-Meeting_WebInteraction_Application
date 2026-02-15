import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import mysql.connector

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
DB_DIR = BASE_DIR / "db"
SCHEMA_PATH = DB_DIR / "schema.sql"

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass


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
        for _ in cursor.execute(schema_sql, multi=True):
            pass
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
                       COALESCE(GROUP_CONCAT(t.name SEPARATOR ', '), '') AS teams
                FROM members m
                LEFT JOIN team_members tm ON tm.member_id = m.id
                LEFT JOIN teams t ON t.id = tm.team_id
                GROUP BY m.id
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
                       ms.starts_at AS startsAt,
                       ms.start_time AS startTime,
                       ms.end_time AS endTime,
                       ms.timezone,
                       ms.schedule_type AS scheduleType,
                       ms.recurrence_rule AS recurrenceRule,
                       ms.recurrence_end_date AS recurrenceEndDate,
                       GROUP_CONCAT(CONCAT(m.full_name, ' <', m.email, '>') SEPARATOR '; ') AS invitees
                FROM meetings me
                JOIN meeting_schedules ms ON ms.meeting_id = me.id
                LEFT JOIN meeting_invites mi ON mi.meeting_id = me.id
                LEFT JOIN members m ON m.id = mi.member_id
                GROUP BY me.id
                ORDER BY ms.starts_at DESC
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
                finally:
                    conn.close()
                self._send_json({"id": cursor.lastrowid, "name": name}, 201)
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
                invitee_ids = data.get("inviteeIds") or []

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
                    for member_id in invitee_ids:
                        cursor.execute(
                            "INSERT INTO meeting_invites (meeting_id, member_id) VALUES (%s, %s)",
                            (meeting_id, int(member_id)),
                        )
                    conn.commit()
                finally:
                    conn.close()
                self._send_json({"message": "Meeting created successfully.", "meetingId": meeting_id}, 201)
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
