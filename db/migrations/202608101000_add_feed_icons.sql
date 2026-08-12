-- migrate:up
ALTER TABLE rss_feeds ADD COLUMN icon_url TEXT;
ALTER TABLE rss_feeds ADD COLUMN icon_data BLOB;
ALTER TABLE rss_feeds ADD COLUMN icon_media_type TEXT;

ALTER TABLE news_sites ADD COLUMN icon_url TEXT;
ALTER TABLE news_sites ADD COLUMN icon_data BLOB;
ALTER TABLE news_sites ADD COLUMN icon_media_type TEXT;

-- migrate:down
ALTER TABLE news_sites DROP COLUMN icon_media_type;
ALTER TABLE news_sites DROP COLUMN icon_data;
ALTER TABLE news_sites DROP COLUMN icon_url;

ALTER TABLE rss_feeds DROP COLUMN icon_media_type;
ALTER TABLE rss_feeds DROP COLUMN icon_data;
ALTER TABLE rss_feeds DROP COLUMN icon_url;
