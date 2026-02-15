# ER Diagram

This ER diagram is derived from the SQLite model in `db/schema.sql`.

```mermaid
erDiagram
    teams {
        INTEGER id PK
        TEXT name UK
        TEXT created_at
    }

    members {
        INTEGER id PK
        TEXT full_name
        TEXT email UK
        TEXT created_at
    }

    team_members {
        INTEGER team_id PK, FK
        INTEGER member_id PK, FK
        TEXT added_at
    }

    meetings {
        INTEGER id PK
        TEXT name
        TEXT organizer_note
        TEXT created_at
    }

    meeting_schedules {
        INTEGER id PK
        INTEGER meeting_id UK, FK
        TEXT starts_at
        TEXT start_time
        TEXT end_time
        TEXT timezone
        TEXT schedule_type
        TEXT recurrence_rule
        TEXT recurrence_end_date
        TEXT created_at
    }

    meeting_invites {
        INTEGER meeting_id PK, FK
        INTEGER member_id PK, FK
        TEXT invited_at
        TEXT status
    }

    teams ||--o{ team_members : has
    members ||--o{ team_members : belongs_to

    meetings ||--|| meeting_schedules : scheduled_as

    meetings ||--o{ meeting_invites : invites
    members ||--o{ meeting_invites : receives
```

## Relationship Summary

- **teams ↔ members**: many-to-many through `team_members`.
- **meetings ↔ meeting_schedules**: one-to-one through `meeting_schedules.meeting_id` (unique foreign key).
- **meetings ↔ members**: many-to-many through `meeting_invites`.

## Notes

- Junction tables (`team_members`, `meeting_invites`) use composite primary keys to prevent duplicate mappings.
- Cascading deletes are enabled on all foreign keys in the schema, so related join/schedule rows are removed when a parent record is deleted.
- `meeting_schedules.schedule_type` is constrained to `one-time` or `recurring`, and invite `status` is constrained to `pending`, `accepted`, or `declined`.
