CREATE TABLE IF NOT EXISTS jobs (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  uid                TEXT NOT NULL UNIQUE,
  source_file        TEXT,
  source_key         TEXT,
  name               TEXT,
  prompt             TEXT NOT NULL,
  negative_prompt    TEXT,
  tags               TEXT NOT NULL DEFAULT '[]',
  notes              TEXT,

  width              INTEGER NOT NULL DEFAULT 1024,
  height             INTEGER NOT NULL DEFAULT 1024,
  steps              INTEGER NOT NULL DEFAULT 20,
  cfg                REAL NOT NULL DEFAULT 1.0,
  guidance           REAL NOT NULL DEFAULT 3.5,
  sampler            TEXT NOT NULL DEFAULT 'euler',
  scheduler          TEXT NOT NULL DEFAULT 'simple',
  seed               INTEGER,
  quantization       TEXT,
  unet_filename      TEXT,

  status             TEXT NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','running','done','failed','cancelled')),
  comfyui_prompt_id  TEXT,
  comfyui_client_id  TEXT,
  output_path        TEXT,
  output_filename    TEXT,
  error_message      TEXT,
  retry_count        INTEGER NOT NULL DEFAULT 0,

  created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  started_at         TEXT,
  finished_at        TEXT,

  UNIQUE (source_file, source_key)
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs (status, created_at);

CREATE TABLE IF NOT EXISTS schema_migrations (
  version    INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
