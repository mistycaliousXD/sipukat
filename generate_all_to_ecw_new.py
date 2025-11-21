#!/usr/bin/env python3
"""
Generate Global Mapper script untuk SEMUA file GeoTIFF
Output ke folder: D:\Ayah\sipukat\ECW NEW
"""

import os
import re
from pathlib import Path

# Configuration
INPUT_FOLDER = r"D:\Ayah\sipukat\merged"
OUTPUT_FOLDER = r"D:\Ayah\sipukat\ECW NEW"
OUTPUT_SCRIPT = "batch_convert_ALL_to_ECW_NEW.gms"
FILE_PATTERN = "merged_batch_*.tif"
COMPRESSION_RATIO = 10

# Scan folder untuk semua file yang matching
input_path = Path(INPUT_FOLDER)
all_files = sorted(input_path.glob(FILE_PATTERN))

# Juga include merged_map_*.tif
map_files = sorted(input_path.glob("merged_map*.tif"))
all_files.extend(map_files)
all_files = sorted(set(all_files))  # Remove duplicates and sort

print(f"Total files yang akan diproses: {len(all_files)}")

# Create output folder if not exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
print(f"Output folder: {OUTPUT_FOLDER}")

# Generate script
script_content = f"""// Global Mapper Batch Convert Script (Compatible with v22.1)
// Konversi SEMUA GeoTIFF ke ECW
// Output folder: {OUTPUT_FOLDER}
// Proses SEQUENTIAL (satu per satu, berurutan)
//
// Total files: {len(all_files)}
// Compression ratio: {COMPRESSION_RATIO}:1

// Clear workspace
UNLOAD_ALL

// ===== FILE PROCESSING (SEQUENTIAL) =====
"""

# Add each file
total_size = 0
for i, input_file in enumerate(all_files, 1):
    input_str = str(input_file).replace('/', '\\')
    output_filename = input_file.stem + '.ecw'
    output_str = os.path.join(OUTPUT_FOLDER, output_filename).replace('/', '\\')

    file_size = os.path.getsize(input_file) / (1024 * 1024)
    total_size += file_size

    script_content += f"""
// [{i}/{len(all_files)}] Processing: {input_file.name} ({file_size:.1f} MB)
IMPORT FILENAME="{input_str}"
EXPORT_RASTER FILENAME="{output_str}" TYPE=ECW SPATIAL_RES_METERS=CURRENT COMPRESSION_RATIO={COMPRESSION_RATIO}
UNLOAD_ALL
"""

# Add completion message
script_content += f"""
// ===== PROCESSING COMPLETE =====
// Script selesai - {len(all_files)} files processed
// Total input size: {total_size:.2f} MB (~{total_size/1024:.2f} GB)
// Estimated output size: ~{total_size/COMPRESSION_RATIO:.2f} MB (~{total_size/COMPRESSION_RATIO/1024:.2f} GB)
"""

# Write script
with open(OUTPUT_SCRIPT, 'w', encoding='utf-8') as f:
    f.write(script_content)

print(f"\n[OK] Script generated: {OUTPUT_SCRIPT}")
print(f"\nFiles yang akan diproses:")
for i, f in enumerate(all_files, 1):
    size_mb = os.path.getsize(f) / (1024 * 1024)
    print(f"  {i:3d}. {f.name:50s} ({size_mb:8.2f} MB)")

print(f"\n{'='*70}")
print(f"Total: {len(all_files)} files")
print(f"Total size: {total_size:.2f} MB (~{total_size/1024:.2f} GB)")
print(f"Estimated output: ~{total_size/COMPRESSION_RATIO:.2f} MB (~{total_size/COMPRESSION_RATIO/1024:.2f} GB)")
print(f"Compression ratio: {COMPRESSION_RATIO}:1")
print(f"Output folder: {OUTPUT_FOLDER}")
print(f"{'='*70}")
print(f"\nUntuk run script:")
print(f"  1. Buka Global Mapper")
print(f"  2. File > Run Script")
print(f"  3. Pilih: {os.path.abspath(OUTPUT_SCRIPT)}")
