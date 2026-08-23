use rusqlite::Connection;
use shiori_feed_batch::{
    database_path, ensure_vec_extension_registered, run_article_analysis_manual, run_batch,
    run_single_article_analysis,
};
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    ensure_vec_extension_registered();
    let conn = Connection::open(database_path())?;
    let args: Vec<String> = std::env::args().collect();
    if let Some(spec) = args
        .iter()
        .find_map(|argument| argument.strip_prefix("--reanalyze-article="))
    {
        let (source_type, article_id) = spec
            .split_once(':')
            .ok_or("invalid --reanalyze-article value, expected <source_type>:<article_id>")?;
        let article_id: i64 = article_id.parse()?;
        let report = run_single_article_analysis(&conn, source_type, article_id).await?;
        println!("{}", serde_json::to_string(&report)?);
        return Ok(());
    }
    if args
        .iter()
        .any(|argument| argument == "--article-analysis-only")
    {
        let report = run_article_analysis_manual(&conn).await?;
        println!("{}", serde_json::to_string(&report)?);
        return Ok(());
    }
    run_batch(&conn).await
}
