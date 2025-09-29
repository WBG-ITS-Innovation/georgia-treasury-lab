-- === vNext additions (audit-friendly metadata) ===
ALTER TABLE rule_atoms ADD COLUMN severity      TEXT DEFAULT 'medium';
ALTER TABLE rule_atoms ADD COLUMN category      TEXT DEFAULT 'contract:bank';
ALTER TABLE rule_atoms ADD COLUMN applicability TEXT DEFAULT 'retail';
ALTER TABLE rule_atoms ADD COLUMN version       TEXT DEFAULT 'nbkr-2025.01';
ALTER TABLE rule_atoms ADD COLUMN effective_from TEXT;
ALTER TABLE rule_atoms ADD COLUMN effective_to   TEXT;
ALTER TABLE rule_atoms ADD COLUMN updated_at     INTEGER;

-- === Helper: explicit anchors to KB sections/URLs ===
CREATE TABLE IF NOT EXISTS rule_support(
  id INTEGER PRIMARY KEY,
  rule_id INTEGER NOT NULL,
  doc_id  INTEGER,
  section TEXT,
  url     TEXT,
  snippet TEXT,
  FOREIGN KEY(rule_id) REFERENCES rule_atoms(id)
);

-- === Helper: regex/keyword hooks to boost precision/recall ===
CREATE TABLE IF NOT EXISTS rule_tests(
  id INTEGER PRIMARY KEY,
  rule_id INTEGER NOT NULL,
  kind    TEXT,                 -- 'regex'|'keyword'|'negation'|'llm'
  pattern TEXT,
  weight  REAL DEFAULT 1.0,
  notes   TEXT,
  FOREIGN KEY(rule_id) REFERENCES rule_atoms(id)
);
