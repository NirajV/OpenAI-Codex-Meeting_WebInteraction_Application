import json
import os
from datetime import UTC, datetime, timedelta
from urllib import error as urllib_error
from urllib import request as urllib_request

import mysql.connector
import pytest

BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000")


def _request_json(method, path, payload=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib_request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib_request.urlopen(req, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _server_available():
    try:
        _request_json("GET", "/api/teams")
        return True
    except Exception:
        return False


def _create_meeting():
    now_utc = datetime.now(UTC)
    starts_at = (now_utc.date() + timedelta(days=1)).isoformat()
    meeting_data = {
        "name": f"Team Sync Meeting {now_utc.strftime('%Y%m%d%H%M%S')}",
        "startsAt": starts_at,
        "startTime": "10:00",
        "endTime": "11:00",
        "timezone": "UTC",
        "scheduleType": "one-time",
        "inviteeEmail": "niraj.k.vishwakarma@gmail.com, nirajkv@gmail.com",
    }
    status, result = _request_json("POST", "/api/meetings", meeting_data)
    return status, result


def _find_meeting(meeting_id):
    status, meetings = _request_json("GET", "/api/meetings")
    if status != 200:
        return None
    for meeting in meetings:
        if meeting.get("id") == meeting_id:
            return meeting
    return None


def _get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "12345678"),
        database=os.environ.get("DB_NAME", "General_meetings_db"),
    )


def _get_response_token(meeting_id):
    conn = _get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT response_token FROM meeting_invitee_responses WHERE meeting_id = %s LIMIT 1",
            (meeting_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _get_response_status(meeting_id, token):
    conn = _get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM meeting_invitee_responses WHERE meeting_id = %s AND response_token = %s",
            (meeting_id, token),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


@pytest.fixture(scope="module", autouse=True)
def _require_server():
    if not _server_available():
        pytest.skip(f"Server not reachable at {BASE_URL}")


def test_create_meeting_with_invitees():
    status, result = _create_meeting()
    assert status == 201
    assert "id" in result
    assert result.get("name")

    meeting_view = result
    if not result.get("timezone") or not result.get("teamsJoinUrl"):
        meeting_view = _find_meeting(result["id"])

    assert meeting_view
    assert meeting_view.get("timezone") == "EST"
    teams_join_url = meeting_view.get("teamsJoinUrl")
    assert teams_join_url
    assert teams_join_url.startswith("https://teams.microsoft.com/l/meeting/new?")


def test_accept_invitation_records_response():
    status, result = _create_meeting()
    assert status == 201
    meeting_id = result["id"]

    try:
        token = _get_response_token(meeting_id)
    except mysql.connector.Error as exc:
        pytest.skip(f"Database not reachable: {exc}")

    if not token:
        pytest.skip("No response token generated. EMAIL_ENABLED may be false.")

    try:
        status, payload = _request_json(
            "GET", f"/api/respond-to-meeting/{token}?action=accept"
        )
    except urllib_error.HTTPError as exc:
        pytest.fail(f"Response endpoint failed: HTTP {exc.code}")

    assert status == 200
    assert payload.get("success") is True
    assert payload.get("action") == "accept"

    db_status = _get_response_status(meeting_id, token)
    assert db_status == "Accept"
