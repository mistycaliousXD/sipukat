#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Georeferencer
Menambahkan georeference ke tiles dalam batches
"""

import os
import sys
import json
import argparse
import subprocess
import math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Fix Windows terminal encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Progress bar
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# ============= KONFIGURASI =============
TILES_DIR = Path("tiles")
GEOREF_DIR = Path("georeferenced")
PROGRESS_FILE = GEOREF_DIR / "georeference_progress.json"
MAX_WORKERS = 4  # CPU intensive, don't use too many


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


def tile_to_lat_lon(x: int, y: int, zoom: int):
    """Convert tile coordinates to lat/lon"""
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def get_tile_bounds(x: int, y: int, zoom: int):
    """Get bounding box dari tile"""
    lat_top, lon_left = tile_to_lat_lon(x, y, zoom)
    lat_bottom, lon_right = tile_to_lat_lon(x + 1, y + 1, zoom)
    return lon_left, lat_bottom, lon_right, lat_top


def georeference_tile(tile_path: Path, output_path: Path, x: int, y: int, zoom: int):
    """Add georeference to single tile"""
    # Skip if already exists
    if output_path.exists():
        return {'status': 'skipped', 'tile': tile_path.name}

    # Get bounds for this tile
    min_lon, min_lat, max_lon, max_lat = get_tile_bounds(x, y, zoom)

    # Use gdal_translate to add georeference
    cmd = [
        'gdal_translate',
        '-of', 'GTiff',
        '-a_srs', 'EPSG:4326',
        '-a_ullr', str(min_lon), str(max_lat), str(max_lon), str(min_lat),
        str(tile_path),
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=setup_gdal_env())
        if result.returncode == 0:
            return {'status': 'success', 'tile': tile_path.name}
        else:
            return {'status': 'failed', 'tile': tile_path.name, 'error': result.stderr}
    except Exception as e:
        return {'status': 'failed', 'tile': tile_path.name, 'error': str(e)}


def list_available_batches(count_tiles=False):
    """List all available tile batches

    Args:
        count_tiles: If True, count tiles eagerly. If False, set tiles_count to None (lazy loading)
    """
    if not TILES_DIR.exists():
        return []

    batches = []
    for batch_dir in sorted(TILES_DIR.glob("tiles_batch_*")):
        if batch_dir.is_dir():
            batch_num = int(batch_dir.name.split('_')[-1])
            # Only count tiles if explicitly requested (e.g., for --list mode)
            tile_count = len(list(batch_dir.glob("*.jpg"))) if count_tiles else None
            batches.append({
                'batch_num': batch_num,
                'path': batch_dir,
                'tiles_count': tile_count
            })

    return batches


def get_batch_tile_count(batch_path):
    """Count tiles in a batch on-demand

    Args:
        batch_path: Path to the batch directory

    Returns:
        Number of tiles in the batch
    """
    return len(list(batch_path.glob("*.jpg")))


def load_progress():
    """Load georeference progress"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'completed_batches': [], 'batch_details': {}}
    return {'completed_batches': [], 'batch_details': {}}


def save_progress(progress_data):
    """Save georeference progress"""
    GEOREF_DIR.mkdir(parents=True, exist_ok=True)
    progress_data['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress_data, f, indent=2)


def georeference_batch(batch_info, progress_data):
    """Georeference all tiles in a batch"""
    batch_num = batch_info['batch_num']
    batch_dir = batch_info['path']
    output_dir = GEOREF_DIR / f"georeferenced_batch_{batch_num:03d}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all tiles in batch
    tile_files = sorted(batch_dir.glob("tile_*.jpg"))

    if not tile_files:
        print(f"❌ Batch {batch_num}: Tidak ada tiles ditemukan")
        return

    print(f"\n🌍 Processing Batch {batch_num} ({len(tile_files)} tiles)...")

    success_count = 0
    failed_count = 0
    skipped_count = 0
    failed_list = []

    import time
    start_time = time.time()

    # Progress bar
    if HAS_TQDM:
        pbar = tqdm(total=len(tile_files), desc=f"Batch {batch_num}", unit="tiles")

    # Process with thread pool
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []

        for tile_file in tile_files:
            # Parse coordinates from filename: tile_21_1728675_1051362.jpg
            parts = tile_file.stem.split('_')
            if len(parts) >= 4:
                zoom = int(parts[1])
                x = int(parts[2])
                y = int(parts[3])

                output_path = output_dir / f"{tile_file.stem}.tif"

                future = executor.submit(georeference_tile, tile_file, output_path, x, y, zoom)
                futures.append(future)

        for future in as_completed(futures):
            result = future.result()

            if result['status'] == 'success':
                success_count += 1
            elif result['status'] == 'skipped':
                skipped_count += 1
            elif result['status'] == 'failed':
                failed_count += 1
                failed_list.append({
                    'tile': result['tile'],
                    'error': result.get('error', 'Unknown error')
                })

            if HAS_TQDM:
                pbar.update(1)
                pbar.set_postfix({
                    'OK': success_count,
                    'Skip': skipped_count,
                    'Fail': failed_count
                })

    if HAS_TQDM:
        pbar.close()

    elapsed_time = time.time() - start_time

    # Save progress
    batch_stats = {
        'status': 'completed',
        'tiles': len(tile_files),
        'success': success_count,
        'skipped': skipped_count,
        'failed': failed_count,
        'time_seconds': elapsed_time,
        'failed_tiles': failed_list if failed_list else []
    }

    progress_data['batch_details'][str(batch_num)] = batch_stats
    if batch_num not in progress_data['completed_batches']:
        progress_data['completed_batches'].append(batch_num)

    save_progress(progress_data)

    # Print summary
    print(f"✅ Batch {batch_num} selesai!")
    print(f"   Sukses: {success_count} | Skipped: {skipped_count} | Gagal: {failed_count}")
    print(f"   Output: {output_dir}")

    if failed_list:
        print(f"   ⚠️  {len(failed_list)} tiles gagal di-georeference")


def main():
    parser = argparse.ArgumentParser(description='Batch Georeferencer')
    parser.add_argument('--batch', type=int, help='Process batch tertentu')
    parser.add_argument('--batch-range', help='Process batch range (e.g., 1-10)')
    parser.add_argument('--all', action='store_true', help='Process semua batch')
    parser.add_argument('--list', action='store_true', help='List available batches')

    args = parser.parse_args()

    print("=" * 60)
    print("   Batch Georeferencer")
    print("=" * 60)
    print()

    # List available batches (fast mode - no tile counting)
    print("🔍 Scanning batches...", end='', flush=True)
    available_batches = list_available_batches(count_tiles=False)
    print(f" Found {len(available_batches)} batches")

    if not available_batches:
        print("❌ Tidak ada tiles batches ditemukan!")
        print(f"   Jalankan download_tiles_batch.py terlebih dahulu")
        return

    # List mode - need to count tiles for display
    if args.list:
        print(f"📋 Available Batches ({len(available_batches)}):\n")
        for batch in available_batches:
            # Count tiles on-demand for list display
            if batch['tiles_count'] is None:
                batch['tiles_count'] = get_batch_tile_count(batch['path'])
            print(f"   Batch {batch['batch_num']:03d}: {batch['tiles_count']:,} tiles")
        print()
        return

    # Load progress
    progress = load_progress()

    # Determine which batches to process
    batches_to_process = []

    if args.all:
        batches_to_process = available_batches
        print(f"📥 Processing ALL {len(batches_to_process)} batches...")

    elif args.batch:
        batch = next((b for b in available_batches if b['batch_num'] == args.batch), None)
        if batch:
            batches_to_process = [batch]
            print(f"📥 Processing Batch {args.batch}...")
        else:
            print(f"❌ Batch {args.batch} tidak ditemukan")
            return

    elif args.batch_range:
        try:
            start, end = map(int, args.batch_range.split('-'))
            batches_to_process = [b for b in available_batches if start <= b['batch_num'] <= end]
            print(f"📥 Processing Batches {start}-{end} ({len(batches_to_process)} batches)...")
        except:
            print("❌ Invalid batch range format. Use: --batch-range 1-10")
            return

    else:
        # Interactive mode
        print(f"📋 Available Batches: {len(available_batches)}\n")

        # Show first 10 - count tiles on-demand for display
        for batch in available_batches[:10]:
            if batch['tiles_count'] is None:
                batch['tiles_count'] = get_batch_tile_count(batch['path'])
            status = "✅" if batch['batch_num'] in progress['completed_batches'] else "⏳"
            print(f"   {status} Batch {batch['batch_num']:03d}: {batch['tiles_count']:,} tiles")

        if len(available_batches) > 10:
            print(f"   ... dan {len(available_batches) - 10} batches lainnya")

        print("\nOptions:")
        print("  - Specific batch: 1")
        print("  - Multiple batches: 1,2,5,10")
        print("  - Batch range: 1-10")
        print("  - All batches: all")
        print()

        choice = input("Pilih batch untuk diproses: ").strip()

        if choice.lower() == 'all':
            batches_to_process = available_batches
        elif ',' in choice:
            # Comma-separated batch numbers
            try:
                batch_nums = [int(x.strip()) for x in choice.split(',')]
                batches_to_process = [b for b in available_batches if b['batch_num'] in batch_nums]
                if not batches_to_process:
                    print("❌ Tidak ada batch yang valid ditemukan")
                    return
            except:
                print("❌ Invalid input - gunakan format: 1,2,5,10")
                return
        elif '-' in choice:
            try:
                start, end = map(int, choice.split('-'))
                batches_to_process = [b for b in available_batches if start <= b['batch_num'] <= end]
            except:
                print("❌ Invalid input")
                return
        else:
            try:
                batch_num = int(choice)
                batch = next((b for b in available_batches if b['batch_num'] == batch_num), None)
                if batch:
                    batches_to_process = [batch]
                else:
                    print(f"❌ Batch {batch_num} tidak ditemukan")
                    return
            except:
                print("❌ Invalid input")
                return

    if not batches_to_process:
        print("❌ Tidak ada batch untuk diproses")
        return

    # Process batches
    try:
        for i, batch in enumerate(batches_to_process, 1):
            print(f"\n{'='*60}")
            print(f"Progress: {i}/{len(batches_to_process)} batches")
            print(f"{'='*60}")

            georeference_batch(batch, progress)

        # Final summary
        print("\n" + "=" * 60)
        print("✅ GEOREFERENCE SELESAI!")
        print("=" * 60)
        print(f"Total batches processed: {len(batches_to_process)}")
        print(f"Output directory: {GEOREF_DIR.absolute()}/")
        print()

    except KeyboardInterrupt:
        print("\n\n⏸️  Processing di-pause")
        print(f"   Progress tersimpan di: {PROGRESS_FILE}")
        print()


if __name__ == "__main__":
    main()
