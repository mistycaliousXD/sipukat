#!/usr/bin/env python3
"""
Generate Global Mapper script untuk file tertentu saja
"""

import os
import re
from pathlib import Path

# Configuration
INPUT_FOLDER = r"D:\Ayah\sipukat\merged"
OUTPUT_SCRIPT = "batch_convert_073_keatas.gms"
FILE_PATTERN = "merged_batch_*.tif"
MIN_NUMBER = 73  # Filter: hanya file dengan nomor >= 73

def extract_number(filename):
    """Extract number dari filename seperti merged_batch_073.tif"""
    match = re.search(r'merged_batch_(\d+)', filename)
    if match:
        return int(match.group(1))
    return 0

# Scan folder untuk file yang matching
input_path = Path(INPUT_FOLDER)
all_files = sorted(input_path.glob(FILE_PATTERN))

# Filter hanya file dengan nomor >= MIN_NUMBER
filtered_files = [f for f in all_files if extract_number(f.name) >= MIN_NUMBER]

print(f"Total files ditemukan: {len(all_files)}")
print(f"Files yang akan diproses (>= {MIN_NUMBER}): {len(filtered_files)}")

# Generate script (Compatible with Global Mapper 22)
script_content = f"""// Global Mapper Batch Convert Script (Compatible with v22.1)
// Konversi GeoTIFF ke ECW untuk file merged_batch_{MIN_NUMBER:03d} ke atas
// Proses SEQUENTIAL (satu per satu, berurutan)
//
// Total files: {len(filtered_files)}

// Clear workspace
UNLOAD_ALL

// ===== FILE PROCESSING (SEQUENTIAL) =====
"""

# Add each file
for i, input_file in enumerate(filtered_files, 1):
    input_str = str(input_file).replace('/', '\\')
    output_str = str(input_file.parent / (input_file.stem + '.ecw')).replace('/', '\\')

    script_content += f"""
// [{i}/{len(filtered_files)}] Processing: {input_file.name}
IMPORT FILENAME="{input_str}"
EXPORT_RASTER FILENAME="{output_str}" TYPE=ECW SPATIAL_RES_METERS=CURRENT COMPRESSION_RATIO=10
UNLOAD_ALL
"""

# Add completion message
script_content += f"""
// ===== PROCESSING COMPLETE =====
// Script selesai - {len(filtered_files)} files processed
"""

# Write script
with open(OUTPUT_SCRIPT, 'w', encoding='utf-8') as f:
    f.write(script_content)

print(f"\n[OK] Script generated: {OUTPUT_SCRIPT}")
print(f"\nFiles yang akan diproses:")
for i, f in enumerate(filtered_files, 1):
    size_mb = os.path.getsize(f) / (1024 * 1024)
    print(f"  {i:3d}. {f.name:40s} ({size_mb:8.2f} MB)")

print(f"\n{'='*70}")
print(f"Total: {len(filtered_files)} files")
print(f"{'='*70}")
print(f"\nUntuk run script:")
print(f"  1. Buka Global Mapper")
print(f"  2. File > Run Script")
print(f"  3. Pilih: {os.path.abspath(OUTPUT_SCRIPT)}")
