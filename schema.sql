CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room TEXT,
  author TEXT,
  text TEXT,
  "when" TEXT,
  image TEXT,
  media TEXT,
  reply_to INTEGER,  -- If this message is last, forward responses to the bot with this id
  state BLOB         -- Only forward to the bot if this state is a nonempty string of json data.
);

CREATE TABLE IF NOT EXISTS bots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room TEXT,
  name TEXT,
  responds_to TEXT,
  url TEXT
);
