BEGIN;

CREATE TABLE IF NOT EXISTS system_bootstrap_state (
    id           SMALLINT PRIMARY KEY CHECK (id = 1),
    completed    BOOLEAN NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO system_bootstrap_state (id, completed, completed_at)
VALUES (1, TRUE, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO UPDATE
SET completed = EXCLUDED.completed,
    completed_at = EXCLUDED.completed_at;

COMMIT;