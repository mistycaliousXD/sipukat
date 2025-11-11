# BPN Tile Downloader & GeoTIFF Merger

Sistem download, georeference, dan merge tiles dari BPN (Badan Pertanahan Nasional) dengan batch processing dan resume capability.

## 📋 Daftar Isi

- [Fitur](#fitur)
- [Persyaratan](#persyaratan)
- [Instalasi](#instalasi)
- [Struktur File](#struktur-file)
- [Cara Penggunaan](#cara-penggunaan)
  - [Step 1: Download Tiles](#step-1-download-tiles)
  - [Step 2: Georeference](#step-2-georeference)
  - [Step 3: Merge ke GeoTIFF](#step-3-merge-ke-geotiff)
- [Command Line Arguments](#command-line-arguments)
- [Progress Tracking](#progress-tracking)
- [Error Handling](#error-handling)
- [Tips & Tricks](#tips--tricks)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Fitur

### Download (`download_tiles_batch.py`)

- ✅ **Batch Processing**: Split tiles ke batches 50x50 (2,500 tiles/batch)
- ✅ **Resume Capability**: Pause (Ctrl+C) dan resume kapan saja
- ✅ **Auto Retry**: Retry failed tiles 3x dengan exponential backoff
- ✅ **Skip Existing**: Auto skip tiles yang sudah didownload
- ✅ **Progress Tracking**: JSON file untuk track progress
- ✅ **Progress Bar**: Real-time progress dengan tqdm
- ✅ **ETA Calculation**: Estimasi waktu selesai
- ✅ **Failed Tiles Log**: Simpan daftar tiles yang gagal
- ✅ **Parallel Download**: Multi-threading (10 workers)

### Georeference (`georeference_batch.py`)

- ✅ **Batch Selection**: Pilih batch mana yang ingin diproses
- ✅ **Multi-Batch Processing**: Process multiple batches sekaligus
- ✅ **Progress Bar**: Real-time progress per batch
- ✅ **Skip Existing**: Auto skip tiles yang sudah di-georeference
- ✅ **Multi-Threading**: Parallel processing untuk speed
- ✅ **Progress Tracking**: JSON file untuk track progress

### Merge (`merge_geotiff.py`)

- ✅ **Auto-Detect Batches**: Scan semua georeferenced batches
- ✅ **Selective Merge**: Merge batch tertentu atau semua
- ✅ **VRT Intermediate**: Create VRT dulu untuk efisiensi
- ✅ **Compression**: LZW compression untuk size reduction
- ✅ **Auto-Increment Naming**: merged_map_001.tif, merged_map_002.tif, dst
- ✅ **Merge Log**: Log file untuk track merge history

---

## 📦 Persyaratan

### Software

- **Python 3.7+**
- **GDAL** (command-line tools)
  - Windows: Download dari [GISInternals](https://www.gisinternals.com/release.php)
  - Path harus ter-set: `C:\Program Files\GDAL`

### Python Packages

```bash
pip install requests tqdm
```

### GDAL Environment Variables

Script akan auto-setup GDAL environment variables jika installed di:

- `C:\Program Files\GDAL`
- `C:\Program Files\GDAL\projlib` (PROJ_LIB)
- `C:\Program Files\GDAL\gdal-data` (GDAL_DATA)

Jika GDAL di lokasi berbeda, edit fungsi `setup_gdal_env()` di setiap script.

---

## 🚀 Instalasi

### 1. Clone atau Download Repository

```bash
git clone <repository-url>
cd sipukat
```

### 2. Install Python Dependencies

```bash
pip install requests tqdm
```

### 3. Install GDAL

- Download dari [GISInternals](https://www.gisinternals.com/release.php)
- Pilih versi sesuai Python (e.g., MSVC 2022 / x64 untuk Python 3.11)
- Install ke `C:\Program Files\GDAL`
- Verifikasi: `gdalbuildvrt --version`

### 4. Test Installation

```bash
python download_tiles_batch.py --status
```

---

## 📁 Struktur File

```
sipukat/
├── download_tiles_batch.py      # Script download tiles
├── georeference_batch.py         # Script georeference
├── merge_geotiff.py              # Script merge
├── README.md                     # Dokumentasi
│
├── tiles/                        # Output download
│   ├── tiles_batch_001/         # Batch 1: JPG files
│   ├── tiles_batch_002/         # Batch 2: JPG files
│   ├── ...
│   ├── progress.json            # Download progress
│   └── failed_tiles.json        # Failed tiles list
│
├── georeferenced/               # Output georeference
│   ├── georeferenced_batch_001/ # Batch 1: GeoTIFF files
│   ├── georeferenced_batch_002/ # Batch 2: GeoTIFF files
│   ├── ...
│   └── georeference_progress.json
│
└── merged/                      # Output merge
    ├── mosaic.vrt              # VRT mosaic
    ├── merged_map_001.tif      # Final GeoTIFF
    └── merge_log_*.txt         # Merge logs
```

---

## 📖 Cara Penggunaan

### Step 1: Download Tiles

#### Basic Usage

```bash
python download_tiles_batch.py
```

Kemudian input koordinat (Koordinat ini adalah target yang akan di download secara besar):

```
X Start: 1728675
X End: 1729154
Y Start: 1051362
Y End: 1052034
Zoom Level: 21
Variant (default 2): 2
```

Script akan:

1. Calculate total batches (480×673 tiles = 140 batches @ 50×50)
2. Download setiap batch dengan progress bar
3. Save progress setiap batch selesai
4. Log failed tiles ke `failed_tiles.json`

**Output:**

```
tiles/
├── tiles_batch_001/  (2,500 tiles)
├── tiles_batch_002/  (2,500 tiles)
├── ...
├── tiles_batch_140/  (~690 tiles)
├── progress.json
└── failed_tiles.json
```

#### Resume Download

Jika download terputus (Ctrl+C atau network error):

```bash
python download_tiles_batch.py --resume
```

Script akan:

- Load progress dari `progress.json`
- Skip batches yang sudah selesai
- Lanjutkan dari batch terakhir

#### Retry Failed Tiles

```bash
python download_tiles_batch.py --retry-failed
```

Re-download semua tiles yang gagal dari `failed_tiles.json`.

#### Download Batch Tertentu

```bash
python download_tiles_batch.py --batch 25
```

Download hanya batch 25.

#### Check Progress

```bash
python download_tiles_batch.py --status
```

Tampilkan statistik download tanpa download.

---

### Step 2: Georeference

#### Interactive Mode

```bash
python georeference_batch.py
```

Akan muncul menu:

```
📋 Available Batches: 140

   ⏳ Batch 001: 2,500 tiles
   ⏳ Batch 002: 2,500 tiles
   ...

Options:
  - Specific batch: 1
  - Batch range: 1-10
  - All batches: all

Pilih batch untuk diproses: _
```

Input pilihan:

- `1` → Process batch 1 saja
- `1-10` → Process batch 1 sampai 10
- `all` → Process semua batch

#### Process All Batches

```bash
python georeference_batch.py --all
```

Process semua batch sekaligus (bisa lama!).

#### Process Specific Batch

```bash
python georeference_batch.py --batch 5
```

Process hanya batch 5.

#### Process Batch Range

```bash
python georeference_batch.py --batch-range 1-20
```

Process batch 1 sampai 20.

#### List Available Batches

```bash
python georeference_batch.py --list
```

Tampilkan daftar batch yang tersedia.

**Output:**

```
georeferenced/
├── georeferenced_batch_001/
│   ├── tile_21_1728675_1051362.tif
│   └── ... (2,500 GeoTIFF files)
├── georeferenced_batch_002/
└── georeference_progress.json
```

---

### Step 3: Merge ke GeoTIFF

#### Merge All Batches

```bash
python merge_geotiff.py
```

Script akan:

1. Scan semua `georeferenced_batch_*` folders
2. Tampilkan ringkasan batches
3. Create VRT mosaic
4. Merge ke single GeoTIFF

**Output:**

```
merged/
├── mosaic.vrt
├── merged_map_001.tif  (Final GeoTIFF)
└── merge_log_20251108_171801.txt
```

#### Merge Specific Batches

```bash
python merge_geotiff.py --batches 1,2,5,10
```

Merge hanya batch 1, 2, 5, dan 10.

#### Merge Batch Range

```bash
python merge_geotiff.py --batch-range 1-50
```

Merge batch 1 sampai 50.

#### List Available Batches

```bash
python merge_geotiff.py --list
```

Tampilkan daftar georeferenced batches.

---

## 🎮 Command Line Arguments

### `download_tiles_batch.py`

| Argument         | Deskripsi                         |
| ---------------- | --------------------------------- |
| `--resume`       | Resume dari progress terakhir     |
| `--retry-failed` | Retry semua failed tiles          |
| `--batch N`      | Download batch N saja             |
| `--status`       | Tampilkan progress tanpa download |

**Contoh:**

```bash
# Resume download
python download_tiles_batch.py --resume

# Retry failed
python download_tiles_batch.py --retry-failed

# Download batch 10
python download_tiles_batch.py --batch 10

# Check status
python download_tiles_batch.py --status
```

### `georeference_batch.py`

| Argument            | Deskripsi                |
| ------------------- | ------------------------ |
| `--batch N`         | Process batch N saja     |
| `--batch-range M-N` | Process batch M sampai N |
| `--all`             | Process semua batch      |
| `--list`            | List available batches   |

**Contoh:**

```bash
# Process batch 5
python georeference_batch.py --batch 5

# Process batch 1-20
python georeference_batch.py --batch-range 1-20

# Process all
python georeference_batch.py --all

# List batches
python georeference_batch.py --list
```

### `merge_geotiff.py`

| Argument            | Deskripsi              |
| ------------------- | ---------------------- |
| `--batches M,N,P`   | Merge batch M, N, P    |
| `--batch-range M-N` | Merge batch M sampai N |
| `--list`            | List available batches |

**Contoh:**

```bash
# Merge specific batches
python merge_geotiff.py --batches 1,5,10,20

# Merge batch 1-50
python merge_geotiff.py --batch-range 1-50

# Merge all (default)
python merge_geotiff.py

# List batches
python merge_geotiff.py --list
```

---

## 📊 Progress Tracking

### Download Progress (`tiles/progress.json`)

```json
{
  "total_tiles": 323040,
  "total_batches": 140,
  "completed_batches": [1, 2, 3, 4, 5],
  "current_batch": 6,
  "tiles_downloaded": 12500,
  "tiles_failed": 15,
  "start_time": "2025-11-08 16:30:00",
  "last_update": "2025-11-08 17:45:00",
  "estimated_completion": "2025-11-09 02:15:00",
  "avg_time_per_batch": 125.5,
  "config": {
    "x_start": 1728675,
    "x_end": 1729154,
    "y_start": 1051362,
    "y_end": 1052034,
    "zoom": 21,
    "variant": 2,
    "batch_size": 50
  },
  "batch_details": {
    "1": {
      "status": "completed",
      "tiles": 2500,
      "success": 2500,
      "skipped": 0,
      "failed": 0,
      "time_seconds": 120.5,
      "size_bytes": 2650000
    }
  }
}
```

### Failed Tiles (`tiles/failed_tiles.json`)

```json
{
  "batch_001": [
    {
      "x": 1728675,
      "y": 1051362,
      "error": "Connection timeout",
      "retries": 3
    }
  ],
  "batch_002": [
    {
      "x": 1728725,
      "y": 1051370,
      "error": "404 Not Found",
      "retries": 3
    }
  ]
}
```

### Georeference Progress (`georeferenced/georeference_progress.json`)

```json
{
  "completed_batches": [1, 2, 3],
  "last_update": "2025-11-08 18:30:00",
  "batch_details": {
    "1": {
      "status": "completed",
      "tiles": 2500,
      "success": 2500,
      "skipped": 0,
      "failed": 0,
      "time_seconds": 180.2,
      "failed_tiles": []
    }
  }
}
```

---

## ⚠️ Error Handling

### Retry Mechanism

Script otomatis retry tiles yang gagal:

- **Max retries**: 3 kali per tile
- **Delay**: 2, 4, 6 seconds (exponential backoff)
- **Failed tiles** disimpan ke `failed_tiles.json`

### Network Errors

Jika koneksi terputus:

1. Script akan retry otomatis
2. Setelah 3x retry gagal, tile di-skip dan dicatat
3. Progress tetap tersimpan
4. Bisa resume kapan saja dengan `--resume`
5. Bisa retry manual dengan `--retry-failed`

### GDAL Errors

Jika GDAL error:

- Check environment variables di `setup_gdal_env()`
- Verifikasi GDAL terinstall: `gdalbuildvrt --version`
- Check PROJ_LIB path: `C:\Program Files\GDAL\projlib`

---

## 💡 Tips & Tricks

### 1. Download Strategy untuk 323K Tiles

**Option A: Non-Stop** (Recommended jika koneksi stabil)

```bash
# Jalankan dan biarkan sampai selesai
python download_tiles_batch.py
```

**Option B: Batch-by-Batch** (Recommended jika koneksi tidak stabil)

```bash
# Download batch 1-10 dulu
for i in {1..10}; do
  python download_tiles_batch.py --batch $i
done

# Lanjut batch 11-20
for i in {11..20}; do
  python download_tiles_batch.py --batch $i
done
```

**Option C: Resume-Based** (Paling flexible)

```bash
# Start download
python download_tiles_batch.py

# Pause kapan saja (Ctrl+C)
# Resume nanti
python download_tiles_batch.py --resume
```

### 2. Georeference Strategy

**Option A: All at Once** (Jika CPU kuat)

```bash
python georeference_batch.py --all
```

**Option B: Range-by-Range** (Recommended)

```bash
# Process 20 batches at a time
python georeference_batch.py --batch-range 1-20
python georeference_batch.py --batch-range 21-40
python georeference_batch.py --batch-range 41-60
# dst...
```

**Option C: Overnight Processing**

```bash
# Jalankan sebelum tidur
python georeference_batch.py --batch-range 1-70

# Besok pagi lanjut sisanya
python georeference_batch.py --batch-range 71-140
```

### 3. Merge Strategy

**Option A: Partial Merge** (Test dulu)

```bash
# Merge batch 1-10 dulu untuk test
python merge_geotiff.py --batch-range 1-10
```

**Option B: Full Merge**

```bash
# Merge semua batch
python merge_geotiff.py
```

### 4. Monitoring Progress

**Check download status:**

```bash
python download_tiles_batch.py --status
```

**Check what batches are downloaded:**

```bash
ls -l tiles/tiles_batch_*/
```

**Check what batches are georeferenced:**

```bash
python georeference_batch.py --list
```

**Check disk usage:**

```bash
du -sh tiles/ georeferenced/ merged/
```

### 5. Optimization

**Adjust worker threads:**
Edit di script sesuai CPU/Network:

```python
# download_tiles_batch.py
MAX_WORKERS = 10  # Increase jika network cepat

# georeference_batch.py
MAX_WORKERS = 4   # Increase jika CPU banyak core
```

---

## 🔧 Troubleshooting

### Problem: "GDAL tidak ditemukan"

**Solusi:**

1. Check GDAL installed: `gdalbuildvrt --version`
2. Check path di `setup_gdal_env()` function
3. Reinstall GDAL dari [GISInternals](https://www.gisinternals.com/release.php)

### Problem: "PROJ database error"

**Solusi:**

1. Set PROJ_LIB ke GDAL projlib:
   ```bash
   export PROJ_LIB="/c/Program Files/GDAL/projlib"
   ```
2. Atau edit `setup_gdal_env()` di script

### Problem: Download lambat

**Solusi:**

1. Check koneksi internet
2. Increase `MAX_WORKERS` di `download_tiles_batch.py`
3. Download per batch kecil dengan `--batch`

### Problem: Failed tiles banyak

**Solusi:**

1. Check `failed_tiles.json` untuk pattern error
2. Retry manual: `python download_tiles_batch.py --retry-failed`
3. Jika masih gagal, tiles mungkin memang tidak ada di server

### Problem: Georeference lambat

**Solusi:**

1. Increase `MAX_WORKERS` di `georeference_batch.py`
2. Process per batch range kecil
3. Close aplikasi lain untuk free CPU

### Problem: Merge error / out of memory

**Solusi:**

1. Merge per batch range kecil:
   ```bash
   python merge_geotiff.py --batch-range 1-50
   python merge_geotiff.py --batch-range 51-100
   python merge_geotiff.py --batch-range 101-140
   ```
2. Increase virtual memory di Windows
3. Close aplikasi lain

### Problem: File sudah ada (merged_map.tif)

**Solusi:**
Script otomatis create auto-increment filename:

- `merged_map.tif` → sudah ada
- `merged_map_001.tif` → created
- `merged_map_002.tif` → created next time
- dst...

---

## 📈 Estimasi Waktu & Size

### Untuk 323,040 Tiles (480×673 tiles, Zoom 21)

| Step         | Batches | Tiles/Batch | Time/Batch | Total Time       | Disk Size  |
| ------------ | ------- | ----------- | ---------- | ---------------- | ---------- |
| Download     | 140     | 2,500       | 1-2 min    | **2-3 hours**    | ~300 MB    |
| Georeference | 140     | 2,500       | 3-5 min    | **8-10 hours**   | ~50 GB     |
| Merge        | 1       | 323,040     | 30-60 min  | **1 hour**       | ~5-10 GB   |
| **TOTAL**    |         |             |            | **~12-14 hours** | **~60 GB** |

_Estimasi bisa berbeda tergantung internet speed, CPU, dan disk speed_

---

## 📝 Notes

1. **Disk Space**: Pastikan ada minimal **70 GB** free space
2. **Network**: Stable internet connection recommended
3. **CPU**: Multi-core CPU akan mempercepat georeference
4. **RAM**: Minimal 8 GB RAM recommended
5. **Time**: Bisa dijalankan bertahap (tidak harus sekaligus)

---

## 🆘 Support

Jika ada masalah:

1. Check log files di `tiles/progress.json` dan `failed_tiles.json`
2. Run dengan `--status` untuk lihat progress
3. Check disk space: `df -h` (Linux/Mac) atau `dir` (Windows)
4. Verify GDAL: `gdalbuildvrt --version`

---

## 📄 License

Free to use for personal and educational purposes.

---

## 🙏 Credits

- BPN (Badan Pertanahan Nasional) untuk tile server
- GDAL untuk geospatial tools
- Python community untuk libraries

---

**Happy Mapping! 🗺️**
