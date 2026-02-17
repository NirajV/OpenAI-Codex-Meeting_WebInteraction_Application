# Email-Based Meeting Acceptance & Calendar Integration

## 📧 Feature Overview

Your meeting application now supports **email-based meeting responses** with automatic calendar updates. Users can accept, decline, or mark as tentative directly from their email inbox, and all responses appear in the calendar view.

---

## 🎯 How It Works

### 1. **Meeting Creation with Email Invites**
When you create a meeting with invitee emails:
- Each invitee receives a unique email with their personal action links
- The system generates a secure token for each invitee-meeting pair
- Responses are tracked individually in the database

### 2. **Email Invitation Format**
Invitees receive an email with:
```
Meeting: [Meeting Name]
Meeting ID: [ID]
Date: [Date]
Time: [Start] - [End] ([Timezone])
Schedule: [Type]

--- RESPOND TO THIS INVITATION ---
ACCEPT:    http://localhost:3000/api/respond-to-meeting/{TOKEN}?action=accept
DECLINE:   http://localhost:3000/api/respond-to-meeting/{TOKEN}?action=decline
TENTATIVE: http://localhost:3000/api/respond-to-meeting/{TOKEN}?action=tentative
```

### 3. **Responding to Invitations**
Users click the appropriate link in their email to respond:
- ✓ **ACCEPT** - Confirms attendance
- ✕ **DECLINE** - Cannot attend
- ? **TENTATIVE** - May or may not attend

### 4. **Calendar View with Response Status**
The meeting calendar displays:
- **RSVP Status Summary**: Shows count of accepted, declined, tentative, and pending responses
- **Individual Response Details**: Lists each invitee with their response status and icon
- **Response Tracking**: Timestamps captured when responses are submitted

---

## 🗄️ Database Schema Changes

### New Table: `meeting_invitee_responses`
```sql
CREATE TABLE meeting_invitee_responses (
  id INT PRIMARY KEY AUTO_INCREMENT,
  meeting_id INT NOT NULL,
  invitee_email VARCHAR(255) NOT NULL,
  response_token VARCHAR(255) NOT NULL UNIQUE,
  status ENUM('pending', 'accepted', 'declined', 'tentative'),
  responded_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Status Values:**
- `pending` - Invitation sent, awaiting response
- `accepted` - Invitee confirmed attendance
- `declined` - Invitee confirmed non-attendance
- `tentative` - Invitee marked as tentative

---

## 🔗 API Endpoints

### Response Handler Endpoint
**GET** `/api/respond-to-meeting/{token}?action=accept|decline|tentative`

**Example URL:**
```
http://localhost:3000/api/respond-to-meeting/abc123token456?action=accept
```

**Response:**
```json
{
  "success": true,
  "message": "Your response (accept) has been recorded successfully!",
  "meeting": "Team Sync Meeting",
  "invitee_email": "user@example.com",
  "action": "accept"
}
```

### Meetings Endpoint (Enhanced)
**GET** `/api/meetings`

Now includes `responses` object showing all invitee responses:
```json
{
  "id": 27,
  "name": "Team Sync Meeting",
  "invitees": "niraj.k.vishwakarma@gmail.com, nirajkv@gmail.com",
  "responses": {
    "niraj.k.vishwakarma@gmail.com": "accepted",
    "nirajkv@gmail.com": "pending"
  },
  ...
}
```

---

## 🖥️ Frontend Display

### Calendar View Shows:
```
#27 Team Sync Meeting - one-time at 2026-02-25 (10:00 - 11:00) (UTC)

RSVP Status: ✓ 1 Accepted ⟳ 1 Pending

Details:
✓ niraj.k.vishwakarma@gmail.com (accepted)
⟳ nirajkv@gmail.com (pending)

Patients: [List of patients...]
```

**Status Icons:**
- ✓ = Accepted (green)
- ✕ = Declined (red)
- ? = Tentative (orange)
- ⟳ = Pending (gray)

---

## 🔐 Security Features

### Token-Based Responses
- Each invitee gets a **unique security token** (32-character URL-safe random string)
- Tokens are stored in the database with:
  - Meeting ID
  - Invitee email
  - Response status
  - Timestamp

### Response Verification
- Invalid tokens return: `{"error": "Invalid or expired response token."}`
- No authentication required (email recipients can click directly)
- Each token can only be used once per meeting-invitee pair

---

## 📋 Usage Examples

### Example 1: Create Meeting
```python
POST /api/meetings
{
  "name": "Q1 Planning",
  "startsAt": "2026-03-01",
  "startTime": "14:00",
  "endTime": "15:30",
  "timezone": "UTC",
  "scheduleType": "one-time",
  "inviteeEmail": "alice@example.com, bob@example.com"
}
```

**Response:**
```json
{
  "id": 28,
  "name": "Q1 Planning",
  "email_status": "Invitation emails sent successfully"
}
```

### Example 2: Invitee Accepts
Alice clicks the ACCEPT link in her email:
```
GET /api/respond-to-meeting/token_for_alice?action=accept
```

Database updates:
```
meeting_invitee_responses:
  - meeting_id: 28
  - invitee_email: alice@example.com
  - status: accepted
  - responded_at: 2026-02-16 14:30:00
```

### Example 3: View Calendar
```python
GET /api/meetings
```

Returns meeting with responses:
```json
{
  "id": 28,
  "name": "Q1 Planning",
  "responses": {
    "alice@example.com": "accepted",
    "bob@example.com": "pending"
  }
}
```

---

## ⚙️ Configuration

### Base URL for Email Links
The email links currently use: `http://localhost:3000/api/respond-to-meeting/`

For production, update in [app.py](app.py) line ~482:
```python
send_invite_emails(
    invitees_with_tokens,
    meeting_payload,
    base_url="https://your-domain.com"  # Change this
)
```

###  SMTP Configuration
Ensure `.env` file has:
```
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
SMTP_USE_TLS=true
```

---

## 🧪 Testing

### Run Test Script
```bash
python test_acceptance.py
```

This creates a test meeting and shows all expected functionality.

### Manual Testing
1. Create a meeting via the web form with your email
2. Check your inbox for the invitation
3. Click one of the action links
4. Return to the calendar view
5. See your response displayed with status icon

---

## 📊 Database Queries

### Get All Responses for a Meeting
```sql
SELECT invitee_email, status, responded_at
FROM meeting_invitee_responses
WHERE meeting_id = 27
ORDER BY invitee_email;
```

### Get Acceptance Summary
```sql
SELECT 
  status,
  COUNT(*) as count
FROM meeting_invitee_responses
WHERE meeting_id = 27
GROUP BY status;
```

### Get Pending Responses
```sql
SELECT invitee_email, created_at
FROM meeting_invitee_responses
WHERE meeting_id = 27 AND status = 'pending'
ORDER BY created_at;
```

---

## 🔄 Workflow Summary

```
1. User creates meeting with invitee emails
   ↓
2. System generates unique tokens for each invitee
   ↓
3. Tokens stored in meeting_invitee_responses table (status: pending)
   ↓
4. SMTP sends individual emails with action links
   ↓
5. Invitee clicks link → /api/respond-to-meeting/{token}?action=X
   ↓
6. Status updated in database + timestamp recorded
   ↓
7. Calendar view fetches responses and displays status
   ↓
8. User sees: "✓ 2 Accepted ✕ 1 Declined ⟳ 1 Pending"
```

---

## ✨ Features Implemented

✅ Email invitations with unique tokens  
✅ Accept/Decline/Tentative responses  
✅ Database tracking of all responses  
✅ Timestamp recording of responses  
✅ Calendar display with response summary  
✅ Individual response details  
✅ Security token validation  
✅ Unique constraint per invitee-meeting pair  
✅ SMTP integration for email delivery  
✅ Error handling and validation  

---

## 🐛 Troubleshooting

### Emails Not Received
1. Check `.env` EMAIL_ENABLED=true
2. Verify SMTP credentials in `.env`
3. Check SMTP_PASSWORD (should be app-specific for Gmail)
4. Check terminal logs for [EMAIL ERROR] messages

### Tokens Not Working
1. Verify token in URL matches database
2. Check if response already processed (status != pending)
3. Ensure meeting_id exists in meetings table

### Calendar Not Showing Responses
1. Refresh the page (Ctrl+F5)
2. Check browser console for JS errors
3. Verify meeting was created with invitee emails

---

**Created:** February 16, 2026  
**Feature:** Email-Based Meeting Acceptance with Calendar Integration  
**Status:** ✓ Fully Implemented and Tested
