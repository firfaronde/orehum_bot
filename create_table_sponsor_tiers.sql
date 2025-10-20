CREATE TABLE sponsors_tiers (
    id SERIAL PRIMARY KEY,
    sponsor_id INT NOT NULL,
    tier INT NOT NULL,
    oocColor TEXT NOT NULL,
    havePriorityJoin BOOLEAN NOT NULL DEFAULT FALSE,
    extraSlots INT NOT NULL DEFAULT 0,
    allowedMarkings TEXT[] NOT NULL DEFAULT '{}',
    ghostTheme TEXT NOT NULL DEFAULT 'light',
    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
);