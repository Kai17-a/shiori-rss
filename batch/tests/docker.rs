use reqwest::{Client, Url};
use rusqlite::Connection;
use sha2::{Digest, Sha256};
use shiori_feed_batch::docker::{
    ensure_public_host, parse_reference, resolve_manifest_digest, run_docker_image_batch_with_base,
};
use wiremock::{
    Mock, MockServer, ResponseTemplate,
    matchers::{header, method, path},
};

fn digest(body: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(body))
}

fn database(webhook_server: &MockServer) -> Connection {
    let conn = Connection::open_in_memory().expect("open database");
    conn.execute_batch(r#"
        CREATE TABLE docker_images (
            id INTEGER PRIMARY KEY, registry TEXT NOT NULL, repository TEXT NOT NULL, tag TEXT NOT NULL,
            display_name TEXT NOT NULL, latest_digest TEXT NOT NULL, latest_notified_digest TEXT NOT NULL,
            fetched_at TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE webhook_endpoints (id INTEGER PRIMARY KEY, url TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE docker_image_webhooks (image_id INTEGER NOT NULL, webhook_id INTEGER NOT NULL, PRIMARY KEY (image_id, webhook_id));
        CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    "#).expect("create schema");
    conn.execute("INSERT INTO docker_images VALUES (1, 'registry.example', 'owner/name', 'latest', 'registry.example/owner/name:latest', 'sha256:old', 'sha256:old', '', '', '')", []).expect("insert image");
    conn.execute(
        "INSERT INTO webhook_endpoints VALUES (1, ?, 1)",
        [format!("{}/hook", webhook_server.uri())],
    )
    .expect("insert webhook");
    conn.execute("INSERT INTO docker_image_webhooks VALUES (1, 1)", [])
        .expect("link webhook");
    conn
}

fn client() -> Client {
    Client::builder()
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .expect("client")
}

#[test]
fn parses_docker_references() {
    for (reference, expected) in [
        (
            "ghcr.io/owner/name:stable",
            ("ghcr.io", "owner/name", "stable"),
        ),
        ("localhost:5000/name:tag", ("localhost:5000", "name", "tag")),
        ("nginx", ("registry-1.docker.io", "library/nginx", "latest")),
        (
            "docker.io/nginx",
            ("registry-1.docker.io", "library/nginx", "latest"),
        ),
        (
            "index.docker.io/nginx",
            ("registry-1.docker.io", "library/nginx", "latest"),
        ),
        (
            "registry-1.docker.io/nginx:1.27",
            ("registry-1.docker.io", "library/nginx", "1.27"),
        ),
        (
            "owner/name",
            ("registry-1.docker.io", "owner/name", "latest"),
        ),
    ] {
        let parsed = parse_reference(reference).unwrap();
        assert_eq!(
            (parsed.0.as_str(), parsed.1.as_str(), parsed.2.as_str()),
            expected
        );
    }
}

#[tokio::test]
async fn rejects_loopback_registry_before_http_request() {
    let error = resolve_manifest_digest(
        &client(),
        Url::parse("https://127.0.0.1:12345/manifest").unwrap(),
        false,
    )
    .await
    .unwrap_err();
    assert_eq!(
        error.to_string(),
        "registry host resolves to a disallowed network address"
    );
}

#[tokio::test]
async fn accepts_public_registry_address() {
    ensure_public_host(&Url::parse("https://8.8.8.8/manifest").unwrap())
        .await
        .unwrap();
}

#[tokio::test]
async fn resolves_anonymous_manifest_and_falls_back_without_header() {
    let server = MockServer::start().await;
    let body = br#"{"schemaVersion":2}"#;
    Mock::given(method("GET"))
        .and(path("/manifest"))
        .respond_with(ResponseTemplate::new(200).set_body_bytes(body))
        .mount(&server)
        .await;
    let actual = resolve_manifest_digest(
        &client(),
        Url::parse(&format!("{}/manifest", server.uri())).unwrap(),
        true,
    )
    .await
    .unwrap();
    assert_eq!(actual, digest(body));
}

#[tokio::test]
async fn authenticates_with_bearer_token() {
    let server = MockServer::start().await;
    let body = br#"{"schemaVersion":2}"#;
    Mock::given(method("GET"))
        .and(path("/token"))
        .respond_with(
            ResponseTemplate::new(200).set_body_json(serde_json::json!({"access_token":"secret"})),
        )
        .mount(&server)
        .await;
    Mock::given(method("GET"))
        .and(path("/manifest"))
        .and(header("authorization", "Bearer secret"))
        .respond_with(
            ResponseTemplate::new(200)
                .insert_header("Docker-Content-Digest", digest(body))
                .set_body_bytes(body),
        )
        .with_priority(1)
        .mount(&server)
        .await;
    Mock::given(method("GET")).and(path("/manifest"))
        .respond_with(ResponseTemplate::new(401).insert_header("WWW-Authenticate", format!("Basic realm=\"legacy\", Bearer realm=\"{}/token\",service=\"registry\",scope=\"repository:owner/name:pull\"", server.uri()))).mount(&server).await;
    let actual = resolve_manifest_digest(
        &client(),
        Url::parse(&format!("{}/manifest", server.uri())).unwrap(),
        true,
    )
    .await
    .unwrap();
    assert_eq!(actual, digest(body));
}

#[tokio::test]
async fn cross_host_redirect_does_not_forward_authorization() {
    let registry = MockServer::start().await;
    let storage = MockServer::start().await;
    let body = br#"{"schemaVersion":2}"#;
    Mock::given(method("GET"))
        .and(path("/token"))
        .respond_with(
            ResponseTemplate::new(200).set_body_json(serde_json::json!({"token":"secret"})),
        )
        .mount(&registry)
        .await;
    Mock::given(method("GET"))
        .and(path("/manifest"))
        .and(header("authorization", "Bearer secret"))
        .respond_with(
            ResponseTemplate::new(307).insert_header("Location", format!("{}/blob", storage.uri())),
        )
        .with_priority(1)
        .mount(&registry)
        .await;
    Mock::given(method("GET"))
        .and(path("/manifest"))
        .respond_with(ResponseTemplate::new(401).insert_header(
            "WWW-Authenticate",
            format!("Bearer realm=\"{}/token\"", registry.uri()),
        ))
        .mount(&registry)
        .await;
    Mock::given(method("GET"))
        .and(path("/blob"))
        .respond_with(
            ResponseTemplate::new(200)
                .insert_header("Docker-Content-Digest", digest(body))
                .set_body_bytes(body),
        )
        .mount(&storage)
        .await;
    resolve_manifest_digest(
        &client(),
        Url::parse(&format!("{}/manifest", registry.uri())).unwrap(),
        true,
    )
    .await
    .unwrap();
    let requests = storage.received_requests().await.unwrap();
    assert_eq!(requests.len(), 1);
    assert!(!requests[0].headers.contains_key("authorization"));
}

#[tokio::test]
async fn rejects_mismatched_digest_malformed_manifest_and_rate_limit() {
    for response in [
        ResponseTemplate::new(200)
            .insert_header("Docker-Content-Digest", "sha256:wrong")
            .set_body_string("{}"),
        ResponseTemplate::new(200).set_body_string("not-json"),
        ResponseTemplate::new(429),
    ] {
        let server = MockServer::start().await;
        Mock::given(method("GET"))
            .and(path("/manifest"))
            .respond_with(response)
            .mount(&server)
            .await;
        assert!(
            resolve_manifest_digest(
                &client(),
                Url::parse(&format!("{}/manifest", server.uri())).unwrap(),
                true
            )
            .await
            .is_err()
        );
    }
}

#[tokio::test]
async fn notifies_once_after_successful_delivery() {
    let server = MockServer::start().await;
    let conn = database(&server);
    let body = br#"{"schemaVersion":2}"#;
    Mock::given(method("GET"))
        .and(path("/v2/owner/name/manifests/latest"))
        .respond_with(
            ResponseTemplate::new(200)
                .insert_header("Docker-Content-Digest", digest(body))
                .set_body_bytes(body),
        )
        .mount(&server)
        .await;
    Mock::given(method("POST"))
        .and(path("/hook"))
        .respond_with(ResponseTemplate::new(204))
        .mount(&server)
        .await;
    run_docker_image_batch_with_base(&conn, &server.uri())
        .await
        .unwrap();
    run_docker_image_batch_with_base(&conn, &server.uri())
        .await
        .unwrap();
    let notified: String = conn
        .query_row(
            "SELECT latest_notified_digest FROM docker_images",
            [],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(notified, digest(body));
    let requests = server.received_requests().await.unwrap();
    assert_eq!(
        requests
            .iter()
            .filter(|request| request.method.as_str() == "POST")
            .count(),
        1
    );
}

#[tokio::test]
async fn failed_delivery_is_retried_and_rate_limit_skips_update() {
    let server = MockServer::start().await;
    let conn = database(&server);
    let body = br#"{"schemaVersion":2}"#;
    Mock::given(method("GET"))
        .and(path("/v2/owner/name/manifests/latest"))
        .respond_with(ResponseTemplate::new(200).set_body_bytes(body))
        .up_to_n_times(2)
        .mount(&server)
        .await;
    Mock::given(method("POST"))
        .and(path("/hook"))
        .respond_with(ResponseTemplate::new(400))
        .mount(&server)
        .await;
    run_docker_image_batch_with_base(&conn, &server.uri())
        .await
        .unwrap();
    run_docker_image_batch_with_base(&conn, &server.uri())
        .await
        .unwrap();
    let notified: String = conn
        .query_row(
            "SELECT latest_notified_digest FROM docker_images",
            [],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(notified, "sha256:old");
    let requests = server.received_requests().await.unwrap();
    assert_eq!(
        requests
            .iter()
            .filter(|request| request.method.as_str() == "POST")
            .count(),
        2
    );

    let limited = MockServer::start().await;
    Mock::given(method("GET"))
        .respond_with(ResponseTemplate::new(429))
        .mount(&limited)
        .await;
    run_docker_image_batch_with_base(&conn, &limited.uri())
        .await
        .unwrap();
    let latest: String = conn
        .query_row("SELECT latest_digest FROM docker_images", [], |row| {
            row.get(0)
        })
        .unwrap();
    assert_eq!(latest, digest(body));
}
