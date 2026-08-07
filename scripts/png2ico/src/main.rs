use std::env;
use std::fs::{self, File};
use std::path::Path;

use ico::{IconDir, IconDirEntry, IconImage, ResourceType};
use image::GenericImageView;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: {} <input.png>", args[0]);
        std::process::exit(1);
    }

    let input = Path::new(&args[1]);

    // 出力ディレクトリ
    let dist_dir = Path::new("dist");
    fs::create_dir_all(dist_dir)?; // 無ければ作成

    // ファイル名を取得して .ico に変更
    let file_stem = input.file_stem().ok_or("Invalid input filename")?;

    let output_path = dist_dir.join(format!("{}.ico", file_stem.to_string_lossy()));

    // 画像読み込み
    let img = image::open(input)?;
    let (width, height) = img.dimensions();

    // 16x16でなければリサイズ
    let resized = if width != 16 || height != 16 {
        img.resize_exact(16, 16, image::imageops::FilterType::Lanczos3)
    } else {
        img
    };

    let rgba = resized.to_rgba8();

    let icon_image = IconImage::from_rgba_data(16, 16, rgba.into_raw());
    let entry = IconDirEntry::encode(&icon_image)?;

    let mut icon_dir = IconDir::new(ResourceType::Icon);
    icon_dir.add_entry(entry);

    let file = File::create(&output_path)?;
    icon_dir.write(file)?;

    println!("Converted {} -> {}", input.display(), output_path.display());

    Ok(())
}
