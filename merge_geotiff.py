#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoTIFF Merger
Merge semua georeferenced batches menjadi single GeoTIFF
"""

import os
import sys
import argparse
import subprocess
import math
import multiprocessing
import time
import signal
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Fix Windows terminal encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# ============= KONFIGURASI =============
DEFAULT_GEOREF_SUFFIX = "_georeferenced"
DEFAULT_MERGED_SUFFIX = "_merged"
OUTPUT_GEOTIFF = "merged_map.tif"

# Global flag for graceful shutdown
SHUTDOWN_REQUESTED = False


def setup_gdal_env():
    """Setup environment variables untuk GDAL commands dengan optimasi performance"""
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

    # ===== PERFORMANCE OPTIMIZATIONS =====
    # Multi-threading: Use all available CPU cores
    env['GDAL_NUM_THREADS'] = 'ALL_CPUS'

    # Cache optimization: Dynamic cache sizing based on available RAM
    # Default is 5%, we use 25% for maximum performance
    if HAS_PSUTIL:
        try:
            # Get available memory and set cache to 25% of it
            available_ram_mb = psutil.virtual_memory().available / (1024 * 1024)
            cache_size_mb = int(available_ram_mb * 0.25)
            # Cap at 4GB to avoid excessive memory usage
            cache_size_mb = min(cache_size_mb, 4096)
            # Minimum 512MB
            cache_size_mb = max(cache_size_mb, 512)
            env['GDAL_CACHEMAX'] = str(cache_size_mb)
        except:
            env['GDAL_CACHEMAX'] = '512'  # Fallback to 512MB
    else:
        env['GDAL_CACHEMAX'] = '512'  # 512MB if psutil not available

    # Disable PAM (Persistent Auxiliary Metadata) for faster processing
    env['GDAL_PAM_ENABLED'] = 'NO'

    # Optimize VRT reading
    env['VRT_SHARED_SOURCE'] = '0'

    # TIFF optimization
    env['GDAL_TIFF_INTERNAL_MASK'] = 'YES'

    return env


def get_unique_filename(base_dir: Path, base_name: str, extension: str = ".tif") -> Path:
    """Generate unique filename dengan increment number"""
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

        # Safety limit
        if counter > 9999:
            raise ValueError("Terlalu banyak file! Maksimal 9999 file.")


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


def list_available_georef_folders():
    """List all available georeferenced folders"""
    folders = []

    # Search for directories ending with _georeferenced or containing georeferenced_batch folders
    for path in Path('.').iterdir():
        if path.is_dir():
            # Check if it contains georeferenced_batch folders
            batch_dirs = list(path.glob("georeferenced_batch_*"))
            if batch_dirs:
                batch_count = len(batch_dirs)
                # Count total tiles
                total_tiles = sum(len(list(bd.glob("tile_*.tif"))) for bd in batch_dirs)
                folders.append({
                    'name': path.name,
                    'path': path,
                    'batch_count': batch_count,
                    'total_tiles': total_tiles
                })

    return sorted(folders, key=lambda x: x['name'])


def check_batch_ready(batch_num, georef_dir):
    """Check if a batch is georeferenced and ready for merging

    Args:
        batch_num: Batch number to check
        georef_dir: Georeferenced directory path

    Returns:
        dict with 'ready' (bool), 'path' (Path), 'tiles_count' (int), 'tiles' (list)
        or None if not ready
    """
    batch_dir = georef_dir / f"georeferenced_batch_{batch_num:03d}"

    if not batch_dir.exists() or not batch_dir.is_dir():
        return None

    tile_files = list(batch_dir.glob("tile_*.tif"))

    if not tile_files:
        return None

    return {
        'ready': True,
        'batch_num': batch_num,
        'path': batch_dir,
        'tiles_count': len(tile_files),
        'tiles': tile_files
    }


def find_georeferenced_batches(georef_dir, batch_filter=None):
    """Find all georeferenced batches

    Args:
        georef_dir: Georeferenced directory path
        batch_filter: List of batch numbers to filter
    """
    if not georef_dir.exists():
        return []

    batches = []
    for batch_dir in sorted(georef_dir.glob("georeferenced_batch_*")):
        if batch_dir.is_dir():
            batch_num = int(batch_dir.name.split('_')[-1])

            # Apply filter if specified
            if batch_filter and batch_num not in batch_filter:
                continue

            tile_files = list(batch_dir.glob("tile_*.tif"))
            if tile_files:
                batches.append({
                    'batch_num': batch_num,
                    'path': batch_dir,
                    'tiles_count': len(tile_files),
                    'tiles': tile_files
                })

    return batches


def parse_tile_info(tile_file):
    """Parse tile information from filename - used for parallel processing"""
    parts = tile_file.stem.split('_')
    if len(parts) >= 4:
        z = int(parts[1])
        x = int(parts[2])
        y = int(parts[3])
        return tile_file, z, x, y
    return tile_file, None, None, None


def create_vrt(batches, output_vrt: Path, verbose=True, resampling='cubic'):
    """Create VRT from all batches with parallel metadata extraction

    Args:
        batches: List of batch info dicts
        output_vrt: Output VRT file path
        verbose: Show progress messages
        resampling: Resampling algorithm - 'nearest', 'bilinear', 'cubic', 'lanczos' (default: cubic)
    """
    if verbose:
        print(f"🔨 Membuat VRT dari {len(batches)} batches...")
        print(f"   Resampling: {resampling}")

    # Collect all tiles from all batches first
    all_tile_files = []
    for batch in batches:
        all_tile_files.extend(batch['tiles'])

    if not all_tile_files:
        if verbose:
            print("❌ Tidak ada tiles ditemukan!")
        return False

    if verbose:
        print(f"   Total tiles: {len(all_tile_files):,}")
        print(f"   Parsing metadata...", end='', flush=True)

    # Parse tile metadata in parallel for speed
    all_tiles = []
    x_coords = []
    y_coords = []
    zoom = None

    # Use ThreadPoolExecutor for parallel metadata parsing
    max_workers = min(8, multiprocessing.cpu_count())  # Limit to 8 threads for I/O
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(parse_tile_info, all_tile_files))

    # Collect parsed results
    for tile_file, z, x, y in results:
        all_tiles.append(tile_file)
        if x is not None and y is not None:
            x_coords.append(x)
            y_coords.append(y)
            if zoom is None and z is not None:
                zoom = z

    if verbose:
        print(f" Done!")

    if verbose:
        print(f"   Zoom: {zoom}")

    # Calculate overall bounds
    x_start, x_end = min(x_coords), max(x_coords)
    y_start, y_end = min(y_coords), max(y_coords)

    min_lon, min_lat, _, _ = get_tile_bounds(x_start, y_end, zoom)
    _, _, max_lon, max_lat = get_tile_bounds(x_end, y_start, zoom)

    if verbose:
        print(f"   Bounding Box:")
        print(f"     Min: {min_lat:.6f}, {min_lon:.6f}")
        print(f"     Max: {max_lat:.6f}, {max_lon:.6f}")

    # Write tile list to file (to avoid Windows command line length limit)
    tile_list_file = output_vrt.parent / f"tile_list_{output_vrt.stem}.txt"
    with open(tile_list_file, 'w') as f:
        # Batch write - convert all paths at once and join with newlines
        tile_paths = [str(tile).replace('\\', '/') for tile in all_tiles]
        f.write('\n'.join(tile_paths) + '\n')

    if verbose:
        print(f"   Tile list: {tile_list_file}")
        print(f"\n⚙️  Running GDAL BuildVRT...", end='', flush=True)

    # Build VRT command
    # Use full path on Windows for better compatibility
    gdalbuildvrt_cmd = 'gdalbuildvrt'
    if sys.platform == 'win32':
        gdalbuildvrt_path = r"C:\Program Files\GDAL\gdalbuildvrt.exe"
        if Path(gdalbuildvrt_path).exists():
            gdalbuildvrt_cmd = gdalbuildvrt_path

    vrt_cmd = [
        gdalbuildvrt_cmd,
        '-resolution', 'highest',  # Use highest resolution from input tiles
        '-r', resampling,  # Resampling algorithm for better quality
        '-te', str(min_lon), str(min_lat), str(max_lon), str(max_lat),
        '-a_srs', 'EPSG:4326',
        '-input_file_list', str(tile_list_file),
        str(output_vrt)
    ]

    try:
        import time
        start_time = time.time()

        result = subprocess.run(vrt_cmd, capture_output=True, text=True, env=setup_gdal_env(), shell=False)

        elapsed = time.time() - start_time

        if result.returncode == 0:
            if verbose:
                print(f" Done! ({elapsed:.2f}s)")
                print(f"✅ VRT berhasil dibuat: {output_vrt}\n")
            return True
        else:
            if verbose:
                print(f" Failed!")
                print(f"❌ Error membuat VRT:")
                print(result.stderr)
            return False

    except FileNotFoundError as e:
        if verbose:
            print(f"❌ GDAL tidak ditemukan!")
            print(f"   Error: {str(e)}")
        return False
    except Exception as e:
        if verbose:
            print(f"❌ Error: {str(e)}")
        return False


def merge_to_geotiff(vrt_file: Path, output_tif: Path, verbose=True, compress=False, resampling='cubic'):
    """Convert VRT ke GeoTIFF

    Args:
        vrt_file: Input VRT file
        output_tif: Output GeoTIFF file
        verbose: Show progress
        compress: Use LZW compression (slower but smaller file, keeps CPU busy)
        resampling: Resampling algorithm - 'nearest', 'bilinear', 'cubic', 'lanczos' (default: cubic)
    """
    if not vrt_file.exists():
        if verbose:
            print(f"❌ VRT file tidak ditemukan: {vrt_file}")
        return False

    if verbose:
        print(f"🔨 Merging ke GeoTIFF...")
        print(f"   Output: {output_tif}")
        print(f"   Resampling: {resampling}")
        if compress:
            print(f"   Compression: LZW (slower but smaller, max CPU usage)")
        else:
            print(f"   Compression: None (fastest)")
        print()

    # Use full path on Windows for better compatibility
    gdal_translate_cmd = 'gdal_translate'
    if sys.platform == 'win32':
        gdal_translate_path = r"C:\Program Files\GDAL\gdal_translate.exe"
        if Path(gdal_translate_path).exists():
            gdal_translate_cmd = gdal_translate_path

    # ===== OPTIMIZED FOR SPEED OR SIZE =====
    # COMPRESS=NONE: 10-20x faster than LZW (larger file but much faster)
    # COMPRESS=LZW: Slower but 80% smaller file, keeps CPU at 100%
    # NUM_THREADS=ALL_CPUS: Use all CPU cores
    # BLOCKXSIZE/BLOCKYSIZE: Optimized for tile processing
    # BIGTIFF=YES: Always use BigTIFF for multi-batch processing
    # -r: Resampling algorithm for better quality
    translate_cmd = [
        gdal_translate_cmd,
        '-of', 'GTiff',
        '-r', resampling,                # Resampling algorithm
        '-co', 'COMPRESS=LZW' if compress else 'COMPRESS=NONE',
        '-co', 'TILED=YES',              # Tiled output for better performance
        '-co', 'BLOCKXSIZE=512',         # Optimized block size
        '-co', 'BLOCKYSIZE=512',         # Optimized block size
        '-co', 'BIGTIFF=YES',            # Always use BigTIFF for safety
        '-co', 'NUM_THREADS=ALL_CPUS',   # Multi-threaded processing
        str(vrt_file),
        str(output_tif)
    ]

    try:
        # Run subprocess with/without verbose output
        if verbose:
            # Show progress with subprocess
            process = subprocess.Popen(
                translate_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=setup_gdal_env(),
                shell=False
            )

            # Print output in real-time
            for line in process.stdout:
                if line.strip():
                    print(f"   {line.strip()}")

            process.wait()
        else:
            # Silent mode for parallel processing
            process = subprocess.run(
                translate_cmd,
                capture_output=True,
                text=True,
                env=setup_gdal_env(),
                shell=False
            )

        returncode = process.returncode if verbose else process.returncode

        if returncode == 0:
            if verbose:
                file_size_mb = output_tif.stat().st_size / (1024 * 1024)
                print(f"\n✅ GeoTIFF berhasil dibuat!")
                print(f"   File: {output_tif}")
                print(f"   Size: {file_size_mb:.2f} MB")
            return True
        else:
            if verbose:
                print(f"❌ Error membuat GeoTIFF")
            return False

    except Exception as e:
        if verbose:
            print(f"❌ Error: {str(e)}")
        return False


def process_single_batch(batch_info):
    """
    Process single batch ke GeoTIFF - untuk parallel processing
    Returns: (success, batch_num, output_file, error_message)
    """
    batch = batch_info['batch']
    batch_num = batch['batch_num']
    output_dir = batch_info['output_dir']
    compress = batch_info.get('compress', False)
    resampling = batch_info.get('resampling', 'cubic')

    try:
        # Create VRT untuk single batch
        vrt_file = output_dir / f"batch_{batch_num:03d}.vrt"
        output_tif = output_dir / f"merged_batch_{batch_num:03d}.tif"

        # Create VRT (silent mode)
        if not create_vrt([batch], vrt_file, verbose=False, resampling=resampling):
            return (False, batch_num, None, "Failed to create VRT")

        # Merge to GeoTIFF (silent mode)
        if not merge_to_geotiff(vrt_file, output_tif, verbose=False, compress=compress, resampling=resampling):
            return (False, batch_num, None, "Failed to merge to GeoTIFF")

        # Clean up VRT and tile list
        if vrt_file.exists():
            vrt_file.unlink()

        tile_list = output_dir / f"tile_list_{vrt_file.stem}.txt"
        if tile_list.exists():
            tile_list.unlink()

        return (True, batch_num, output_tif, None)

    except Exception as e:
        return (False, batch_num, None, str(e))


def process_batches_parallel(batches, output_dir, max_workers=None, compress=False, resampling='cubic'):
    """
    Process multiple batches in parallel
    max_workers: Number of parallel processes (default: CPU count for I/O-bound tasks)
    compress: Use LZW compression
    resampling: Resampling algorithm
    """
    if max_workers is None:
        # Use all CPU cores for I/O-bound tasks (merge is I/O heavy)
        # GDAL already uses threading internally, so we maximize parallelism at batch level
        max_workers = multiprocessing.cpu_count()

    print(f"🚀 Processing {len(batches)} batches in parallel (max {max_workers} workers)...\n")

    # Prepare batch info
    batch_infos = [
        {'batch': batch, 'output_dir': output_dir, 'compress': compress, 'resampling': resampling}
        for batch in batches
    ]

    results = []
    completed = 0

    # Process in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_single_batch, info): info['batch']['batch_num']
            for info in batch_infos
        }

        # Process as they complete
        for future in as_completed(futures):
            batch_num = futures[future]
            completed += 1

            try:
                success, b_num, output_file, error = future.result()
                results.append({
                    'batch_num': b_num,
                    'success': success,
                    'output_file': output_file,
                    'error': error
                })

                if success:
                    file_size_mb = output_file.stat().st_size / (1024 * 1024)
                    print(f"✅ [{completed}/{len(batches)}] Batch {b_num:03d} selesai - {file_size_mb:.2f} MB")
                else:
                    print(f"❌ [{completed}/{len(batches)}] Batch {b_num:03d} gagal: {error}")

            except Exception as e:
                print(f"❌ [{completed}/{len(batches)}] Batch {batch_num:03d} error: {str(e)}")
                results.append({
                    'batch_num': batch_num,
                    'success': False,
                    'output_file': None,
                    'error': str(e)
                })

    print()
    return results


def merge_single_batch(batch_num, georef_dir, merged_dir, compress=False, resampling='cubic'):
    """Merge a single batch to individual GeoTIFF file

    Args:
        batch_num: Batch number to merge
        georef_dir: Georeferenced directory path
        merged_dir: Merged output directory path
        compress: Use LZW compression
        resampling: Resampling algorithm

    Returns:
        tuple: (success: bool, output_file: Path, error_message: str)
    """
    # Check if batch is ready
    batch_info = check_batch_ready(batch_num, georef_dir)
    if not batch_info:
        return (False, None, f"Batch {batch_num} not ready or not found")

    # Check if already merged
    output_file = merged_dir / f"merged_batch_{batch_num:03d}.tif"
    if output_file.exists():
        return (True, output_file, "Already exists (skipped)")

    try:
        # Create VRT for this batch
        vrt_file = merged_dir / f"batch_{batch_num:03d}.vrt"

        if not create_vrt([batch_info], vrt_file, verbose=False, resampling=resampling):
            return (False, None, "VRT creation failed")

        # Merge to GeoTIFF
        if not merge_to_geotiff(vrt_file, output_file, verbose=False, compress=compress, resampling=resampling):
            return (False, None, "GeoTIFF conversion failed")

        # Clean up VRT and tile list
        if vrt_file.exists():
            vrt_file.unlink()

        tile_list = merged_dir / f"tile_list_{vrt_file.stem}.txt"
        if tile_list.exists():
            tile_list.unlink()

        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        return (True, output_file, f"{file_size_mb:.1f} MB")

    except Exception as e:
        return (False, None, str(e))


def load_watch_progress(merged_dir):
    """Load watch mode progress from JSON file"""
    progress_file = merged_dir / "watch_mode_progress.json"
    if progress_file.exists():
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'batches_requested': [],
        'merged': [],
        'waiting': [],
        'failed': [],
        'last_update': None,
        'check_interval': 30,
        'start_time': None
    }


def save_watch_progress(progress_data, merged_dir):
    """Save watch mode progress to JSON file"""
    merged_dir.mkdir(parents=True, exist_ok=True)
    progress_data['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    progress_file = merged_dir / "watch_mode_progress.json"
    with open(progress_file, 'w') as f:
        json.dump(progress_data, f, indent=2)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global SHUTDOWN_REQUESTED
    print("\n\n⏸️  Shutdown requested... Saving progress...")
    SHUTDOWN_REQUESTED = True


def watch_and_merge(batch_list, georef_dir, merged_dir, check_interval=30, compress=False, parallel=False, max_workers=None, resampling='cubic'):
    """Watch for georeferenced batches and merge automatically

    Args:
        batch_list: List of batch numbers to watch and merge
        georef_dir: Georeferenced directory path
        merged_dir: Merged output directory path
        check_interval: Seconds between checks (default: 30)
        compress: Use LZW compression
        parallel: Merge multiple batches in parallel (default: False)
        max_workers: Max parallel workers (default: CPU count)
        resampling: Resampling algorithm (default: cubic)

    Returns:
        dict: Summary of merging results
    """
    global SHUTDOWN_REQUESTED

    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Set max workers for parallel mode
    if parallel and max_workers is None:
        max_workers = multiprocessing.cpu_count()

    print("=" * 60)
    if parallel:
        print("   GeoTIFF Merger - WATCH MODE (PARALLEL)")
    else:
        print("   GeoTIFF Merger - WATCH MODE")
    print("=" * 60)
    print()

    # Load or create progress
    progress = load_watch_progress(merged_dir)

    # Initialize if first run
    if not progress['start_time']:
        progress['batches_requested'] = sorted(batch_list)
        progress['start_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        progress['check_interval'] = check_interval
        progress['parallel'] = parallel
        progress['max_workers'] = max_workers if parallel else 1

    # Check which batches are already ready
    ready_batches = []
    waiting_batches = []

    for batch_num in progress['batches_requested']:
        if batch_num in progress['merged']:
            continue  # Already merged

        if check_batch_ready(batch_num, georef_dir):
            ready_batches.append(batch_num)
        else:
            waiting_batches.append(batch_num)

    progress['waiting'] = waiting_batches

    print(f"📦 Total batches: {len(progress['batches_requested'])}")
    print()
    print(f"✅ Ready to merge: {len(ready_batches)} batches")
    if ready_batches:
        print(f"   {', '.join(map(str, ready_batches[:10]))}" + (" ..." if len(ready_batches) > 10 else ""))
    print(f"⏳ Waiting: {len(waiting_batches)} batches")
    if waiting_batches:
        print(f"   {', '.join(map(str, waiting_batches[:10]))}" + (" ..." if len(waiting_batches) > 10 else ""))
    print()

    # Merge ready batches immediately
    if ready_batches:
        if parallel:
            print(f"Starting immediate parallel merge for ready batches ({max_workers} workers)...")
        else:
            print("Starting immediate merge for ready batches...")

        if parallel and len(ready_batches) > 1:
            # PARALLEL MERGE
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all merge tasks
                future_to_batch = {
                    executor.submit(merge_single_batch, batch_num, georef_dir, merged_dir, compress, resampling): batch_num
                    for batch_num in ready_batches
                    if not SHUTDOWN_REQUESTED
                }

                # Process results as they complete
                for future in as_completed(future_to_batch):
                    if SHUTDOWN_REQUESTED:
                        break

                    batch_num = future_to_batch[future]
                    try:
                        success, output_file, message = future.result()
                        if success:
                            print(f"✅ Merged batch {batch_num:03d} → {output_file.name} ({message})")
                            progress['merged'].append(batch_num)
                            progress['waiting'] = [b for b in progress['waiting'] if b != batch_num]
                        else:
                            print(f"❌ Failed batch {batch_num:03d}: {message}")
                            progress['failed'].append(batch_num)
                    except Exception as e:
                        print(f"❌ Failed batch {batch_num:03d}: {str(e)}")
                        progress['failed'].append(batch_num)

                    save_watch_progress(progress, merged_dir)
        else:
            # SEQUENTIAL MERGE (original behavior)
            for batch_num in ready_batches:
                if SHUTDOWN_REQUESTED:
                    break

                success, output_file, message = merge_single_batch(batch_num, georef_dir, merged_dir, compress=compress, resampling=resampling)
                if success:
                    print(f"✅ Merged batch {batch_num:03d} → {output_file.name} ({message})")
                    progress['merged'].append(batch_num)
                    progress['waiting'] = [b for b in progress['waiting'] if b != batch_num]
                else:
                    print(f"❌ Failed batch {batch_num:03d}: {message}")
                    progress['failed'].append(batch_num)

                save_watch_progress(progress, merged_dir)

        print()

    # Watch loop for remaining batches
    if progress['waiting'] and not SHUTDOWN_REQUESTED:
        print(f"👀 Watching for new batches... (checking every {check_interval}s)")
        print(f"   Press Ctrl+C to stop safely")
        print()

        while progress['waiting'] and not SHUTDOWN_REQUESTED:
            time.sleep(check_interval)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Checking batches...")

            newly_ready = []
            for batch_num in list(progress['waiting']):
                if SHUTDOWN_REQUESTED:
                    break

                if check_batch_ready(batch_num, georef_dir):
                    newly_ready.append(batch_num)

            if newly_ready:
                if parallel and len(newly_ready) > 1:
                    # PARALLEL MERGE for newly ready batches
                    print(f"✅ New batches ready: {', '.join(map(str, newly_ready))}")
                    print(f"🔨 Merging {len(newly_ready)} batches in parallel...")

                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_batch = {
                            executor.submit(merge_single_batch, batch_num, georef_dir, merged_dir, compress, resampling): batch_num
                            for batch_num in newly_ready
                            if not SHUTDOWN_REQUESTED
                        }

                        for future in as_completed(future_to_batch):
                            if SHUTDOWN_REQUESTED:
                                break

                            batch_num = future_to_batch[future]
                            try:
                                success, output_file, message = future.result()
                                if success:
                                    print(f"✅ Merged batch {batch_num:03d} → {output_file.name} ({message})")
                                    progress['merged'].append(batch_num)
                                    if batch_num in progress['waiting']:
                                        progress['waiting'].remove(batch_num)
                                else:
                                    print(f"❌ Failed batch {batch_num:03d}: {message}")
                                    progress['failed'].append(batch_num)
                                    if batch_num in progress['waiting']:
                                        progress['waiting'].remove(batch_num)
                            except Exception as e:
                                print(f"❌ Failed batch {batch_num:03d}: {str(e)}")
                                progress['failed'].append(batch_num)
                                if batch_num in progress['waiting']:
                                    progress['waiting'].remove(batch_num)

                            save_watch_progress(progress, merged_dir)
                else:
                    # SEQUENTIAL MERGE for newly ready batches
                    for batch_num in newly_ready:
                        if SHUTDOWN_REQUESTED:
                            break

                        print(f"✅ New batch ready: {batch_num:03d}")
                        print(f"🔨 Merging batch {batch_num:03d}...")

                        success, output_file, message = merge_single_batch(batch_num, georef_dir, merged_dir, compress=compress, resampling=resampling)
                        if success:
                            print(f"✅ Merged batch {batch_num:03d} → {output_file.name} ({message})")
                            progress['merged'].append(batch_num)
                            progress['waiting'].remove(batch_num)
                        else:
                            print(f"❌ Failed batch {batch_num:03d}: {message}")
                            progress['failed'].append(batch_num)
                            progress['waiting'].remove(batch_num)

                        save_watch_progress(progress, merged_dir)

                print(f"⏳ Waiting: {len(progress['waiting'])} batches remaining")
                print()
            else:
                print(f"⏳ Waiting: {len(progress['waiting'])} batches remaining")

    # Final summary
    save_watch_progress(progress, merged_dir)

    progress_file = merged_dir / "watch_mode_progress.json"
    print("\n" + "=" * 60)
    if SHUTDOWN_REQUESTED:
        print("⏸️  WATCH MODE STOPPED")
    else:
        print("✅ ALL BATCHES COMPLETED!")
    print("=" * 60)
    print(f"\n✅ Total merged: {len(progress['merged'])} batches")
    if progress['failed']:
        print(f"❌ Failed: {len(progress['failed'])} batches")
        print(f"   {', '.join(map(str, progress['failed']))}")
    print(f"📁 Output directory: {merged_dir.absolute()}/")
    print(f"💾 Progress saved: {progress_file}")
    print()

    return progress


def write_merge_log(batches, output_file, log_file):
    """Write merge log"""
    with open(log_file, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("GeoTIFF Merge Log\n")
        f.write("=" * 60 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Output file: {output_file}\n")
        f.write(f"\nBatches merged: {len(batches)}\n")
        f.write("\nBatch details:\n")

        total_tiles = 0
        for batch in batches:
            f.write(f"  Batch {batch['batch_num']:03d}: {batch['tiles_count']:,} tiles\n")
            total_tiles += batch['tiles_count']

        f.write(f"\nTotal tiles: {total_tiles:,}\n")


def main():
    parser = argparse.ArgumentParser(description='GeoTIFF Merger - Optimized for Speed')
    parser.add_argument('--georef-folder', type=str, help='Folder georeferenced yang akan di-merge')
    parser.add_argument('--output', type=str, help='Custom output folder untuk hasil merged')
    parser.add_argument('--batches', help='Comma-separated batch numbers (e.g., 1,2,5,10)')
    parser.add_argument('--batch-range', help='Batch range (e.g., 1-20)')
    parser.add_argument('--list', action='store_true', help='List available batches')
    parser.add_argument('--list-folders', action='store_true', help='List available georef folders')
    parser.add_argument('--parallel', action='store_true', help='Process multiple batches in parallel (faster for multiple batches)')
    parser.add_argument('--workers', type=int, default=None, help='Number of parallel workers (default: CPU count)')
    parser.add_argument('--single-file', action='store_true', help='Merge all batches into single GeoTIFF (slower but one file)')
    parser.add_argument('--compress', action='store_true', help='Use LZW compression (slower but smaller file, maximizes CPU usage)')
    parser.add_argument('--resampling', type=str, default='cubic', choices=['nearest', 'bilinear', 'cubic', 'lanczos'], help='Resampling algorithm (default: cubic for best quality)')
    parser.add_argument('--watch', action='store_true', help='Watch mode: auto-merge batches as they become ready')
    parser.add_argument('--check-interval', type=int, default=30, help='Watch mode: seconds between checks (default: 30)')
    parser.add_argument('--resume', action='store_true', help='Resume previous watch mode session')

    args = parser.parse_args()

    print("=" * 60)
    print("   GeoTIFF Merger - OPTIMIZED")
    print("=" * 60)
    print()

    # List folders mode
    if args.list_folders:
        folders = list_available_georef_folders()
        if not folders:
            print("❌ Tidak ada folder georeferenced ditemukan!")
            return

        print(f"📁 Available Georeferenced Folders ({len(folders)}):\n")
        for folder in folders:
            print(f"   📂 {folder['name']}: {folder['batch_count']} batches, {folder['total_tiles']:,} tiles")
        print()
        return

    # Determine georef directory
    georef_dir = None
    if args.georef_folder:
        georef_dir = Path(args.georef_folder)
        if not georef_dir.exists():
            print(f"❌ Folder '{args.georef_folder}' tidak ditemukan!")
            return
    else:
        # Interactive folder selection
        folders = list_available_georef_folders()

        if not folders:
            print("❌ Tidak ada folder georeferenced ditemukan!")
            print(f"   Jalankan georeference_batch.py terlebih dahulu")
            return
        elif len(folders) == 1:
            # Only one folder, use it automatically
            georef_dir = folders[0]['path']
            print(f"📂 Menggunakan folder: {georef_dir.name} ({folders[0]['batch_count']} batches)")
        else:
            # Multiple folders, ask user to choose
            print(f"📁 Available Georeferenced Folders ({len(folders)}):\n")
            for i, folder in enumerate(folders, 1):
                print(f"   {i}. {folder['name']}: {folder['batch_count']} batches, {folder['total_tiles']:,} tiles")
            print()

            choice = input("Pilih folder (nomor atau nama): ").strip()

            # Try as number first
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(folders):
                    georef_dir = folders[idx]['path']
                else:
                    print("❌ Nomor tidak valid")
                    return
            except ValueError:
                # Try as folder name
                folder = next((f for f in folders if f['name'] == choice), None)
                if folder:
                    georef_dir = folder['path']
                else:
                    print(f"❌ Folder '{choice}' tidak ditemukan")
                    return

    # Determine output directory
    if args.output:
        merged_dir = Path(args.output)
        print(f"📂 Georef Folder: {georef_dir.absolute()}")
        print(f"📂 Output Folder (custom): {merged_dir.absolute()}")
    else:
        # Ask for custom output folder name
        print(f"\n📂 Georef Folder: {georef_dir.absolute()}")
        default_output = str(georef_dir) + DEFAULT_MERGED_SUFFIX
        print(f"📂 Default Output: {Path(default_output).absolute()}")
        print()

        output_input = input(f"📁 Nama folder output (Enter untuk default): ").strip()

        if output_input:
            merged_dir = Path(output_input)
            print(f"📂 Output Folder: {merged_dir.absolute()}")
        else:
            merged_dir = Path(default_output)
            print(f"📂 Output Folder: {merged_dir.absolute()}")

    print()

    # WATCH MODE or RESUME
    if args.watch or args.resume:
        # Get batch list from args or progress file
        if args.resume:
            # Load from progress file
            progress = load_watch_progress(merged_dir)
            if not progress['batches_requested']:
                print("❌ No previous watch session found")
                print(f"   Start a new watch session with --watch")
                return
            batch_list = progress['batches_requested']
        else:
            # Get from command line args
            batch_filter = None

            if args.batches:
                batch_filter = [int(b.strip()) for b in args.batches.split(',')]
            elif args.batch_range:
                try:
                    start, end = map(int, args.batch_range.split('-'))
                    batch_filter = list(range(start, end + 1))
                except:
                    print("❌ Invalid batch range format")
                    return
            else:
                print("❌ Watch mode requires --batches or --batch-range")
                return

            batch_list = batch_filter

        # Start watch and merge
        watch_and_merge(batch_list,
                        georef_dir,
                        merged_dir,
                        check_interval=args.check_interval,
                        compress=args.compress,
                        parallel=args.parallel,
                        max_workers=args.workers,
                        resampling=args.resampling)
        return

    # NORMAL MODE: Continue with existing logic
    # Find batches
    batch_filter = None

    if args.batches:
        batch_filter = [int(b.strip()) for b in args.batches.split(',')]
    elif args.batch_range:
        try:
            start, end = map(int, args.batch_range.split('-'))
            batch_filter = list(range(start, end + 1))
        except:
            print("❌ Invalid batch range format")
            return

    batches = find_georeferenced_batches(georef_dir, batch_filter)

    if not batches:
        print("❌ Tidak ada georeferenced batches ditemukan!")
        print(f"   Jalankan georeference_batch.py terlebih dahulu")
        return

    # List mode
    if args.list:
        print(f"📋 Available Georeferenced Batches ({len(batches)}):\n")
        for batch in batches:
            print(f"   Batch {batch['batch_num']:03d}: {batch['tiles_count']:,} tiles")
        print()
        return

    # Show batches to merge
    print(f"📦 Batches to merge: {len(batches)}\n")
    total_tiles = 0
    for batch in batches:
        print(f"   Batch {batch['batch_num']:03d}: {batch['tiles_count']:,} tiles")
        total_tiles += batch['tiles_count']

    print(f"\n   Total tiles: {total_tiles:,}")

    # Show processing mode
    cpu_count = multiprocessing.cpu_count()
    if args.parallel and len(batches) > 1:
        workers = args.workers if args.workers else cpu_count
        print(f"\n⚡ Mode: PARALLEL processing ({workers} workers, {cpu_count} CPU cores)")
        print(f"   Setiap batch akan di-process terpisah secara parallel")
        if HAS_PSUTIL:
            ram_gb = psutil.virtual_memory().total / (1024**3)
            print(f"   RAM: {ram_gb:.1f} GB available")
    elif args.single_file:
        print(f"\n📄 Mode: Single file output")
        print(f"   Semua batches akan di-merge jadi 1 GeoTIFF")
    else:
        print(f"\n📄 Mode: Sequential processing")
        print(f"   Processing batch satu per satu")

    confirm = input("\n✅ Lanjutkan merge? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ Merge dibatalkan")
        return

    print()

    # Create output directory
    merged_dir.mkdir(parents=True, exist_ok=True)

    start_time = datetime.now()

    # PARALLEL MODE: Process batches in parallel
    if args.parallel and len(batches) > 1:
        results = process_batches_parallel(batches, merged_dir, args.workers, args.compress, args.resampling)

        # Summary
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]

        print("=" * 60)
        print("✅ PARALLEL PROCESSING SELESAI!")
        print("=" * 60)
        print(f"\nBerhasil: {len(successful)}/{len(batches)} batches")

        if successful:
            print(f"\nFile output:")
            for result in sorted(successful, key=lambda x: x['batch_num']):
                file_size_mb = result['output_file'].stat().st_size / (1024 * 1024)
                print(f"  - Batch {result['batch_num']:03d}: {result['output_file'].name} ({file_size_mb:.2f} MB)")

        if failed:
            print(f"\n❌ Gagal: {len(failed)} batches")
            for result in failed:
                print(f"  - Batch {result['batch_num']:03d}: {result['error']}")

    # SINGLE FILE MODE: Merge all to one GeoTIFF
    else:
        # Create VRT
        vrt_file = merged_dir / "mosaic.vrt"
        if not create_vrt(batches, vrt_file, resampling=args.resampling):
            return

        # Generate unique output filename
        base_name = OUTPUT_GEOTIFF.replace(".tif", "").replace(".TIF", "")
        output_geotiff = get_unique_filename(merged_dir, base_name, ".tif")

        print(f"📁 Output file: {output_geotiff.name}\n")

        # Merge to GeoTIFF with optional compression
        if merge_to_geotiff(vrt_file, output_geotiff, compress=args.compress, resampling=args.resampling):
            # Write log
            log_file = merged_dir / f"merge_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            write_merge_log(batches, output_geotiff, log_file)

            print("\n" + "=" * 60)
            print("✅ MERGE SELESAI!")
            print("=" * 60)
            print(f"\nFile output:")
            print(f"  - VRT: {vrt_file}")
            print(f"  - GeoTIFF: {output_geotiff}")
            print(f"  - Log: {log_file}")
        else:
            print("\n❌ Gagal membuat GeoTIFF!")

    # Show elapsed time
    elapsed = datetime.now() - start_time
    minutes = int(elapsed.total_seconds() // 60)
    seconds = int(elapsed.total_seconds() % 60)
    print(f"\n⏱️  Waktu proses: {minutes} menit {seconds} detik")
    print()
    print("Anda bisa membuka GeoTIFF di QGIS atau software GIS lainnya.")


if __name__ == "__main__":
    main()
