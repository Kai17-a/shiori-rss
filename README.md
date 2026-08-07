# Shiori Keeper

## Overview

Shiori Keeper is a very simple web app for listing, finding, and organizing bookmarks collected in your browser.  
It is designed to make it easier to revisit links later.

_Shiori(栞)_ means “bookmark” in Japanese.

> [!WARNING]
> This project is still in alpha, so destructive changes to the database may happen.
> If anything goes wrong, please report it with the `bug` label on the issue tracker.

## How to Install

If you use the published image, pull it from GitHub Container Registry and run it locally:

```bash
docker pull ghcr.io/kai17-a/shiori-keeper:latest
docker run --rm -p 3000:3000 -p 8000:8000 \
  -e DATABASE_URL=/data/data.db \
  -v "$(pwd)/data:/data" \
  ghcr.io/kai17-a/shiori-keeper:latest
```

After startup, open the frontend at `http://127.0.0.1:3000` and the API at `http://127.0.0.1:8000`.

If you prefer `docker compose`, use a setup like this:

```yaml
services:
  shiori-keeper:
    container_name: shiori-keeper
    image: ghcr.io/kai17-a/shiori-keeper:latest
    environment:
      DATABASE_URL: /data/data.db
      RSS_CRON_SCHEDULE: "0 * * * *"
      TZ: UTC
    ports:
      - "3000:3000"
      - "8000:8000"
    volumes:
      - ./data:/data
```

The scheduled RSS/custom-news batch runs hourly by default. Override
`RSS_CRON_SCHEDULE` with a cron expression and set `TZ` when the schedule must
follow a specific timezone. For example, this runs hourly from 06:00 through
22:00 in Japan and does not run from 23:00 through 05:59:

```yaml
environment:
  RSS_CRON_SCHEDULE: "0 6-22 * * *"
  TZ: Asia/Tokyo
```

Changing either value requires recreating the container.

## What You Can Do

### Manage bookmarks in one place

- Register bookmarks with a URL, title, and description
- Edit or delete bookmarks later
- Mark important bookmarks as favorites so they are easier to find

### Organize with folders

- Group bookmarks into folders
- Create, rename, and delete folders
- When a folder is deleted, the bookmarks inside remain and are simply unassigned from that folder

### Classify with tags

- Attach multiple tags to a single bookmark
- Create, rename, and delete tags
- When a tag is deleted, its bookmark links are removed automatically

### Find things quickly

- Search bookmarks by keyword
- Filter by folder or tag
- Browse results with pagination

### Keep RSS feeds separately

- Register RSS or Atom feed URLs
- List, edit, and delete RSS feeds
- Optionally choose per feed which registered webhooks receive its notifications (unselected feeds notify all webhooks)
- Run a feed manually and connect the result to external notifications
- Run RSS feeds periodically with the batch process and send new articles to Discord, Slack, or Microsoft Teams webhooks
- Register news-list pages that do not publish RSS; an LLM analyzes and tests reusable CSS selectors before saving
- Run custom news sites manually or in the same scheduled batch flow, with duplicate delivery prevention and per-site webhook selection

### Configure custom-site analysis

- Configure Ollama, vLLM, or an OpenAI-compatible chat-completions endpoint
- Test the endpoint, model, and credentials before settings are saved
- Custom news sites cannot be registered until working LLM settings exist
- Custom-site registration errors identify the failed stage and include a reference ID for matching server logs

### Configure notifications

- Register multiple Discord, Slack, or Microsoft Teams webhooks with identifying names
- Test whether each webhook endpoint is reachable
- Use the registered webhooks as the notification targets for RSS execution
- Choose globally whether RSS and custom-news webhook notifications include article summaries

### See the overall status at a glance

- View counts for bookmarks, folders, tags, favorites, RSS feeds, and custom news sites on the dashboard
- See recent bookmarks and saved folders or tags

### Switch the appearance

- Choose between system, light, and dark themes

## Main Screens

- `Dashboard`: View overall counts and recent bookmarks
- `Bookmarks`: List, search, add, edit, and delete bookmarks
- `Favorites`: View only bookmarked items marked as favorites
- `Folders`: Create, edit, and delete folders
- `Tags`: Create, edit, and delete tags
- `RSS`: Register, edit, delete, and execute RSS feeds and custom news sites, including periodic batch runs
- `Settings`: Configure the theme, notification webhooks, and LLM connection

## Where Data Is Stored

- Data is stored in a SQLite database
- Your saved information remains even after you close the browser

## Intended Use

- A bookmark organizer for individuals or small teams
- Helps turn an ever-growing list of saved links into something easier to browse with folders and tags
- Also keeps RSS feeds and non-RSS news sources in the same app

## Browser Extension

- [chrome web store](https://chrome.google.com/webstore/detail/dfjcocpbcdlleogghldbdcapomilohia)

## Notes

- Invalid URL formats cannot be registered
- Duplicate bookmark URLs, tag names, RSS feed URLs, custom news-site URLs, and webhook URLs are not allowed
- The webhook system supports Discord, Slack, and Microsoft Teams incoming webhooks

## Development Notes

- Workflow and commit rules are in [DEVELOPMENT.md](./DEVELOPMENT.md)
- Changelogs stay focused on user-facing changes

## Screenshots

### Light

![Dashboard light](docs/app-images/dashboard-light.png)
![Bookmarks light](docs/app-images/bookmarks-light.png)
![Favorites light](docs/app-images/favorites-light.png)
![Folders light](docs/app-images/folders-light.png)
![Tags light](docs/app-images/tags-light.png)
![RSS light](docs/app-images/rss-light.png)
![Settings light](docs/app-images/settings-light.png)

### Dark

![Dashboard dark](docs/app-images/dashboard-dark.png)
![Bookmarks dark](docs/app-images/bookmarks-dark.png)
![Favorites dark](docs/app-images/favorites-dark.png)
![Folders dark](docs/app-images/folders-dark.png)
![Tags dark](docs/app-images/tags-dark.png)
![RSS dark](docs/app-images/rss-dark.png)
![Settings dark](docs/app-images/settings-dark.png)
