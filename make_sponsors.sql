CREATE TABLE sponsors (
    id SERIAL PRIMARY KEY,
    player_id UUID NOT NULL UNIQUE,
    discord_id TEXT UNIQUE NOT NULL,
    FOREIGN KEY (player_id) REFERENCES player(user_id) ON DELETE CASCADE
);

CREATE TABLE sponsors_tiers (
    id SERIAL PRIMARY KEY,
    sponsor_id INT NOT NULL UNIQUE,
    tier INT NOT NULL,
    oocColor TEXT NOT NULL,
    havePriorityJoin BOOLEAN NOT NULL DEFAULT FALSE,
    extraSlots INT NOT NULL DEFAULT 0,
    allowedMarkings TEXT[] NOT NULL DEFAULT '{}',
    ghostTheme TEXT NOT NULL DEFAULT 'light',
    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
);
