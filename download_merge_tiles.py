#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script untuk download tiles dari petadasar.atrbpn.go.id dan merge menjadi GeoTIFF
"""

import os
import sys
import requests
from pathlib import Path
import subprocess
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple

# Fix Windows terminal encoding untuk support emoji
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Setup GDAL environment variables untuk subprocess
def setup_gdal_env():
    """Setup environment variables untuk GDAL commands"""
    env = os.environ.copy()

    # Set GDAL paths
    gdal_path = r"C:\Program Files\GDAL"
    proj_lib_path = r"C:\Program Files\GDAL\projlib"
    gdal_data_path = r"C:\Program Files\GDAL\gdal-data"

    # Add GDAL to PATH if not already there
    if gdal_path not in env.get('PATH', ''):
        env['PATH'] = gdal_path + os.pathsep + env.get('PATH', '')

    # Set PROJ_LIB
    env['PROJ_LIB'] = proj_lib_path

    # Set GDAL_DATA
    env['GDAL_DATA'] = gdal_data_path

    return env


def get_unique_filename(base_dir: Path, base_name: str, extension: str = ".tif") -> Path:
    """
    Generate unique filename dengan increment number
    Contoh: merged_map_001.tif, merged_map_002.tif, dst.
    """
    # Cek apakah file base sudah ada
    base_path = base_dir / f"{base_name}{extension}"

    if not base_path.exists():
        return base_path

    # Jika sudah ada, cari nomor increment berikutnya
    counter = 1
    while True:
        new_name = f"{base_name}_{counter:03d}{extension}"
        new_path = base_dir / new_name

        if not new_path.exists():
            return new_path

        counter += 1

        # Safety limit untuk avoid infinite loop
        if counter > 9999:
            raise ValueError("Terlalu banyak file! Maksimal 9999 file.")


# ============= KONFIGURASI =============
# Range tiles yang ingin didownload
X_START = 865069
X_END = 865080
Y_START = 525622
Y_END = 525650
ZOOM = 20
VARIANT = 2

# URL template
BASE_URL = "https://petadasar.atrbpn.go.id/wms/?d={x}/{y}/{z}/{variant}"

# Direktori output
OUTPUT_DIR = Path("tiles")
MERGED_DIR = Path("merged")

# Nama file output
OUTPUT_GEOTIFF = "merged_map.tif"

# Jumlah thread untuk parallel download
MAX_WORKERS = 10

# Headers untuk request (opsional, untuk menghindari blocking)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Referer': 'https://www.transmigrasi.go.id/'
}

# ============= FUNGSI UTILITAS =============

def tile_to_lat_lon(x: int, y: int, zoom: int) -> Tuple[float, float]:
    """
    Konversi tile coordinates (x, y, zoom) ke latitude/longitude
    Menggunakan Web Mercator projection
    """
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def get_tile_bounds(x: int, y: int, zoom: int) -> Tuple[float, float, float, float]:
    """
    Mendapatkan bounding box (minLat, minLon, maxLat, maxLon) dari tile
    """
    lat_top, lon_left = tile_to_lat_lon(x, y, zoom)
    lat_bottom, lon_right = tile_to_lat_lon(x + 1, y + 1, zoom)
    
    # Return: minLon, minLat, maxLon, maxLat (format GDAL)
    return lon_left, lat_bottom, lon_right, lat_top


def download_tile(x: int, y: int, zoom: int, variant: int, output_path: Path) -> bool:
    """
    Download satu tile dan simpan ke file
    Returns True jika sukses, False jika gagal
    """
    url = BASE_URL.format(x=x, y=y, z=zoom, variant=variant)
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            # Simpan file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        else:
            print(f"❌ Error downloading {x}/{y}: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error downloading {x}/{y}: {str(e)}")
        return False


def download_all_tiles(x_start: int, x_end: int, y_start: int, y_end: int, 
                       zoom: int, variant: int, output_dir: Path) -> list:
    """
    Download semua tiles dalam range yang ditentukan secara parallel
    Returns list of successfully downloaded tile paths
    """
    # Buat direktori output
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Buat list semua tiles yang perlu didownload
    tiles_to_download = []
    for x in range(x_start, x_end + 1):
        for y in range(y_start, y_end + 1):
            filename = f"tile_{zoom}_{x}_{y}.jpg"
            output_path = output_dir / filename
            tiles_to_download.append((x, y, output_path))
    
    total_tiles = len(tiles_to_download)
    print(f"📥 Mulai download {total_tiles} tiles...")
    print(f"   Range X: {x_start} - {x_end} ({x_end - x_start + 1} tiles)")
    print(f"   Range Y: {y_start} - {y_end} ({y_end - y_start + 1} tiles)")
    print(f"   Zoom: {zoom}, Variant: {variant}")
    print(f"   Menggunakan {MAX_WORKERS} parallel workers\n")
    
    # Download dengan ThreadPoolExecutor untuk parallel processing
    downloaded_files = []
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit semua download tasks
        future_to_tile = {
            executor.submit(download_tile, x, y, zoom, variant, path): (x, y, path)
            for x, y, path in tiles_to_download
        }
        
        # Process completed downloads
        completed = 0
        for future in as_completed(future_to_tile):
            x, y, path = future_to_tile[future]
            completed += 1
            
            try:
                success = future.result()
                if success:
                    downloaded_files.append(path)
                    print(f"✓ [{completed}/{total_tiles}] Downloaded tile {x}/{y}")
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"❌ [{completed}/{total_tiles}] Exception for tile {x}/{y}: {str(e)}")
                failed_count += 1
    
    print(f"\n📊 Download selesai!")
    print(f"   Berhasil: {len(downloaded_files)}/{total_tiles}")
    print(f"   Gagal: {failed_count}/{total_tiles}\n")
    
    return downloaded_files


def add_georeference_to_tiles(tile_paths: list, zoom: int) -> list:
    """
    Menambahkan georeference ke setiap tile JPG menggunakan gdal_translate
    Returns list of georeferenced tile paths
    """
    print(f"🌍 Menambahkan georeference ke {len(tile_paths)} tiles...")
    georef_dir = OUTPUT_DIR / "georeferenced"
    georef_dir.mkdir(parents=True, exist_ok=True)

    georeferenced_tiles = []
    failed = 0

    for i, tile_path in enumerate(tile_paths, 1):
        # Parse tile coordinates from filename: tile_20_865069_525622.jpg
        parts = tile_path.stem.split('_')
        if len(parts) >= 4:
            x = int(parts[2])
            y = int(parts[3])

            # Get bounds for this tile
            min_lon, min_lat, max_lon, max_lat = get_tile_bounds(x, y, zoom)

            # Output georeferenced file (GeoTIFF)
            georef_path = georef_dir / f"{tile_path.stem}.tif"

            # Use gdal_translate to add georeference
            cmd = [
                'gdal_translate',
                '-of', 'GTiff',
                '-a_srs', 'EPSG:4326',
                '-a_ullr', str(min_lon), str(max_lat), str(max_lon), str(min_lat),
                str(tile_path),
                str(georef_path)
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=setup_gdal_env())
                if result.returncode == 0:
                    georeferenced_tiles.append(georef_path)
                    if i % 50 == 0 or i == len(tile_paths):
                        print(f"   ✓ Processed {i}/{len(tile_paths)} tiles")
                else:
                    print(f"   ❌ Failed to georeference {tile_path.name}: {result.stderr}")
                    failed += 1
            except Exception as e:
                print(f"   ❌ Error processing {tile_path.name}: {str(e)}")
                failed += 1

    print(f"✓ Georeference selesai! Berhasil: {len(georeferenced_tiles)}, Gagal: {failed}\n")
    return georeferenced_tiles


def create_vrt_with_georef(tile_paths: list, x_start: int, y_start: int,
                           x_end: int, y_end: int, zoom: int, output_vrt: Path) -> bool:
    """
    Buat VRT file dengan georeferencing untuk semua tiles
    """
    if not tile_paths:
        print("❌ Tidak ada tiles untuk di-merge!")
        return False

    # Calculate overall bounds
    x_tiles = x_end - x_start + 1
    y_tiles = y_end - y_start + 1

    # Get bounding box for entire tile set
    min_lon, min_lat, _, _ = get_tile_bounds(x_start, y_end, zoom)
    _, _, max_lon, max_lat = get_tile_bounds(x_end, y_start, zoom)
    
    print(f"📍 Bounding Box:")
    print(f"   Min: {min_lat:.6f}, {min_lon:.6f}")
    print(f"   Max: {max_lat:.6f}, {max_lon:.6f}\n")
    
    # Buat VRT file dengan gdalbuildvrt
    vrt_cmd = [
        'gdalbuildvrt',
        '-resolution', 'highest',
        '-te', str(min_lon), str(min_lat), str(max_lon), str(max_lat),  # target extent
        '-a_srs', 'EPSG:4326',  # WGS84
        str(output_vrt)
    ]
    
    # Tambahkan semua tile paths
    vrt_cmd.extend([str(p) for p in tile_paths])
    
    try:
        print(f"🔨 Membuat VRT file...")
        result = subprocess.run(vrt_cmd, capture_output=True, text=True, env=setup_gdal_env())

        if result.returncode == 0:
            print(f"✓ VRT file berhasil dibuat: {output_vrt}\n")
            return True
        else:
            print(f"❌ Error membuat VRT:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ GDAL tidak ditemukan! Pastikan GDAL sudah terinstall.")
        print("   Install dengan: sudo apt-get install gdal-bin (Linux)")
        print("   atau download dari: https://gdal.org")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def merge_to_geotiff(vrt_file: Path, output_tif: Path) -> bool:
    """
    Konversi VRT ke GeoTIFF menggunakan gdal_translate
    """
    if not vrt_file.exists():
        print(f"❌ VRT file tidak ditemukan: {vrt_file}")
        return False
    
    # Gunakan gdal_translate untuk konversi VRT ke GeoTIFF
    translate_cmd = [
        'gdal_translate',
        '-of', 'GTiff',
        '-co', 'COMPRESS=LZW',  # Kompresi untuk ukuran file lebih kecil
        '-co', 'TILED=YES',     # Tiled TIFF untuk performa lebih baik
        '-co', 'BIGTIFF=IF_SAFER',  # Support file besar
        str(vrt_file),
        str(output_tif)
    ]
    
    try:
        print(f"🔨 Merging tiles ke GeoTIFF...")
        print(f"   Output: {output_tif}")
        result = subprocess.run(translate_cmd, capture_output=True, text=True, env=setup_gdal_env())

        if result.returncode == 0:
            # Get file size
            file_size_mb = output_tif.stat().st_size / (1024 * 1024)
            print(f"\n✅ GeoTIFF berhasil dibuat!")
            print(f"   File: {output_tif}")
            print(f"   Size: {file_size_mb:.2f} MB\n")
            return True
        else:
            print(f"❌ Error membuat GeoTIFF:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def get_user_input() -> dict:
    """
    Meminta input koordinat tiles dari user
    Returns dict dengan x_start, x_end, y_start, y_end, zoom, variant
    """
    print("📌 Masukkan koordinat tiles yang ingin didownload:")
    print("   (Tekan Enter untuk menggunakan nilai default)\n")

    # Input X Start
    while True:
        x_start_input = input(f"X Start (default: {X_START}): ").strip()
        if x_start_input == "":
            x_start = X_START
            break
        try:
            x_start = int(x_start_input)
            break
        except ValueError:
            print("❌ Input harus berupa angka! Coba lagi.\n")

    # Input X End
    while True:
        x_end_input = input(f"X End (default: {X_END}): ").strip()
        if x_end_input == "":
            x_end = X_END
            break
        try:
            x_end = int(x_end_input)
            if x_end < x_start:
                print("❌ X End harus >= X Start! Coba lagi.\n")
                continue
            break
        except ValueError:
            print("❌ Input harus berupa angka! Coba lagi.\n")

    # Input Y Start
    while True:
        y_start_input = input(f"Y Start (default: {Y_START}): ").strip()
        if y_start_input == "":
            y_start = Y_START
            break
        try:
            y_start = int(y_start_input)
            break
        except ValueError:
            print("❌ Input harus berupa angka! Coba lagi.\n")

    # Input Y End
    while True:
        y_end_input = input(f"Y End (default: {Y_END}): ").strip()
        if y_end_input == "":
            y_end = Y_END
            break
        try:
            y_end = int(y_end_input)
            if y_end < y_start:
                print("❌ Y End harus >= Y Start! Coba lagi.\n")
                continue
            break
        except ValueError:
            print("❌ Input harus berupa angka! Coba lagi.\n")

    # Input Zoom
    while True:
        zoom_input = input(f"Zoom Level (default: {ZOOM}): ").strip()
        if zoom_input == "":
            zoom = ZOOM
            break
        try:
            zoom = int(zoom_input)
            if zoom < 0 or zoom > 22:
                print("❌ Zoom harus antara 0-22! Coba lagi.\n")
                continue
            break
        except ValueError:
            print("❌ Input harus berupa angka! Coba lagi.\n")

    # Input Variant
    while True:
        variant_input = input(f"Variant (default: {VARIANT}): ").strip()
        if variant_input == "":
            variant = VARIANT
            break
        try:
            variant = int(variant_input)
            break
        except ValueError:
            print("❌ Input harus berupa angka! Coba lagi.\n")

    # Hitung jumlah tiles
    total_tiles = (x_end - x_start + 1) * (y_end - y_start + 1)

    # Konfirmasi
    print("\n" + "=" * 60)
    print("📋 Ringkasan:")
    print("=" * 60)
    print(f"  X Range: {x_start} - {x_end} ({x_end - x_start + 1} tiles)")
    print(f"  Y Range: {y_start} - {y_end} ({y_end - y_start + 1} tiles)")
    print(f"  Zoom: {zoom}")
    print(f"  Variant: {variant}")
    print(f"  Total tiles: {total_tiles}")
    print("=" * 60)

    confirm = input("\n✅ Lanjutkan download? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ Download dibatalkan.")
        sys.exit(0)

    print()
    return {
        'x_start': x_start,
        'x_end': x_end,
        'y_start': y_start,
        'y_end': y_end,
        'zoom': zoom,
        'variant': variant
    }


def main():
    """
    Main function
    """
    print("=" * 60)
    print("   BPN Tile Downloader & GeoTIFF Merger")
    print("=" * 60)
    print()

    # Get user input
    config = get_user_input()

    # 1. Download tiles
    downloaded_files = download_all_tiles(
        config['x_start'], config['x_end'],
        config['y_start'], config['y_end'],
        config['zoom'], config['variant'],
        OUTPUT_DIR
    )
    
    if not downloaded_files:
        print("❌ Tidak ada tiles yang berhasil didownload!")
        return

    # 2. Add georeference to tiles
    georeferenced_tiles = add_georeference_to_tiles(downloaded_files, config['zoom'])

    if not georeferenced_tiles:
        print("❌ Tidak ada tiles yang berhasil di-georeference!")
        return

    # 3. Buat direktori untuk merged output
    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Buat VRT dengan georeferencing
    vrt_file = MERGED_DIR / "mosaic.vrt"
    if not create_vrt_with_georef(georeferenced_tiles, config['x_start'], config['y_start'],
                                    config['x_end'], config['y_end'], config['zoom'], vrt_file):
        return

    # 5. Merge ke GeoTIFF dengan unique filename
    base_name = OUTPUT_GEOTIFF.replace(".tif", "").replace(".TIF", "")
    output_geotiff = get_unique_filename(MERGED_DIR, base_name, ".tif")

    print(f"📁 Output file: {output_geotiff.name}\n")

    if merge_to_geotiff(vrt_file, output_geotiff):
        print("=" * 60)
        print("✅ SELESAI!")
        print("=" * 60)
        print(f"\nFile output:")
        print(f"  - Tiles: {OUTPUT_DIR}/")
        print(f"  - VRT: {vrt_file}")
        print(f"  - GeoTIFF: {output_geotiff}")
        print()
        print("Anda bisa membuka GeoTIFF di QGIS atau software GIS lainnya.")
    else:
        print("\n❌ Gagal membuat GeoTIFF!")


if __name__ == "__main__":
    main()