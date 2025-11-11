#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Async Batch Tile Downloader - High Performance Version
Download tiles dari BPN menggunakan asyncio + aiohttp untuk maksimal speed
Target: 500-1000 concurrent connections untuk ultra-fast download
"""

import os
import sys
import json
import time
import argparse
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Fix Windows terminal encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Progress bar
try:
    from tqdm.asyncio import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("⚠️  Install tqdm untuk progress bar: pip install tqdm")

# ============= KONFIGURASI =============
BATCH_SIZE = 50  # 50x50 tiles per batch
MAX_CONCURRENT = 500  # Concurrent downloads (bisa sampai 1000 untuk koneksi cepat)
RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.5  # Shorter delay for async
CHUNK_SIZE = 16384  # 16KB chunks
PROGRESS_DETAIL_LIMIT = 20
TIMEOUT_CONNECT = 10
TIMEOUT_READ = 30
BASE_URL = "https://petadasar.atrbpn.go.id/wms/?d={x}/{y}/{z}/{variant}"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Referer': 'https://www.transmigrasi.go.id/'
}

# Directories
TILES_DIR = Path("tiles")
PROGRESS_FILE = TILES_DIR / "progress_async.json"
FAILED_FILE = TILES_DIR / "failed_tiles_async.json"


def format_time(seconds):
    """Format seconds to human readable time"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds/60)}m {int(seconds%60)}s"
    else:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h {mins}m"


def format_size(bytes_size):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def calculate_batches(x_start, x_end, y_start, y_end, batch_size=BATCH_SIZE):
    """Calculate all batches needed"""
    batches = []
    batch_num = 1

    x_range = x_end - x_start + 1
    y_range = y_end - y_start + 1

    x_batches = (x_range + batch_size - 1) // batch_size
    y_batches = (y_range + batch_size - 1) // batch_size

    for y_batch_idx in range(y_batches):
        for x_batch_idx in range(x_batches):
            batch_x_start = x_start + (x_batch_idx * batch_size)
            batch_x_end = min(batch_x_start + batch_size - 1, x_end)

            batch_y_start = y_start + (y_batch_idx * batch_size)
            batch_y_end = min(batch_y_start + batch_size - 1, y_end)

            batch_info = {
                'batch_num': batch_num,
                'x_start': batch_x_start,
                'x_end': batch_x_end,
                'y_start': batch_y_start,
                'y_end': batch_y_end,
                'tiles_count': (batch_x_end - batch_x_start + 1) * (batch_y_end - batch_y_start + 1)
            }
            batches.append(batch_info)
            batch_num += 1

    return batches


def load_progress():
    """Load progress from JSON"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None


def save_progress(progress_data):
    """Save progress with optimized batch details"""
    TILES_DIR.mkdir(parents=True, exist_ok=True)
    progress_data['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Keep only recent batch details
    if len(progress_data['batch_details']) > PROGRESS_DETAIL_LIMIT:
        batch_keys = sorted(progress_data['batch_details'].keys(), key=int)
        recent_keys = batch_keys[-PROGRESS_DETAIL_LIMIT:]
        progress_data['batch_details'] = {
            k: progress_data['batch_details'][k] for k in recent_keys
        }

    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress_data, f, indent=2)


def load_failed_tiles():
    """Load failed tiles"""
    if FAILED_FILE.exists():
        try:
            with open(FAILED_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_failed_tiles(failed_data):
    """Save failed tiles"""
    with open(FAILED_FILE, 'w') as f:
        json.dump(failed_data, f, indent=2)


async def download_tile(session, semaphore, x, y, zoom, variant, output_path, retry=0):
    """Async download single tile with streaming"""
    url = BASE_URL.format(x=x, y=y, z=zoom, variant=variant)

    # Skip if exists
    if output_path.exists():
        return {'status': 'skipped', 'x': x, 'y': y}

    async with semaphore:
        try:
            timeout = aiohttp.ClientTimeout(connect=TIMEOUT_CONNECT, total=TIMEOUT_READ)
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    # Stream to file
                    total_size = 0
                    async with aiofiles.open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                            await f.write(chunk)
                            total_size += len(chunk)

                    return {'status': 'success', 'x': x, 'y': y, 'size': total_size}
                else:
                    error_msg = f"HTTP {response.status}"
                    if retry < RETRY_ATTEMPTS:
                        await asyncio.sleep(RETRY_DELAY * (retry + 1))
                        return await download_tile(session, semaphore, x, y, zoom, variant, output_path, retry + 1)
                    return {'status': 'failed', 'x': x, 'y': y, 'error': error_msg, 'retries': retry}

        except asyncio.TimeoutError:
            error_msg = "Timeout"
            if retry < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_DELAY * (retry + 1))
                return await download_tile(session, semaphore, x, y, zoom, variant, output_path, retry + 1)
            return {'status': 'failed', 'x': x, 'y': y, 'error': error_msg, 'retries': retry}

        except Exception as e:
            error_msg = str(e)
            if retry < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_DELAY * (retry + 1))
                return await download_tile(session, semaphore, x, y, zoom, variant, output_path, retry + 1)
            return {'status': 'failed', 'x': x, 'y': y, 'error': error_msg, 'retries': retry}


async def download_batch(batch_info, zoom, variant, progress_data, failed_tiles_data, max_concurrent=MAX_CONCURRENT):
    """Async download all tiles in a batch"""
    batch_num = batch_info['batch_num']
    batch_dir = TILES_DIR / f"tiles_batch_{batch_num:03d}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    # Generate tiles list
    tiles_to_download = []
    for x in range(batch_info['x_start'], batch_info['x_end'] + 1):
        for y in range(batch_info['y_start'], batch_info['y_end'] + 1):
            filename = f"tile_{zoom}_{x}_{y}.jpg"
            output_path = batch_dir / filename
            tiles_to_download.append((x, y, output_path))

    total_tiles = len(tiles_to_download)
    success_count = 0
    failed_count = 0
    skipped_count = 0
    total_size = 0
    failed_list = []

    start_time = time.time()

    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrent)

    # Create client session with connection pooling
    connector = aiohttp.TCPConnector(
        limit=max_concurrent,
        limit_per_host=max_concurrent,
        ttl_dns_cache=300
    )

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        # Create tasks
        tasks = [
            download_tile(session, semaphore, x, y, zoom, variant, path)
            for x, y, path in tiles_to_download
        ]

        # Progress bar
        pbar = None
        if HAS_TQDM:
            pbar = tqdm(total=total_tiles, desc=f"Batch {batch_num}", unit="tiles")

        try:
            # Execute all tasks with gather for better cancellation handling
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                # Handle cancellation
                if isinstance(result, asyncio.CancelledError):
                    if HAS_TQDM:
                        pbar.update(1)
                    continue

                # Handle other exceptions
                if isinstance(result, Exception):
                    failed_count += 1
                    if HAS_TQDM:
                        pbar.update(1)
                    continue

                # Handle normal results
                if result['status'] == 'success':
                    success_count += 1
                    total_size += result.get('size', 0)
                elif result['status'] == 'skipped':
                    skipped_count += 1
                elif result['status'] == 'failed':
                    failed_count += 1
                    failed_list.append({
                        'x': result['x'],
                        'y': result['y'],
                        'error': result['error'],
                        'retries': result['retries']
                    })

                if HAS_TQDM:
                    pbar.update(1)
                    pbar.set_postfix({
                        'OK': success_count,
                        'Skip': skipped_count,
                        'Fail': failed_count
                    })

        except KeyboardInterrupt:
            # Cancel all pending tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

            # Wait for cancellation to complete
            await asyncio.gather(*tasks, return_exceptions=True)

            # Re-raise to propagate to main
            raise

        finally:
            # Ensure progress bar is closed
            if HAS_TQDM and pbar:
                pbar.close()

            # Ensure all tasks are cleaned up
            for task in tasks:
                if not task.done():
                    task.cancel()

    elapsed_time = time.time() - start_time

    # Save failed tiles
    if failed_list:
        batch_key = f"batch_{batch_num:03d}"
        failed_tiles_data[batch_key] = failed_list
        save_failed_tiles(failed_tiles_data)

    # Update progress
    batch_stats = {
        'status': 'completed',
        'tiles': total_tiles,
        'success': success_count,
        'skipped': skipped_count,
        'failed': failed_count,
        'time_seconds': elapsed_time,
        'size_bytes': total_size
    }

    progress_data['batch_details'][str(batch_num)] = batch_stats
    progress_data['completed_batches'].append(batch_num)
    progress_data['tiles_downloaded'] += success_count
    progress_data['tiles_failed'] += failed_count

    # Calculate ETA
    completed_batches = len(progress_data['completed_batches'])
    total_batches = progress_data['total_batches']
    avg_time_per_batch = (time.time() - datetime.fromisoformat(progress_data['start_time']).timestamp()) / completed_batches
    remaining_batches = total_batches - completed_batches
    eta_seconds = remaining_batches * avg_time_per_batch
    progress_data['estimated_completion'] = (datetime.now() + timedelta(seconds=eta_seconds)).strftime("%Y-%m-%d %H:%M:%S")
    progress_data['avg_time_per_batch'] = avg_time_per_batch

    save_progress(progress_data)

    # Print summary
    print(f"\n✅ Batch {batch_num}/{total_batches} selesai!")
    print(f"   Sukses: {success_count} | Skipped: {skipped_count} | Gagal: {failed_count}")
    print(f"   Waktu: {format_time(elapsed_time)} | Size: {format_size(total_size)}")
    print(f"   Speed: {total_tiles/elapsed_time:.1f} tiles/s")
    print(f"   Progress: {completed_batches}/{total_batches} batches ({completed_batches*100//total_batches}%)")
    print(f"   ETA: {format_time(eta_seconds)} (selesai ~{progress_data['estimated_completion'].split()[1]})")
    print()

    return batch_stats


async def main_async(progress, failed_tiles, config, batches, args, concurrent_limit):
    """Main async download loop with proper task cleanup"""
    try:
        for batch in batches:
            # Skip completed batches
            if batch['batch_num'] in progress['completed_batches']:
                continue

            progress['current_batch'] = batch['batch_num']
            save_progress(progress)

            await download_batch(batch, config['zoom'], config['variant'], progress, failed_tiles, concurrent_limit)

        # Final summary
        print("\n" + "=" * 60)
        print("✅ SEMUA BATCH SELESAI!")
        print("=" * 60)
        print(f"Total batches: {len(progress['completed_batches'])}/{progress['total_batches']}")
        print(f"Total tiles downloaded: {progress['tiles_downloaded']:,}")
        print(f"Total tiles failed: {progress['tiles_failed']:,}")
        print()
        print(f"📁 Tiles disimpan di: {TILES_DIR.absolute()}/")
        if progress['tiles_failed'] > 0:
            print(f"⚠️  Failed tiles list: {FAILED_FILE}")
        print()

    except KeyboardInterrupt:
        print("\n\n⏸️  Download di-pause")

        # Cancel all pending tasks gracefully
        current_task = asyncio.current_task()
        pending_tasks = [task for task in asyncio.all_tasks()
                        if task is not current_task and not task.done()]

        if pending_tasks:
            print(f"   Membatalkan {len(pending_tasks)} pending tasks...")
            for task in pending_tasks:
                task.cancel()

            # Wait for all cancellations to complete
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        print(f"   Progress tersimpan di: {PROGRESS_FILE}")
        print()

    except Exception as e:
        # Handle unexpected errors
        print(f"\n❌ Error tidak terduga: {e}")

        # Still cleanup pending tasks
        current_task = asyncio.current_task()
        pending_tasks = [task for task in asyncio.all_tasks()
                        if task is not current_task and not task.done()]

        if pending_tasks:
            for task in pending_tasks:
                task.cancel()
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        raise


def main():
    parser = argparse.ArgumentParser(description='BPN Async Tile Downloader (High Performance)')
    parser.add_argument('--resume', action='store_true', help='Resume dari progress terakhir')
    parser.add_argument('--concurrent', type=int, default=MAX_CONCURRENT, help=f'Max concurrent downloads (default: {MAX_CONCURRENT})')

    args = parser.parse_args()

    print("=" * 60)
    print("   BPN Async Tile Downloader (TURBO MODE)")
    print("=" * 60)
    print()

    # Check for resume
    progress = load_progress()
    failed_tiles = load_failed_tiles()

    if args.resume and progress:
        print("📂 Melanjutkan download dari progress terakhir...")
        config = progress['config']
        x_start = config['x_start']
        x_end = config['x_end']
        y_start = config['y_start']
        y_end = config['y_end']
        zoom = config['zoom']
        variant = config['variant']

        print(f"   Range: X[{x_start}-{x_end}], Y[{y_start}-{y_end}], Zoom {zoom}")
        print(f"   Completed: {len(progress['completed_batches'])}/{progress['total_batches']} batches")
        print()

    else:
        # Get user input
        print("📌 Input koordinat tiles:")
        print()

        x_start = int(input("X Start: "))
        x_end = int(input("X End: "))
        y_start = int(input("Y Start: "))
        y_end = int(input("Y End: "))
        zoom = int(input("Zoom Level: "))
        variant = int(input("Variant (default 2): ") or "2")

        # Calculate batches
        batches = calculate_batches(x_start, x_end, y_start, y_end)
        total_tiles = (x_end - x_start + 1) * (y_end - y_start + 1)

        print("\n" + "=" * 60)
        print("📋 Ringkasan:")
        print("=" * 60)
        print(f"  X Range: {x_start} - {x_end} ({x_end - x_start + 1} tiles)")
        print(f"  Y Range: {y_start} - {y_end} ({y_end - y_start + 1} tiles)")
        print(f"  Zoom: {zoom} | Variant: {variant}")
        print(f"  Total tiles: {total_tiles:,}")
        print(f"  Batch size: {BATCH_SIZE}x{BATCH_SIZE} = {BATCH_SIZE*BATCH_SIZE:,} tiles/batch")
        print(f"  Total batches: {len(batches)}")
        print(f"  Max concurrent: {args.concurrent}")
        print("=" * 60)

        confirm = input("\n✅ Lanjutkan download? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Download dibatalkan")
            return

        print()

        # Initialize progress
        progress = {
            'total_tiles': total_tiles,
            'total_batches': len(batches),
            'completed_batches': [],
            'current_batch': None,
            'tiles_downloaded': 0,
            'tiles_failed': 0,
            'start_time': datetime.now().isoformat(),
            'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'config': {
                'x_start': x_start,
                'x_end': x_end,
                'y_start': y_start,
                'y_end': y_end,
                'zoom': zoom,
                'variant': variant,
                'batch_size': BATCH_SIZE,
                'max_concurrent': args.concurrent
            },
            'batch_details': {}
        }
        save_progress(progress)

    # Calculate batches
    config = progress['config']
    batches = calculate_batches(
        config['x_start'],
        config['x_end'],
        config['y_start'],
        config['y_end']
    )

    # Use concurrent limit from args or config
    concurrent_limit = args.concurrent if args.concurrent else config.get('max_concurrent', MAX_CONCURRENT)

    print(f"🚀 Starting async download with {concurrent_limit} concurrent connections...")
    print()

    # Run async event loop
    if sys.platform == 'win32':
        # Windows requires specific event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main_async(progress, failed_tiles, config, batches, args, concurrent_limit))


if __name__ == "__main__":
    main()
