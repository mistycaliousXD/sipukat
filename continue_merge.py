#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script untuk melanjutkan merge tiles yang sudah di-georeference
Gunakan ini jika proses merge terputus setelah georeferencing selesai
"""

import sys
import os
from pathlib import Path
import subprocess

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


# Direktori
GEOREF_DIR = Path("tiles/georeferenced")
MERGED_DIR = Path("merged")
OUTPUT_GEOTIFF = "merged_map.tif"


def tile_to_lat_lon(x: int, y: int, zoom: int):
    """Konversi tile coordinates ke lat/lon"""
    import math
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def get_tile_bounds(x: int, y: int, zoom: int):
    """Mendapatkan bounding box dari tile"""
    lat_top, lon_left = tile_to_lat_lon(x, y, zoom)
    lat_bottom, lon_right = tile_to_lat_lon(x + 1, y + 1, zoom)
    return lon_left, lat_bottom, lon_right, lat_top


def create_vrt_from_georef(georef_dir: Path, output_vrt: Path):
    """Buat VRT dari tiles yang sudah di-georeference"""
    # Cari semua file .tif di folder georeferenced
    all_tiles = sorted(georef_dir.glob("tile_*.tif"))

    if not all_tiles:
        print("❌ Tidak ada georeferenced tiles ditemukan!")
        print(f"   Pastikan ada file .tif di: {georef_dir}")
        return False

    # Group by zoom level
    tiles_by_zoom = {}
    for tile_file in all_tiles:
        parts = tile_file.stem.split('_')
        if len(parts) >= 4:
            z = int(parts[1])
            if z not in tiles_by_zoom:
                tiles_by_zoom[z] = []
            tiles_by_zoom[z].append(tile_file)

    # Gunakan zoom level dengan tiles terbanyak atau tanya user
    if len(tiles_by_zoom) > 1:
        print(f"\n⚠️  Ditemukan tiles dengan beberapa zoom level:")
        for z, tiles in sorted(tiles_by_zoom.items()):
            print(f"   Zoom {z}: {len(tiles)} tiles")

        # Gunakan zoom dengan tiles terbanyak
        zoom = max(tiles_by_zoom.keys(), key=lambda z: len(tiles_by_zoom[z]))
        print(f"\n✅ Menggunakan Zoom {zoom} ({len(tiles_by_zoom[zoom])} tiles)")
        tile_files = tiles_by_zoom[zoom]
    else:
        zoom = list(tiles_by_zoom.keys())[0]
        tile_files = tiles_by_zoom[zoom]
        print(f"✅ Ditemukan {len(tile_files)} georeferenced tiles (Zoom {zoom})")

    # Parse koordinat dari nama file untuk mendapatkan bounds
    x_coords = []
    y_coords = []

    for tile_file in tile_files:
        # Format: tile_20_865111_525647.tif
        parts = tile_file.stem.split('_')
        if len(parts) >= 4:
            x = int(parts[2])
            y = int(parts[3])
            x_coords.append(x)
            y_coords.append(y)

    if not x_coords:
        print("❌ Tidak bisa parse koordinat dari nama file!")
        return False

    x_start, x_end = min(x_coords), max(x_coords)
    y_start, y_end = min(y_coords), max(y_coords)

    # Calculate bounding box
    min_lon, min_lat, _, _ = get_tile_bounds(x_start, y_end, zoom)
    _, _, max_lon, max_lat = get_tile_bounds(x_end, y_start, zoom)

    print(f"\n📍 Bounding Box:")
    print(f"   Min: {min_lat:.6f}, {min_lon:.6f}")
    print(f"   Max: {max_lat:.6f}, {max_lon:.6f}")
    print(f"   Zoom: {zoom}\n")

    # Buat VRT
    vrt_cmd = [
        'gdalbuildvrt',
        '-resolution', 'highest',
        '-te', str(min_lon), str(min_lat), str(max_lon), str(max_lat),
        '-a_srs', 'EPSG:4326',
        str(output_vrt)
    ]
    vrt_cmd.extend([str(f) for f in tile_files])

    try:
        print("🔨 Membuat VRT file...")
        result = subprocess.run(vrt_cmd, capture_output=True, text=True, env=setup_gdal_env())

        if result.returncode == 0:
            print(f"✓ VRT file berhasil dibuat: {output_vrt}\n")
            return True
        else:
            print(f"❌ Error membuat VRT:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("❌ GDAL tidak ditemukan!")
        print(f"   Cek PROJ_LIB: {os.environ.get('PROJ_LIB', 'NOT SET')}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def merge_to_geotiff(vrt_file: Path, output_tif: Path):
    """Konversi VRT ke GeoTIFF"""
    if not vrt_file.exists():
        print(f"❌ VRT file tidak ditemukan: {vrt_file}")
        return False

    translate_cmd = [
        'gdal_translate',
        '-of', 'GTiff',
        '-co', 'COMPRESS=LZW',
        '-co', 'TILED=YES',
        '-co', 'BIGTIFF=IF_SAFER',
        str(vrt_file),
        str(output_tif)
    ]

    try:
        print(f"🔨 Merging tiles ke GeoTIFF...")
        print(f"   Output: {output_tif}\n")

        result = subprocess.run(translate_cmd, capture_output=True, text=True, env=setup_gdal_env())

        if result.returncode == 0:
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


def main():
    print("=" * 60)
    print("   Continue Merge - GeoTIFF Creator")
    print("=" * 60)
    print()

    # Cek apakah ada georeferenced tiles
    if not GEOREF_DIR.exists():
        print(f"❌ Folder georeferenced tidak ditemukan: {GEOREF_DIR}")
        print("   Jalankan download_merge_tiles.py terlebih dahulu!")
        return

    # Buat direktori merged
    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    # Buat VRT
    vrt_file = MERGED_DIR / "mosaic.vrt"
    if not create_vrt_from_georef(GEOREF_DIR, vrt_file):
        return

    # Merge ke GeoTIFF dengan unique filename
    base_name = OUTPUT_GEOTIFF.replace(".tif", "").replace(".TIF", "")
    output_geotiff = get_unique_filename(MERGED_DIR, base_name, ".tif")

    print(f"📁 Output file: {output_geotiff.name}\n")

    if merge_to_geotiff(vrt_file, output_geotiff):
        print("=" * 60)
        print("✅ SELESAI!")
        print("=" * 60)
        print(f"\nFile output:")
        print(f"  - VRT: {vrt_file}")
        print(f"  - GeoTIFF: {output_geotiff}")
        print()
        print("Anda bisa membuka GeoTIFF di QGIS atau software GIS lainnya.")
    else:
        print("\n❌ Gagal membuat GeoTIFF!")


if __name__ == "__main__":
    main()
