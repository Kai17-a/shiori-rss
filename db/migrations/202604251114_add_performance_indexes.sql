-- migrate:up
CREATE INDEX IF NOT EXISTS idx_bookmarks_created_id
  ON bookmarks(created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_bookmarks_folder_created_id
  ON bookmarks(folder_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_bookmarks_favorite_created_id
  ON bookmarks(is_favorite, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_bookmark_tags_tag_bookmark
  ON bookmark_tags(tag_id, bookmark_id);

CREATE INDEX IF NOT EXISTS idx_rss_feeds_title_id
  ON rss_feeds(title ASC, id ASC);

CREATE INDEX IF NOT EXISTS idx_rss_feed_articles_feed_published_id
  ON rss_feed_articles(feed_id, published DESC, id DESC);

-- migrate:down
DROP INDEX IF EXISTS idx_rss_feed_articles_feed_published_id;
DROP INDEX IF EXISTS idx_rss_feeds_title_id;
DROP INDEX IF EXISTS idx_bookmark_tags_tag_bookmark;
DROP INDEX IF EXISTS idx_bookmarks_favorite_created_id;
DROP INDEX IF EXISTS idx_bookmarks_folder_created_id;
DROP INDEX IF EXISTS idx_bookmarks_created_id;
