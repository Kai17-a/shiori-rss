use reqwest::{
    Client, StatusCode, Url,
    dns::{Addrs, Name, Resolve, Resolving},
    header::{ACCEPT, ACCEPT_ENCODING, AUTHORIZATION, LOCATION, WWW_AUTHENTICATE},
};
use rusqlite::{Connection, params};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{collections::HashMap, error::Error, io, net::IpAddr, time::Duration};
use tokio::net::lookup_host;

use crate::{fetch_webhook_endpoints, webhook};

const MANIFEST_ACCEPT: &str = "application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json";
const MAX_REDIRECTS: usize = 5;

#[derive(Clone)]
struct PublicDnsResolver {
    allow_private_addresses: bool,
}

impl Resolve for PublicDnsResolver {
    fn resolve(&self, name: Name) -> Resolving {
        let host = name.as_str().to_owned();
        let allow_private_addresses = self.allow_private_addresses;
        Box::pin(async move {
            let addresses = lookup_host((host.as_str(), 0)).await?.collect::<Vec<_>>();
            if addresses.is_empty() {
                return Err(io::Error::other("registry host did not resolve").into());
            }
            if !allow_private_addresses
                && addresses
                    .iter()
                    .any(|address| is_disallowed_address(address.ip()))
            {
                return Err(io::Error::other(
                    "registry host resolves to a disallowed network address",
                )
                .into());
            }
            Ok(Box::new(addresses.into_iter()) as Addrs)
        })
    }
}

#[derive(Debug)]
struct DockerImage {
    id: u32,
    registry: String,
    repository: String,
    tag: String,
    display_name: String,
    latest_notified_digest: String,
    webhook_ids: Vec<u32>,
}

pub fn parse_reference(value: &str) -> Result<(String, String, String, String), String> {
    let display_name = value.trim();
    if display_name.is_empty()
        || display_name == "/"
        || display_name.contains("://")
        || display_name.chars().any(char::is_whitespace)
    {
        return Err("invalid Docker image reference".to_string());
    }
    let (first, rest) = display_name.split_once('/').unwrap_or((display_name, ""));
    let explicit_registry =
        !rest.is_empty() && (first.contains('.') || first.contains(':') || first == "localhost");
    let registry = if explicit_registry {
        first
    } else {
        "registry-1.docker.io"
    };
    let registry = match registry {
        "docker.io" | "index.docker.io" | "registry-1.docker.io" => "registry-1.docker.io",
        registry => registry,
    };
    let repository_with_tag = if explicit_registry {
        rest
    } else {
        display_name
    };
    let last_slash = repository_with_tag.rfind('/');
    let last_colon = repository_with_tag.rfind(':');
    let (mut repository, tag) = match (last_slash, last_colon) {
        (slash, Some(colon)) if slash.is_none_or(|slash| colon > slash) => (
            &repository_with_tag[..colon],
            &repository_with_tag[colon + 1..],
        ),
        _ => (repository_with_tag, "latest"),
    };
    let official_repository;
    if registry == "registry-1.docker.io" && !repository.contains('/') {
        official_repository = format!("library/{repository}");
        repository = &official_repository;
    }
    if registry.is_empty() || repository.is_empty() || tag.is_empty() {
        return Err("invalid Docker image reference".to_string());
    }
    Ok((
        registry.to_string(),
        repository.to_string(),
        tag.to_string(),
        display_name.to_string(),
    ))
}

fn fetch_images(conn: &Connection) -> Result<Vec<DockerImage>, rusqlite::Error> {
    let exists = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'docker_images')",
        [], |row| row.get::<_, bool>(0),
    )?;
    if !exists {
        return Ok(Vec::new());
    }
    let mut stmt = conn.prepare(
        "SELECT id, registry, repository, tag, display_name, latest_notified_digest FROM docker_images ORDER BY id",
    )?;
    let mut images = stmt
        .query_map([], |row| {
            Ok(DockerImage {
                id: row.get(0)?,
                registry: row.get(1)?,
                repository: row.get(2)?,
                tag: row.get(3)?,
                display_name: row.get(4)?,
                latest_notified_digest: row.get(5)?,
                webhook_ids: Vec::new(),
            })
        })?
        .collect::<Result<Vec<_>, _>>()?;
    for image in &mut images {
        let mut links = conn.prepare(
            "SELECT webhook_id FROM docker_image_webhooks WHERE image_id = ? ORDER BY webhook_id",
        )?;
        image.webhook_ids = links
            .query_map([image.id], |row| row.get(0))?
            .collect::<Result<Vec<_>, _>>()?;
    }
    Ok(images)
}

fn update_digest(
    conn: &Connection,
    image_id: u32,
    digest: &str,
    notified: bool,
) -> Result<(), rusqlite::Error> {
    conn.execute(
        r#"UPDATE docker_images SET latest_digest = ?,
            latest_notified_digest = CASE WHEN ? THEN ? ELSE latest_notified_digest END,
            fetched_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?"#,
        params![digest, notified, digest, image_id],
    )?;
    Ok(())
}

fn bearer_parameters(header: &str) -> Option<HashMap<String, String>> {
    let lower = header.to_ascii_lowercase();
    let start = lower.find("bearer ")? + "bearer ".len();
    let bytes = header.as_bytes();
    let mut pos = start;
    let mut values = HashMap::new();
    while pos < bytes.len() {
        while pos < bytes.len() && (bytes[pos].is_ascii_whitespace() || bytes[pos] == b',') {
            pos += 1;
        }
        let key_start = pos;
        while pos < bytes.len()
            && (bytes[pos].is_ascii_alphanumeric() || b"!#$%&'*+-.^_`|~".contains(&bytes[pos]))
        {
            pos += 1;
        }
        let key = &header[key_start..pos];
        while pos < bytes.len() && bytes[pos].is_ascii_whitespace() {
            pos += 1;
        }
        if key.is_empty() || pos >= bytes.len() || bytes[pos] != b'=' {
            break;
        }
        pos += 1;
        while pos < bytes.len() && bytes[pos].is_ascii_whitespace() {
            pos += 1;
        }
        let mut value = String::new();
        if pos < bytes.len() && bytes[pos] == b'"' {
            pos += 1;
            while pos < bytes.len() {
                if bytes[pos] == b'"' {
                    pos += 1;
                    break;
                }
                if bytes[pos] == b'\\' && pos + 1 < bytes.len() {
                    pos += 1;
                }
                value.push(bytes[pos] as char);
                pos += 1;
            }
        } else {
            while pos < bytes.len() && bytes[pos] != b',' && !bytes[pos].is_ascii_whitespace() {
                value.push(bytes[pos] as char);
                pos += 1;
            }
        }
        values.insert(key.to_ascii_lowercase(), value);
    }
    Some(values)
}

async fn get_with_redirects(
    client: &Client,
    url: Url,
    token: Option<&str>,
    allow_http: bool,
) -> Result<reqwest::Response, Box<dyn Error>> {
    let mut current = url;
    let mut send_token = token.is_some();
    for hop in 0..=MAX_REDIRECTS {
        // This fast-fail also covers literal IP URLs, which bypass DNS resolvers.
        // PublicDnsResolver is the enforcement point for hostname connections.
        if !allow_http {
            ensure_public_host(&current).await?;
        }
        let mut request = client
            .get(current.clone())
            .header(ACCEPT, MANIFEST_ACCEPT)
            .header(ACCEPT_ENCODING, "identity");
        if send_token && let Some(token) = token {
            request = request.header(AUTHORIZATION, format!("Bearer {token}"));
        }
        let response = request.send().await?;
        if !response.status().is_redirection() {
            return Ok(response);
        }
        if hop == MAX_REDIRECTS {
            return Err(io::Error::other("registry returned too many redirects").into());
        }
        let location = response
            .headers()
            .get(LOCATION)
            .ok_or_else(|| io::Error::other("registry redirect omitted Location"))?
            .to_str()?;
        let target = current.join(location)?;
        if target.scheme() != "https" && !(allow_http && target.scheme() == "http") {
            return Err(io::Error::other("registry redirected to an insecure URL").into());
        }
        if current.host_str() != target.host_str()
            || current.port_or_known_default() != target.port_or_known_default()
        {
            send_token = false;
        }
        current = target;
    }
    unreachable!()
}

fn is_disallowed_address(address: IpAddr) -> bool {
    match address {
        IpAddr::V4(ip) => {
            ip.is_loopback()
                || ip.is_private()
                || ip.is_link_local()
                || ip.is_multicast()
                || ip.is_unspecified()
                || ip.is_broadcast()
                || ip.is_documentation()
        }
        IpAddr::V6(ip) => {
            if let Some(ipv4) = ip.to_ipv4_mapped() {
                return is_disallowed_address(IpAddr::V4(ipv4));
            }
            let octets = ip.octets();
            let unique_local = octets[0] & 0xfe == 0xfc;
            let link_local = octets[0] == 0xfe && octets[1] & 0xc0 == 0x80;
            ip.is_loopback()
                || ip.is_multicast()
                || ip.is_unspecified()
                || unique_local
                || link_local
        }
    }
}

pub async fn ensure_public_host(url: &Url) -> Result<(), Box<dyn Error>> {
    let host = url
        .host_str()
        .ok_or_else(|| io::Error::other("registry URL has no host"))?;
    let port = url
        .port_or_known_default()
        .ok_or_else(|| io::Error::other("registry URL has no port"))?;
    let addresses = lookup_host((host, port)).await?;
    if addresses
        .map(|address| address.ip())
        .any(is_disallowed_address)
    {
        return Err(
            io::Error::other("registry host resolves to a disallowed network address").into(),
        );
    }
    Ok(())
}

pub async fn resolve_manifest_digest(
    client: &Client,
    manifest_url: Url,
    allow_http: bool,
) -> Result<String, Box<dyn Error>> {
    let mut response = get_with_redirects(client, manifest_url.clone(), None, allow_http).await?;
    if response.status() == StatusCode::UNAUTHORIZED {
        let challenge = response
            .headers()
            .get(WWW_AUTHENTICATE)
            .ok_or_else(|| io::Error::other("registry authentication challenge is missing"))?
            .to_str()?;
        let parameters = bearer_parameters(challenge).ok_or_else(|| {
            io::Error::other("registry Bearer authentication challenge is invalid")
        })?;
        let realm = parameters
            .get("realm")
            .ok_or_else(|| io::Error::other("registry authentication realm is missing"))?;
        let realm_url = Url::parse(realm)?;
        if realm_url.scheme() != "https" && !(allow_http && realm_url.scheme() == "http") {
            return Err(io::Error::other("registry authentication realm is not HTTPS").into());
        }
        let mut token_url = realm_url;
        {
            let mut query = token_url.query_pairs_mut();
            for key in ["service", "scope"] {
                if let Some(value) = parameters.get(key) {
                    query.append_pair(key, value);
                }
            }
        }
        if !allow_http {
            ensure_public_host(&token_url).await?;
        }
        let token_response = client.get(token_url).send().await?.error_for_status()?;
        let token_json: Value = token_response.json().await?;
        let token = token_json
            .get("token")
            .or_else(|| token_json.get("access_token"))
            .and_then(Value::as_str)
            .ok_or_else(|| io::Error::other("registry token response is invalid"))?;
        response = get_with_redirects(client, manifest_url, Some(token), allow_http).await?;
    }
    if response.status() == StatusCode::TOO_MANY_REQUESTS {
        return Err(io::Error::other("registry rate limit exceeded").into());
    }
    let response = response.error_for_status()?;
    let advertised = response
        .headers()
        .get("docker-content-digest")
        .map(|value| value.to_str().map(str::to_owned))
        .transpose()?;
    let body = response.bytes().await?;
    let manifest: Value = serde_json::from_slice(&body)?;
    if !manifest.is_object() {
        return Err(io::Error::other("registry returned an invalid manifest").into());
    }
    let computed = format!("sha256:{:x}", Sha256::digest(&body));
    if let Some(advertised) = advertised {
        if advertised != computed {
            return Err(io::Error::other("registry manifest digest verification failed").into());
        }
        Ok(advertised)
    } else {
        Ok(computed)
    }
}

pub async fn run_docker_image_batch(conn: &Connection) -> Result<(), Box<dyn Error>> {
    run_docker_image_batch_inner(conn, None).await
}

pub async fn run_docker_image_batch_with_base(
    conn: &Connection,
    base_url: &str,
) -> Result<(), Box<dyn Error>> {
    run_docker_image_batch_inner(conn, Some(base_url)).await
}

async fn run_docker_image_batch_inner(
    conn: &Connection,
    base_url: Option<&str>,
) -> Result<(), Box<dyn Error>> {
    let images = fetch_images(conn)?;
    if images.is_empty() {
        return Ok(());
    }
    let endpoints = fetch_webhook_endpoints(conn)?;
    let client = Client::builder()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(Duration::from_secs(10))
        .user_agent("shiori-feed")
        .dns_resolver(PublicDnsResolver {
            allow_private_addresses: base_url.is_some(),
        })
        .build()?;
    for image in images {
        let base = base_url
            .map(str::to_owned)
            .unwrap_or_else(|| format!("https://{}", image.registry));
        let allow_http = base.starts_with("http://");
        let url = match Url::parse(&format!(
            "{}/v2/{}/manifests/{}",
            base.trim_end_matches('/'),
            image.repository,
            image.tag
        )) {
            Ok(url) => url,
            Err(error) => {
                eprintln!("Skipping Docker image {}: {}", image.display_name, error);
                continue;
            }
        };
        let digest = match resolve_manifest_digest(&client, url, allow_http).await {
            Ok(digest) => digest,
            Err(error) => {
                eprintln!("Skipping Docker image {}: {}", image.display_name, error);
                continue;
            }
        };
        let changed = digest != image.latest_notified_digest;
        let mut delivered = false;
        if changed {
            for endpoint in endpoints
                .iter()
                .filter(|endpoint| image.webhook_ids.contains(&endpoint.id))
            {
                match webhook::send_docker_image_update_webhook(
                    &endpoint.url,
                    &image.display_name,
                    &image.registry,
                    &image.repository,
                    &image.tag,
                    &image.latest_notified_digest,
                    &digest,
                )
                .await
                {
                    Ok(()) => delivered = true,
                    Err(error) => eprintln!("{error}"),
                }
            }
        }
        update_digest(conn, image.id, &digest, delivered)?;
    }
    Ok(())
}
