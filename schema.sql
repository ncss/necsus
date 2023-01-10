CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room TEXT CHECK (room != ""), -- There is no "default" empty-name room.
  author TEXT,
  kind TEXT DEFAULT "user" NOT NULL, -- 'user', 'system', or 'bot'.
  text TEXT,
  "when" TEXT,
  image TEXT,
  media TEXT,
  from_bot INTEGER,  -- Non-null only if this message is from a bot.
  state BLOB         -- Only forward to the bot if this state is a nonempty string of json data.
);

CREATE INDEX IF NOT EXISTS messages_byroom ON messages (room, id);

CREATE TABLE IF NOT EXISTS bots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room TEXT CHECK (room != ""), -- There is no "default" empty-name room.
  name TEXT,
  responds_to TEXT,
  url TEXT
);

-- Contains the last-cleared-message id of each room, so that we can replay clears onto clients that
-- disconnected and then reconnected.
CREATE TABLE IF NOT EXISTS clears (
  room TEXT PRIMARY KEY,
  last_cleared_id INTEGER
);
