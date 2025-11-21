# Global Mapper Batch Converter

Solusi otomatis untuk konversi batch GeoTIFF ke ECW menggunakan Global Mapper.

## 📋 Requirements

- **Global Mapper 25+** (dengan lisensi ECW built-in)
- **Python 3.x**
- File template: `global_mapper_batch_template.gms`

## 🚀 Quick Start

### 1. Cara Paling Mudah (Default Settings)

```bash
python global_mapper_batch.py --execute
```

Script akan:
- ✓ Scan folder `D:\Ayah\sipukat\merged` untuk file `.tif`
- ✓ Generate script Global Mapper
- ✓ Execute Global Mapper otomatis
- ✓ Konversi semua file ke ECW dengan compression ratio 10:1

### 2. List Files Dulu (Preview)

```bash
python global_mapper_batch.py --list-only
```

Hanya menampilkan file yang akan diproses, tanpa generate script.

### 3. Custom Input/Output Folder

```bash
python global_mapper_batch.py -i "D:\Data\Input" -o "D:\Data\Output" --execute
```

### 4. High Compression (Ratio 20:1)

```bash
python global_mapper_batch.py -c 20 --execute
```

## 📖 Detailed Usage

### Mode 1: Fully Automatic (Recommended)

```bash
python global_mapper_batch.py --execute
```

- Generate script
- Execute Global Mapper otomatis
- Tunggu sampai selesai

### Mode 2: Generate Script Only (Manual Execution)

```bash
python global_mapper_batch.py --no-execute
```

Kemudian di Global Mapper:
1. Buka Global Mapper
2. **File > Run Script**
3. Pilih: `batch_convert_generated.gms`

### Mode 3: Interactive (Default)

```bash
python global_mapper_batch.py
```

Script akan:
1. Generate script
2. Tanya: Execute otomatis atau manual?
3. User pilih

## 🎛️ Command Line Options

### Input/Output

| Option | Description | Default |
|--------|-------------|---------|
| `-i`, `--input` | Folder input berisi GeoTIFF | `D:\Ayah\sipukat\merged` |
| `-o`, `--output` | Folder output untuk ECW | Sama dengan input |
| `-r`, `--recursive` | Scan subfolder juga | False |

### Conversion Parameters

| Option | Description | Default |
|--------|-------------|---------|
| `-c`, `--compression` | Rasio kompresi ECW (1-100) | 10 |
| `-v`, `--ecw-version` | Versi ECW format (2 atau 3) | 3 |

### Script Generation

| Option | Description | Default |
|--------|-------------|---------|
| `-t`, `--template` | Template .gms file | `global_mapper_batch_template.gms` |
| `-s`, `--script-output` | Output .gms filename | `batch_convert_generated.gms` |

### Execution Control

| Option | Description |
|--------|-------------|
| `-e`, `--execute` | Execute Global Mapper otomatis setelah generate |
| `--no-execute` | Hanya generate script, jangan execute |
| `--gm-path` | Path manual ke `global_mapper.exe` |
| `--no-wait` | Run Global Mapper in background (tidak tunggu selesai) |

### Other

| Option | Description |
|--------|-------------|
| `-l`, `--list-only` | Hanya tampilkan list file yang akan diproses |
| `-h`, `--help` | Show help message |

## 💡 Contoh Penggunaan

### Example 1: Basic Batch Convert

```bash
python global_mapper_batch.py --execute
```

Output:
```
======================================================================
Scanning untuk GeoTIFF files...
======================================================================
Input folder: D:\Ayah\sipukat\merged
Recursive: No
======================================================================

Ditemukan 15 file GeoTIFF:

    1. file001.tif                                            (  234.56 MB)
    2. file002.tif                                            (  198.23 MB)
    ...

======================================================================
Total: 15 files, 3456.78 MB
======================================================================

Generated Global Mapper script: batch_convert_generated.gms
Total files to process: 15
Compression ratio: 10:1
ECW version: 3

✓ Global Mapper execution selesai!
```

### Example 2: High Compression dengan Custom Folder

```bash
python global_mapper_batch.py \
    -i "D:\Data\Orthophoto" \
    -o "D:\Data\ECW_Output" \
    -c 20 \
    --execute
```

Konversi dengan ratio 20:1 (file lebih kecil, quality sedikit turun).

### Example 3: Scan Recursive (Include Subfolder)

```bash
python global_mapper_batch.py \
    -i "D:\Data\AllProjects" \
    -o "D:\Data\ECW_Archive" \
    --recursive \
    --execute
```

Scan semua subfolder untuk file GeoTIFF.

### Example 4: Preview Files Only

```bash
python global_mapper_batch.py -i "D:\Data" --list-only
```

Hanya show list file, tidak generate script.

### Example 5: Generate Script for Manual Execution

```bash
python global_mapper_batch.py -i "D:\Data" --no-execute
```

Generate script `batch_convert_generated.gms`, kemudian:
1. Buka Global Mapper
2. File > Run Script
3. Browse ke `batch_convert_generated.gms`

### Example 6: Custom Global Mapper Path

Jika Global Mapper tidak terdeteksi otomatis:

```bash
python global_mapper_batch.py \
    --gm-path "C:\MyPrograms\GlobalMapper\global_mapper.exe" \
    --execute
```

### Example 7: Background Execution

```bash
python global_mapper_batch.py --execute --no-wait
```

Start Global Mapper dan langsung return (tidak tunggu selesai).

## 🔧 Troubleshooting

### Error: "Global Mapper executable tidak ditemukan"

**Solusi 1:** Install Global Mapper di lokasi default
- `C:\Program Files\GlobalMapper25\`

**Solusi 2:** Specify manual path
```bash
python global_mapper_batch.py --gm-path "C:\path\to\global_mapper.exe"
```

### Error: "Template file tidak ditemukan"

Pastikan file `global_mapper_batch_template.gms` ada di folder yang sama dengan script.

### Error: "Folder tidak ditemukan"

Specify full path dengan quotes:
```bash
python global_mapper_batch.py -i "D:\Full\Path\To\Folder"
```

### Conversion Gagal di Global Mapper

**Cek:**
1. ✓ Global Mapper memiliki lisensi valid (termasuk ECW support)
2. ✓ File input adalah valid GeoTIFF
3. ✓ Output folder memiliki write permission
4. ✓ Cukup disk space untuk output files

## 📊 Compression Ratio Guide

| Ratio | Quality | Use Case | Typical Size Reduction |
|-------|---------|----------|----------------------|
| 5:1   | Excellent | Archival, high precision | ~80% smaller |
| 10:1  | Very Good | General purpose (default) | ~90% smaller |
| 20:1  | Good | Web mapping, visualization | ~95% smaller |
| 50:1  | Fair | Preview, thumbnails | ~98% smaller |

**Recommendation:**
- **Archival/Analysis**: 5:1 atau 10:1
- **Web Mapping**: 10:1 atau 20:1
- **Preview Only**: 20:1 atau higher

## 🎯 Workflow Integration

### Workflow 1: Daily Batch Processing

Buat batch file `daily_convert.bat`:

```batch
@echo off
cd /d D:\Ayah\sipukat
python global_mapper_batch.py -i "D:\Daily\Input" -o "D:\Daily\Output" --execute
pause
```

Double-click untuk run.

### Workflow 2: Scheduled Task

Windows Task Scheduler:
```
Program: C:\Users\YourUser\AppData\Local\Programs\Python\Python311\python.exe
Arguments: D:\Ayah\sipukat\global_mapper_batch.py --execute --no-wait
Start in: D:\Ayah\sipukat
```

### Workflow 3: Watch Folder (Advanced)

Combine dengan file watcher untuk auto-convert saat ada file baru.

## 📝 Global Mapper Script Format

Generated script structure:

```gms
// Set global compression options
GLOBAL_SETTINGS
    EXPORT_ECW_COMPRESSION_RATIO=10
    EXPORT_ECW_VERSION=3
    EXPORT_ECW_FORMAT=LOSSLESS
END_GLOBAL_SETTINGS

// For each file:
IMPORT FILENAME="D:\path\to\input.tif"
EXPORT_ECW FILENAME="D:\path\to\output.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO
UNLOAD_ALL

// Repeat for all files...
```

## 🆚 Comparison: Python Script vs Global Mapper Script

### Python `geotiff_to_ecw.py` (GDAL-based)

**Pros:**
- ✓ Command-line automation
- ✓ No GUI needed
- ✓ Can run on servers

**Cons:**
- ✗ Requires ECW driver setup (complex!)
- ✗ May need commercial license
- ✗ Currently not working (ECW driver not available)

### Global Mapper Script (This solution)

**Pros:**
- ✓ **Works immediately** (ECW built-in)
- ✓ No driver setup needed
- ✓ Full ECW write support included
- ✓ GUI preview available
- ✓ Reliable and tested

**Cons:**
- ✗ Requires Global Mapper license
- ✗ Windows only

## 🔗 Related Files

- `global_mapper_batch.py` - Main Python script
- `global_mapper_batch_template.gms` - Template script
- `batch_convert_generated.gms` - Generated script (auto-created)
- `geotiff_to_ecw.py` - Alternative GDAL-based script (currently not working)

## 📚 Resources

- [Global Mapper Scripting Reference](https://www.bluemarblegeo.com/knowledgebase/global-mapper/Scripting_Reference.htm)
- [ECW Format Information](https://gdal.org/drivers/raster/ecw.html)
- [Global Mapper Download](https://www.bluemarblegeo.com/products/global-mapper.php)

## 🤝 Support

Jika ada error atau pertanyaan:

1. Check error message di terminal
2. Verify Global Mapper installation
3. Try with `--list-only` first
4. Check generated `.gms` script content

## 📜 License

Script ini dibuat untuk keperluan internal. Global Mapper memerlukan lisensi terpisah.

---

**Created by:** Claude Code
**Date:** 2025-11-11
**Version:** 1.0
