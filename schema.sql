CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room TEXT CHECK (room != ''), -- There is no "default" empty-name room.
  author TEXT,
  kind TEXT DEFAULT 'user' NOT NULL, -- 'user', 'system', or 'bot'.
  text TEXT,
  "when" TEXT,  -- Seconds since the epoch.
  image TEXT,
  media TEXT,
  js TEXT,   -- URL to a script to load on the page.
  css TEXT,  -- URL to a stylesheet to load on the page.
  from_bot INTEGER,  -- Non-null only if this message is from a bot.
  base_url TEXT,     -- Any non-absolute URLs in this message (in the HTML text, or image/media/js/css) should be taken
                     -- relative to this base_url. This is the bot url if the message is from a bot. If left as null,
                     -- relative URLs work as usual in the browser.
  state BLOB         -- Only forward to the bot if this state is a nonempty string of json data.
);

CREATE INDEX IF NOT EXISTS messages_byroom ON messages (room, id);

CREATE TABLE IF NOT EXISTS bots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room TEXT CHECK (room != ''), -- There is no "default" empty-name room.
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
