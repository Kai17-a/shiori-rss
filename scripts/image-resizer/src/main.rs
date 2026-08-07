use image::imageops::FilterType;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

const SIZES: [u32; 6] = [128, 16, 32, 48, 64, 96];

fn main() {
    if let Err(err) = run() {
        eprintln!("Error: {err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = env::args();
    let program_name = args.next().unwrap_or_else(|| "image-resizer".to_string());

    let input_path = match args.next() {
        Some(path) => path,
        None => {
            eprintln!("Usage: {program_name} <input_image>");
            std::process::exit(1);
        }
    };

    if args.next().is_some() {
        eprintln!("Usage: {program_name} <input_image>");
        std::process::exit(1);
    }

    let input_path = Path::new(&input_path);
    if !input_path.exists() {
        return Err(format!("File not found: {}", input_path.display()).into());
    }

    // distディレクトリ準備
    let dist_dir = PathBuf::from("dist");
    fs::create_dir_all(&dist_dir)?;

    let img = image::open(input_path)?;
    let width = img.width();
    let height = img.height();

    // 正方形チェック
    if width != height {
        return Err(format!("Input image must be square. Got {}x{}", width, height).into());
    }

    for size in SIZES {
        let resized = img.resize_exact(size, size, FilterType::Lanczos3);

        let output_path = dist_dir.join(format!("{size}.png"));
        resized.save(&output_path)?;

        println!("Saved: {}", output_path.display());
    }

    Ok(())
}
