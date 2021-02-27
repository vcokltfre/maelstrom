CREATE TABLE IF NOT EXISTS Users (
    id              BIGINT NOT NULL,
    guildid         BIGINT NOT NULL,
    xp              BIGINT NOT NULL DEFAULT 0,
    monthly_xp      BIGINT NOT NULL DEFAULT 0,
    banned          BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id, guildid)
);

CREATE TABLE IF NOT EXISTS Guilds (
    id              BIGINT NOT NULL PRIMARY KEY,
    prefix          VARCHAR(255) NOT NULL DEFAULT '!',
    config          TEXT NOT NULL DEFAULT '{}',
    banned          BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS APIKeys (
    guildid         BIGINT NOT NULL,
    token           VARCHAR(64) NOT NULL PRIMARY KEY,
    permission      VARCHAR(255) NOT NULL DEFAULT 'fetch'
);
