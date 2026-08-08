from api.services.news_site_service import NewsSiteService
from api.services.rss_feed_service import RSSFeedService
from api.services.settings_service import SettingsService


def get_news_site_service() -> NewsSiteService:
    return NewsSiteService()


def get_rss_feed_service() -> RSSFeedService:
    return RSSFeedService()


def get_settings_service() -> SettingsService:
    return SettingsService()
