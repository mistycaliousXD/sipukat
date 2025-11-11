# Quick Start Guide

## 🚀 Untuk Langsung Mulai

### Prerequisites
```bash
# Install dependencies
pip install requests tqdm

# Verify GDAL
gdalbuildvrt --version
```

---

## 📥 Download 323,040 Tiles Anda

### Step 1: Download (2-3 jam)
```bash
python download_tiles_batch.py
```

Input:
```
X Start: 1728675
X End: 1729154
Y Start: 1051362
Y End: 1052034
Zoom Level: 21
Variant: 2
```

**Akan membuat 140 batches** @ 50×50 tiles

Jika terputus, resume dengan:
```bash
python download_tiles_batch.py --resume
```

---

### Step 2: Georeference (8-10 jam)

**Option A: All at once**
```bash
python georeference_batch.py --all
```

**Option B: Per 20 batches** (Recommended)
```bash
python georeference_batch.py --batch-range 1-20
python georeference_batch.py --batch-range 21-40
python georeference_batch.py --batch-range 41-60
python georeference_batch.py --batch-range 61-80
python georeference_batch.py --batch-range 81-100
python georeference_batch.py --batch-range 101-120
python georeference_batch.py --batch-range 121-140
```

---

### Step 3: Merge (30-60 menit)
```bash
python merge_geotiff.py
```

Output: `merged/merged_map_001.tif`

---

## ⏸️ Pause & Resume

### Pause Download
Tekan `Ctrl+C` kapan saja

### Resume Download
```bash
python download_tiles_batch.py --resume
```

### Check Progress
```bash
python download_tiles_batch.py --status
```

---

## 📊 Monitoring

### Check downloaded batches
```bash
ls tiles/tiles_batch_*/
```

### Check georeferenced batches
```bash
python georeference_batch.py --list
```

### Check disk usage
```bash
du -sh tiles/ georeferenced/ merged/
```

---

## ⚠️ Common Issues

### "GDAL tidak ditemukan"
```bash
# Verify GDAL path
gdalbuildvrt --version

# If error, check C:\Program Files\GDAL exists
```

### Download terlalu lambat
```bash
# Download per batch
python download_tiles_batch.py --batch 1
python download_tiles_batch.py --batch 2
# etc...
```

### Many failed tiles
```bash
# Retry failed tiles
python download_tiles_batch.py --retry-failed
```

---

## 💡 Recommendations

### For 323K tiles:

**Day 1:**
- Morning: Start download (`download_tiles_batch.py`)
- Let it run 2-3 hours
- Evening: Start georeference batch 1-70 before sleep

**Day 2:**
- Morning: Continue georeference batch 71-140
- Afternoon: Merge all batches

**Total: ~1.5 days for 323K tiles**

---

## 🎯 Final Output

```
merged/merged_map_001.tif  (~5-10 GB)
```

Bisa dibuka di:
- QGIS
- ArcGIS
- Google Earth Pro
- Any GIS software

---

**Lihat README.md untuk dokumentasi lengkap!**
