use rusqlite::Connection;
use shiori_feed_batch::{database_path, run_article_analysis_manual, run_batch};
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let conn = Connection::open(database_path())?;
    if std::env::args().any(|argument| argument == "--article-analysis-only") {
        let report = run_article_analysis_manual(&conn).await?;
        println!("{}", serde_json::to_string(&report)?);
        return Ok(());
    }
    run_batch(&conn).await
}
