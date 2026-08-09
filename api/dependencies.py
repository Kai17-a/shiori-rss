from api.services.ask_ai_service import AskAIService
from api.services.article_analysis_service import ArticleAnalysisService
from api.services.dashboard_service import DashboardService
from api.services.news_site_service import NewsSiteService
from api.services.rss_feed_service import RSSFeedService
from api.services.settings_service import SettingsService


def get_ask_ai_service() -> AskAIService:
    return AskAIService()


def get_article_analysis_service() -> ArticleAnalysisService:
    return ArticleAnalysisService()


def get_dashboard_service() -> DashboardService:
    return DashboardService()


def get_news_site_service() -> NewsSiteService:
    return NewsSiteService()


def get_rss_feed_service() -> RSSFeedService:
    return RSSFeedService()


def get_settings_service() -> SettingsService:
    return SettingsService()
