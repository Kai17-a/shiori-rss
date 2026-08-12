use reqwest::header::{ACCEPT, AUTHORIZATION, HeaderMap, HeaderValue, USER_AGENT};
use rusqlite::{Connection, params};
use serde::Deserialize;
use std::error::Error;
use std::time::Duration;

use crate::{fetch_webhook_endpoints, webhook};

#[derive(Debug)]
struct Repository {
    id: u32,
    owner: String,
    name: String,
    repository_url: String,
    latest_notified_release_tag: Option<String>,
    webhook_ids: Vec<u32>,
}

#[derive(Debug, Deserialize)]
struct Release {
    name: Option<String>,
    tag_name: String,
    html_url: String,
    body: Option<String>,
    published_at: String,
}

fn fetch_repositories(conn: &Connection) -> Result<Vec<Repository>, rusqlite::Error> {
    let exists = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'github_repositories')",
        [], |row| row.get::<_, bool>(0),
    )?;
    if !exists {
        return Ok(Vec::new());
    }
    let mut stmt = conn.prepare(
        "SELECT id, owner, repository, repository_url, latest_notified_release_tag FROM github_repositories ORDER BY id",
    )?;
    let mut repositories: Vec<Repository> = stmt
        .query_map([], |row| {
            Ok(Repository {
                id: row.get(0)?,
                owner: row.get(1)?,
                name: row.get(2)?,
                repository_url: row.get(3)?,
                latest_notified_release_tag: row.get(4)?,
                webhook_ids: Vec::new(),
            })
        })?
        .collect::<Result<Vec<_>, _>>()?;
    for repository in &mut repositories {
        let mut link_stmt = conn.prepare("SELECT webhook_id FROM github_repository_webhooks WHERE repository_id = ? ORDER BY webhook_id")?;
        repository.webhook_ids = link_stmt
            .query_map([repository.id], |row| row.get(0))?
            .collect::<Result<Vec<_>, _>>()?;
    }
    Ok(repositories)
}

fn update_release(
    conn: &Connection,
    repository_id: u32,
    release: &Release,
    notified: bool,
) -> Result<(), rusqlite::Error> {
    conn.execute(
        r#"
        UPDATE github_repositories SET latest_release_name = ?, latest_release_tag = ?,
            latest_release_url = ?, latest_release_body = ?, latest_release_published_at = ?,
            latest_notified_release_tag = CASE WHEN ? THEN ? ELSE latest_notified_release_tag END,
            fetched_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?
        "#,
        params![
            release.name.as_deref().unwrap_or(&release.tag_name),
            release.tag_name,
            release.html_url,
            release.body,
            release.published_at,
            notified,
            release.tag_name,
            repository_id
        ],
    )?;
    Ok(())
}

pub async fn run_github_release_batch(conn: &Connection) -> Result<(), Box<dyn Error>> {
    let api_base = std::env::var("GITHUB_API_BASE_URL")
        .unwrap_or_else(|_| "https://api.github.com".to_string());
    run_github_release_batch_with_base(conn, &api_base).await
}

pub async fn run_github_release_batch_with_base(
    conn: &Connection,
    api_base: &str,
) -> Result<(), Box<dyn Error>> {
    let repositories = fetch_repositories(conn)?;
    if repositories.is_empty() {
        return Ok(());
    }
    let endpoints = fetch_webhook_endpoints(conn)?;
    let mut headers = HeaderMap::new();
    headers.insert(
        ACCEPT,
        HeaderValue::from_static("application/vnd.github+json"),
    );
    headers.insert(USER_AGENT, HeaderValue::from_static("shiori-feed"));
    headers.insert(
        "X-GitHub-Api-Version",
        HeaderValue::from_static("2022-11-28"),
    );
    if let Ok(token) = std::env::var("GITHUB_TOKEN") {
        headers.insert(
            AUTHORIZATION,
            HeaderValue::from_str(&format!("Bearer {token}"))?,
        );
    }
    let client = reqwest::Client::builder()
        .default_headers(headers)
        .timeout(Duration::from_secs(10))
        .build()?;

    for repository in repositories {
        let response = match client
            .get(format!(
                "{api_base}/repos/{}/{}/releases/latest",
                repository.owner, repository.name
            ))
            .send()
            .await
        {
            Ok(response) if response.status().is_success() => response,
            Ok(response) => {
                eprintln!(
                    "Skipping GitHub repository {}: API returned {}",
                    repository.repository_url,
                    response.status()
                );
                continue;
            }
            Err(error) => {
                eprintln!(
                    "Skipping GitHub repository {}: {}",
                    repository.repository_url, error
                );
                continue;
            }
        };
        let release: Release = match response.json().await {
            Ok(release) => release,
            Err(error) => {
                eprintln!(
                    "Skipping GitHub repository {}: invalid release response: {}",
                    repository.repository_url, error
                );
                continue;
            }
        };
        let is_new = repository.latest_notified_release_tag.as_deref() != Some(&release.tag_name);
        let mut delivered = false;
        if is_new {
            for endpoint in endpoints
                .iter()
                .filter(|endpoint| repository.webhook_ids.contains(&endpoint.id))
            {
                match webhook::send_github_release_webhook(
                    &endpoint.url,
                    &format!("{}/{}", repository.owner, repository.name),
                    &repository.repository_url,
                    release.name.as_deref().unwrap_or(&release.tag_name),
                    &release.tag_name,
                    &release.html_url,
                    release.body.as_deref().unwrap_or(""),
                )
                .await
                {
                    Ok(()) => delivered = true,
                    Err(error) => eprintln!("{}", error),
                }
            }
        }
        update_release(conn, repository.id, &release, delivered)?;
    }
    Ok(())
}
