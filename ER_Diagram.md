# ER Diagram

This ER diagram is derived from the MySQL model in `db/schema.sql`.

```mermaid
erDiagram
    teams {
        INT id PK
        VARCHAR name UK
        DATETIME created_at
    }

    members {
        INT id PK
        VARCHAR full_name
        VARCHAR email UK
        DATETIME created_at
    }

    team_members {
        INT team_id PK, FK
        INT member_id PK, FK
        DATETIME added_at
    }

    meeting_patient_details {
        INT id PK
        INT meeting_id FK
        VARCHAR medical_record_number
        VARCHAR patient_name
        DATE patient_date_of_birth
        TEXT patient_description
        VARCHAR doctor_name
        VARCHAR department_name
        TEXT meeting_agenda_note
        DATETIME created_at
    }

    meetings {
        INT id PK
        VARCHAR name
        TEXT organizer_note
        DATETIME created_at
    }

    meeting_attachments {
        INT id PK
        INT meeting_id FK
        VARCHAR medical_record_number
        VARCHAR doctor_name
        VARCHAR department_name
        VARCHAR file_name
        VARCHAR file_type
        BIGINT file_size
        LONGBLOB file_data
        DATETIME created_at
    }

    meeting_schedules {
        INT id PK
        INT meeting_id UK, FK
        DATE starts_at
        TIME start_time
        TIME end_time
        VARCHAR timezone
        ENUM schedule_type
        TEXT recurrence_rule
        DATE recurrence_end_date
        DATETIME created_at
    }

    meeting_invites {
        INT id PK
        INT meeting_id FK
        VARCHAR emails
        DATETIME invited_at
        ENUM status
    }

    meeting_invitee_responses {
        INT id PK
        INT meeting_id FK
        VARCHAR invitee_email
        VARCHAR response_token UK
        ENUM status
        DATETIME responded_at
        DATETIME created_at
    }

    teams ||--o{ team_members : has
    members ||--o{ team_members : belongs_to

    meetings ||--|| meeting_schedules : scheduled_as
    meetings ||--o{ meeting_patient_details : includes
    meeting_patient_details ||--o{ meeting_attachments : stores
    meetings ||--o{ meeting_invites : invites
    meetings ||--o{ meeting_invitee_responses : tracks
```

## Relationship Summary

- **teams ↔ members**: many-to-many through `team_members`.
- **meetings ↔ meeting_schedules**: one-to-one through `meeting_schedules.meeting_id` (unique foreign key).
- **meetings ↔ meeting_patient_details**: one-to-many. A meeting can have multiple patient detail rows.
- **meeting_patient_details ↔ meeting_attachments**: one-to-many through the composite foreign key on patient details.
- **meetings ↔ meeting_invites**: one-to-many. A meeting stores its invited email list in `meeting_invites`.
- **meetings ↔ meeting_invitee_responses**: one-to-many. Tracks per-invitee response tokens and RSVP status.

## Table Descriptions

### Core Tables

- **teams**: Organizational teams or groups.
- **members**: Individual members with email and full name.
- **team_members**: Junction table linking members to teams.

### Meeting Tables

- **meetings**: Core meeting entity with name and optional organizer notes.
- **meeting_schedules**: Scheduling information for each meeting (date, time, timezone, recurrence).
- **meeting_invites**: Stores invited email list per meeting and overall invite status.
- **meeting_invitee_responses**: Per-invitee response tokens and RSVP status.
- **meeting_attachments**: File attachments for meetings stored as binary data (LONGBLOB), linked to patient details.

### Medical/Patient Tables

- **meeting_patient_details**: Patient and doctor information that can optionally be linked to meetings. Includes medical record number, patient demographics, doctor details, and meeting agenda notes.

## Notes

- Junction tables (`team_members`) use composite primary keys to prevent duplicate mappings.
- Cascading deletes are enabled on foreign keys:
  - Deleting a team removes all `team_members` associations.
    - Deleting a member removes all `team_members` associations.
    - Deleting a meeting removes all `meeting_schedules`, `meeting_patient_details`, `meeting_attachments`, `meeting_invites`, and `meeting_invitee_responses`.
    - Deleting patient details removes linked `meeting_attachments` rows via the composite foreign key.
- **ENUM constraints**:
  - `meeting_schedules.schedule_type`: `one-time` or `recurring`
    - `meeting_invites.status`: `Pending`, `Accept`, `Decline`, or `Tentative`
    - `meeting_invitee_responses.status`: `Pending`, `Accept`, `Decline`, or `Tentative`
- **Patient details** are scoped to a meeting via `meeting_patient_details.meeting_id` with uniqueness enforced per meeting, medical record number, doctor, and department.
- **File attachments** are stored directly in the database as binary data (LONGBLOB) with metadata including file name, type, and size.
