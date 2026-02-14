PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS teams (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS members (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS team_members (
  team_id INTEGER NOT NULL,
  member_id INTEGER NOT NULL,
  added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (team_id, member_id),
  FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
  FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS meetings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  organizer_note TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meeting_schedules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  meeting_id INTEGER NOT NULL UNIQUE,
  starts_at TEXT NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  schedule_type TEXT NOT NULL CHECK (schedule_type IN ('one-time', 'recurring')),
  recurrence_rule TEXT,
  recurrence_end_date TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS meeting_invites (
  meeting_id INTEGER NOT NULL,
  member_id INTEGER NOT NULL,
  invited_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
  PRIMARY KEY (meeting_id, member_id),
  FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE,
  FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);
