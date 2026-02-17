import json
import urllib.request

meeting_data = {
    "name": "Test Meeting",
    "startsAt": "2026-02-20",
    "startTime": "08:00",
    "endTime": "09:00",
    "timezone": "UTC",
    "scheduleType": "one-time",
    "inviteeEmail": "niraj.k.vishwakarma@gmail.com, nirajkv@gmail.com"
}

print("[TEST] Creating meeting...")
print(json.dumps(meeting_data, indent=2))

try:
    payload = json.dumps(meeting_data).encode('utf-8')
    req = urllib.request.Request(
        "http://localhost:3000/api/meetings",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print("\n[SUCCESS] Meeting created!")
        print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    error_msg = e.read().decode('utf-8')
    print(f"\n[ERROR] HTTP {e.code}")
    print(error_msg)
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
