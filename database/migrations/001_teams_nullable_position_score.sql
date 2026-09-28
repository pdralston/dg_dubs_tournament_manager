-- Migration: Make teams.position and teams.score nullable
-- This allows teams to be persisted at generation time (before results are recorded)

ALTER TABLE teams MODIFY COLUMN position INT NULL;
ALTER TABLE teams MODIFY COLUMN score INT NULL;
