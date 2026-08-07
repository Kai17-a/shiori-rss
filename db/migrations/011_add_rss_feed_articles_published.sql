-- migrate:up
ALTER TABLE rss_feed_articles ADD COLUMN published DATETIME;

-- migrate:down
ALTER TABLE rss_feed_articles DROP COLUMN published;
