from datetime import date, datetime
from typing import ClassVar, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field as PydField,
    field_validator,
    model_validator,
)
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlmodel import Field, SQLModel


class RSSFeed(SQLModel, table=True):
    __tablename__: ClassVar[str] = "rss_feeds"
    __table_args__ = (
        Index("idx_rss_feeds_url_unique", "url", unique=True),
        Index("idx_rss_feeds_title_id", "title", "id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(sa_column=Column(String, nullable=False))
    title: str = Field(sa_column=Column(String, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text))
    notify_webhook_enabled: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text("1")),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime, nullable=False, server_default=text("(datetime('now'))")
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime, nullable=False, server_default=text("(datetime('now'))")
        )
    )


class RSSFeedArticle(SQLModel, table=True):
    __tablename__: ClassVar[str] = "rss_feed_articles"
    __table_args__ = (
        Index("idx_rss_feed_articles_feed_url_unique", "feed_id", "url", unique=True),
        Index("idx_rss_feed_articles_feed_published_id", "feed_id", "published", "id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    feed_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("rss_feeds.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    url: str = Field(sa_column=Column(String, nullable=False))
    title: str | None = Field(default=None, sa_column=Column(String))
    summary: str | None = Field(default=None, sa_column=Column(Text))
    published: datetime | None = Field(default=None, sa_column=Column(DateTime))
    webhook_notified: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("0")),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime, nullable=False, server_default=text("(datetime('now'))")
        )
    )


class NewsSite(SQLModel, table=True):
    __tablename__: ClassVar[str] = "news_sites"
    __table_args__ = (
        Index("idx_news_sites_url_unique", "url", unique=True),
        Index("idx_news_sites_title_id", "title", "id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(sa_column=Column(String, nullable=False))
    title: str = Field(sa_column=Column(String, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text))
    scrape_config: str = Field(sa_column=Column(Text, nullable=False))
    notify_webhook_enabled: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text("1")),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime, nullable=False, server_default=text("(datetime('now'))")
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime, nullable=False, server_default=text("(datetime('now'))")
        )
    )


class NewsSiteArticle(SQLModel, table=True):
    __tablename__: ClassVar[str] = "news_site_articles"
    __table_args__ = (
        Index("idx_news_site_articles_site_url_unique", "site_id", "url", unique=True),
        Index("idx_news_site_articles_site_published_id", "site_id", "published", "id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    site_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("news_sites.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    url: str = Field(sa_column=Column(String, nullable=False))
    title: str | None = Field(default=None, sa_column=Column(String))
    summary: str | None = Field(default=None, sa_column=Column(Text))
    published: datetime | None = Field(default=None, sa_column=Column(DateTime))
    webhook_notified: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("0")),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime, nullable=False, server_default=text("(datetime('now'))")
        )
    )


class AppSetting(SQLModel, table=True):
    __tablename__: ClassVar[str] = "app_settings"

    key: str = Field(primary_key=True)
    value: str = Field(sa_column=Column(Text, nullable=False))
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime, nullable=False, server_default=text("(datetime('now'))")
        )
    )


class WebhookEndpoint(SQLModel, table=True):
    __tablename__: ClassVar[str] = "webhook_endpoints"
    __table_args__ = (Index("idx_webhook_endpoints_url_unique", "url", unique=True),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(
        default="",
        sa_column=Column(String, nullable=False, server_default=text("''")),
    )
    url: str = Field(sa_column=Column(String, nullable=False))
    enabled: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text("1")),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime, nullable=False, server_default=text("(datetime('now'))")
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime, nullable=False, server_default=text("(datetime('now'))")
        )
    )


class RSSFeedCreate(BaseModel):
    url: AnyHttpUrl
    title: str = PydField(min_length=1)
    description: str | None = None
    notify_webhook_enabled: bool = True
    webhook_ids: list[int] | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        return value

    @field_validator("webhook_ids")
    @classmethod
    def validate_webhook_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("webhook_ids must not contain duplicates")
        return value


class RSSFeedUpdate(BaseModel):
    url: AnyHttpUrl | None = None
    title: str | None = PydField(default=None, min_length=1)
    description: str | None = None
    notify_webhook_enabled: bool | None = None
    webhook_ids: list[int] | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        return value

    @field_validator("webhook_ids")
    @classmethod
    def validate_webhook_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("webhook_ids must not contain duplicates")
        return value

    @model_validator(mode="after")
    def reject_null_non_nullable_fields(self) -> "RSSFeedUpdate":
        for field_name in ("url", "title", "notify_webhook_enabled", "webhook_ids"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class RSSFeedResponse(BaseModel):
    id: int
    url: str
    title: str
    description: str | None
    notify_webhook_enabled: bool
    webhook_ids: list[int]
    created_at: datetime
    updated_at: datetime


class RSSFeedArticleResponse(BaseModel):
    id: int
    feed_id: int
    url: str
    title: str | None = None
    summary: str | None = None
    published: datetime | None = None
    webhook_notified: bool
    created_at: datetime


class RSSFeedArticleListResponse(BaseModel):
    items: list[RSSFeedArticleResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class RSSFeedListResponse(BaseModel):
    items: list[RSSFeedResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class RSSFeedExecuteResponse(BaseModel):
    feed_id: int
    title: str
    delivered: bool
    delivered_count: int
    message: str | None = None


def _reject_duplicate_ids(value: list[int] | None) -> list[int] | None:
    if value is not None and len(value) != len(set(value)):
        raise ValueError("IDs must not contain duplicates")
    return value


class NewsSiteCreate(BaseModel):
    url: AnyHttpUrl
    title: str | None = PydField(default=None, min_length=1)
    description: str | None = None
    webhook_ids: list[int] | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("webhook_ids")
    @classmethod
    def validate_webhook_ids(cls, value: list[int] | None) -> list[int] | None:
        return _reject_duplicate_ids(value)


class NewsSiteUpdate(BaseModel):
    url: AnyHttpUrl | None = None
    title: str | None = PydField(default=None, min_length=1)
    description: str | None = None
    notify_webhook_enabled: bool | None = None
    webhook_ids: list[int] | None = None
    reanalyze: bool = False

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        return value

    @field_validator("webhook_ids")
    @classmethod
    def validate_webhook_ids(cls, value: list[int] | None) -> list[int] | None:
        return _reject_duplicate_ids(value)

    @model_validator(mode="after")
    def reject_null_non_nullable_fields(self) -> "NewsSiteUpdate":
        for field_name in ("url", "title", "notify_webhook_enabled", "webhook_ids"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class NewsSiteResponse(BaseModel):
    id: int
    url: str
    title: str
    description: str | None
    notify_webhook_enabled: bool
    webhook_ids: list[int]
    created_at: datetime
    updated_at: datetime


class NewsSiteListResponse(BaseModel):
    items: list[NewsSiteResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class NewsSiteArticleResponse(BaseModel):
    id: int
    site_id: int
    url: str
    title: str | None
    summary: str | None = None
    published: datetime | None
    webhook_notified: bool = False
    created_at: datetime


class NewsSiteArticleListResponse(BaseModel):
    items: list[NewsSiteArticleResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class NewsSiteExecuteResponse(BaseModel):
    site_id: int
    title: str
    delivered: bool
    delivered_count: int
    message: str | None = None


class SettingsWebhookCreate(BaseModel):
    name: str = PydField(min_length=1)
    webhook_url: AnyHttpUrl

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        return value


class SettingsWebhookResponse(BaseModel):
    id: int
    name: str
    webhook_url: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class SettingsWebhookUpdate(BaseModel):
    enabled: bool


class SettingsWebhookListResponse(BaseModel):
    items: list[SettingsWebhookResponse]


class SettingsWebhookPingRequest(BaseModel):
    webhook_url: str


class SettingsWebhookPingResponse(BaseModel):
    pong: bool


class SettingsRssExecutionResponse(BaseModel):
    enabled: bool


class SettingsRssExecutionUpdate(BaseModel):
    enabled: bool


class SettingsRssWebhookNotificationResponse(BaseModel):
    enabled: bool


class SettingsRssWebhookNotificationUpdate(BaseModel):
    enabled: bool


class SettingsWebhookSummaryResponse(BaseModel):
    enabled: bool


class SettingsWebhookSummaryUpdate(BaseModel):
    enabled: bool


class LLMSettingsUpdate(BaseModel):
    provider: Literal["vllm", "ollama", "openai"]
    base_url: AnyHttpUrl
    api_key: str | None = None
    clear_api_key: bool = False
    model: str = PydField(min_length=1)

    @field_validator("model")
    @classmethod
    def normalize_model(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Model cannot be empty")
        return value

    @field_validator("api_key")
    @classmethod
    def normalize_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip() or None


class LLMSettingsResponse(BaseModel):
    provider: str
    base_url: str
    api_key_configured: bool
    model: str


class LLMSettingsTestRequest(BaseModel):
    provider: Literal["vllm", "ollama", "openai"] | None = None
    base_url: AnyHttpUrl | None = None
    api_key: str | None = None
    clear_api_key: bool = False
    model: str | None = None


class LLMSettingsTestResponse(BaseModel):
    ok: bool
    reply: str | None = None


class ErrorResponse(BaseModel):
    detail: str


class DashboardSummary(BaseModel):
    rss_feed_count: int
    custom_feed_count: int
    today_article_count: int
    pending_notification_count: int


class DashboardArticle(BaseModel):
    source_type: Literal["rss", "custom"]
    source_id: int
    source_title: str
    url: str
    title: str | None
    summary: str | None
    published: datetime | None
    created_at: datetime
    webhook_notified: bool


class DashboardResponse(BaseModel):
    date: date
    summary: DashboardSummary
    articles: list[DashboardArticle]
