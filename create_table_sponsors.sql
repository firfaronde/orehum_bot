CREATE TABLE sponsors (
    id SERIAL PRIMARY KEY,
    player_id UUID NOT NULL,
    discord_id TEXT UNIQUE NOT NULL,
    FOREIGN KEY (player_id) REFERENCES player(user_id) ON DELETE CASCADE
);