from api.services.ask_ai_service import AskAIService
from api.services.ai_article_data_service import AIArticleDataService
from api.services.article_analysis_service import ArticleAnalysisService
from api.services.article_service import ArticleService
from api.services.dashboard_service import DashboardService
from api.services.github_repository_service import GitHubRepositoryService
from api.services.docker_image_service import DockerImageService
from api.services.it_trend_service import ITTrendService
from api.services.news_site_service import NewsSiteService
from api.services.rss_feed_service import RSSFeedService
from api.services.settings_service import SettingsService


def get_ask_ai_service() -> AskAIService:
    return AskAIService()


def get_ai_article_data_service() -> AIArticleDataService:
    return AIArticleDataService()


def get_article_analysis_service() -> ArticleAnalysisService:
    return ArticleAnalysisService()


def get_article_service() -> ArticleService:
    return ArticleService()


def get_dashboard_service() -> DashboardService:
    return DashboardService()


def get_github_repository_service() -> GitHubRepositoryService:
    return GitHubRepositoryService()


def get_docker_image_service() -> DockerImageService:
    return DockerImageService()


def get_it_trend_service() -> ITTrendService:
    return ITTrendService()


def get_news_site_service() -> NewsSiteService:
    return NewsSiteService()


def get_rss_feed_service() -> RSSFeedService:
    return RSSFeedService()


def get_settings_service() -> SettingsService:
    return SettingsService()
