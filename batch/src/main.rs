use rusqlite::Connection;
use shiori_feed_batch::{database_path, run_batch};
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let conn = Connection::open(database_path())?;
    run_batch(&conn).await
}
