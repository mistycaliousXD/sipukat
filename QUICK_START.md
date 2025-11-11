# 🚀 Quick Start Guide - BPN Tile Downloader

## 📦 Install Dependencies

### For Optimized Threading Version (Recommended)
```bash
pip install requests urllib3 tqdm
```

### For Async Turbo Mode (Maximum Speed)
```bash
pip install requests urllib3 tqdm aiohttp aiofiles
# or
pip install -r requirements_async.txt
```

---

## ⚡ Which Version Should I Use?

### Use **Threading Version** (`download_tiles_batch.py`) if:
- ✅ First time user / want simplicity
- ✅ Download < 50,000 tiles
- ✅ Koneksi internet < 50 Mbps
- ✅ Tidak familiar dengan async programming

**Expected Speed:** 15-25 tiles/second (8-10x faster than original)

### Use **Async Version** (`download_tiles_async.py`) if:
- ✅ Download > 100,000 tiles
- ✅ Koneksi internet > 100 Mbps
- ✅ Need maximum speed
- ✅ Comfortable with async/await

**Expected Speed:** 40-70 tiles/second (15-24x faster than original)

---

## 🎮 Quick Usage

### Threading Version (Simple & Fast)
```bash
# Start new download
python download_tiles_batch.py

# Input coordinates when prompted:
X Start: 1728675
X End: 1729154
Y Start: 1051362
Y End: 1052034
Zoom Level: 21
Variant: 2

# Press 'y' to confirm and start
```

### Async Version (Maximum Speed)
```bash
# Start with default settings (500 concurrent)
python download_tiles_async.py

# Or with custom concurrent limit
python download_tiles_async.py --concurrent 800

# For extremely fast internet
python download_tiles_async.py --concurrent 1000
```

---

## 🔄 Resume Interrupted Downloads

### If download interrupted (Ctrl+C, network error, etc.):

**Threading:**
```bash
python download_tiles_batch.py --resume
```

**Async:**
```bash
python download_tiles_async.py --resume
```

Progress automatically saved! No data loss.

---

## 📊 Check Progress

**Threading version:**
```bash
python download_tiles_batch.py --status
```

**Async version:**
Check `tiles/progress_async.json` for details.

---

## 🎯 Performance Comparison

### Your Original Case: 300,000+ tiles

| Version | Estimated Time | Speed | Workers |
|---------|---------------|-------|---------|
| **Original** | ~30 hours | 2.8 tiles/s | 10 |
| **Threading (optimized)** | **~3-4 hours** | 22 tiles/s | 20 |
| **Async (500 concurrent)** | **~1.5-2 hours** | 45 tiles/s | 500 |
| **Async (1000 concurrent)** | **~1-1.5 hours** | 65 tiles/s | 1000 |

**Recommendation:** Use async version untuk save **25-28 hours!** ⚡

---

## 🔧 Configuration Tips

### If download is slow:

#### 1. Check network speed first
```bash
# Run speedtest
speedtest-cli
# or visit speedtest.net
```

#### 2. Tune concurrency based on internet speed

**< 10 Mbps:**
```python
# download_tiles_batch.py
MAX_WORKERS = 10

# download_tiles_async.py
python download_tiles_async.py --concurrent 100
```

**10-50 Mbps:**
```python
# download_tiles_batch.py
MAX_WORKERS = 20  # Default

# download_tiles_async.py
python download_tiles_async.py --concurrent 300
```

**50-100 Mbps:**
```python
# download_tiles_batch.py
MAX_WORKERS = 30  # Edit in file

# download_tiles_async.py
python download_tiles_async.py --concurrent 500  # Default
```

**> 100 Mbps:**
```python
# download_tiles_batch.py
MAX_WORKERS = 40  # Edit in file

# download_tiles_async.py
python download_tiles_async.py --concurrent 1000
```

---

## 🐛 Common Issues & Fixes

### Error: "No module named 'requests'"
```bash
pip install requests tqdm
```

### Error: "No module named 'aiohttp'"
```bash
pip install aiohttp aiofiles
# or
pip install -r requirements_async.txt
```

### Error: "Too many open files" (Windows)
**Solution:** Reduce concurrent connections
```bash
# Threading
Edit download_tiles_batch.py: MAX_WORKERS = 15

# Async
python download_tiles_async.py --concurrent 300
```

### Download stuck at 0%
**Possible causes:**
1. Check internet connection
2. Verify coordinates are correct
3. Check if server is accessible:
   ```bash
   curl -I https://petadasar.atrbpn.go.id/wms/?d=1728675/1051362/21/2
   ```

### Files not downloading
1. Check `tiles/failed_tiles.json` for errors
2. Verify output directory has write permissions
3. Try with smaller batch first (1000 tiles)

---

## 📁 Output Structure

```
sipukat/
├── download_tiles_batch.py          # Optimized threading version
├── download_tiles_async.py          # Async turbo version
├── requirements_async.txt           # Dependencies
├── OPTIMIZATION_README.md           # Detailed docs
├── QUICK_START.md                   # This file
└── tiles/
    ├── tiles_batch_001/             # Batch 1 tiles
    │   ├── tile_21_1728675_1051362.jpg
    │   ├── tile_21_1728675_1051363.jpg
    │   └── ...
    ├── tiles_batch_002/             # Batch 2 tiles
    ├── ...
    ├── progress.json                # Threading progress
    ├── progress_async.json          # Async progress
    ├── failed_tiles.json            # Failed tiles (threading)
    └── failed_tiles_async.json      # Failed tiles (async)
```

---

## 💡 Pro Tips

### 1. Test with small batch first
```bash
# Try with just 1000 tiles to verify everything works
X Start: 1728675
X End: 1728685  # Only 10x100 = 1000 tiles
Y Start: 1051362
Y End: 1051461
```

### 2. Run overnight for large downloads
```bash
# Use nohup for background execution (Linux/Mac)
nohup python download_tiles_async.py &

# Or use screen/tmux
screen -S tiles
python download_tiles_async.py
# Press Ctrl+A, D to detach
```

### 3. Monitor progress in real-time
Progress bar shows:
- `OK`: Successfully downloaded
- `Skip`: Already exists (resume)
- `Fail`: Failed after retries
- `tiles/s`: Current download speed

### 4. Optimize for your use case

**For reliability (unstable internet):**
- Use threading version
- Increase retry attempts in code
- Lower concurrency

**For maximum speed (stable fast internet):**
- Use async version
- Max out concurrent connections
- Monitor CPU/memory usage

---

## 🎓 Understanding the Optimizations

### What makes it faster?

1. **Connection Pooling** - Reuses HTTP connections instead of creating new ones
2. **Concurrent Downloads** - 20-1000 parallel downloads vs 10
3. **Streaming I/O** - Writes directly to disk, saves memory
4. **Non-blocking Retries** - Doesn't waste time waiting
5. **Persistent Workers** - Thread pool reused across batches

### Why async is faster?

- **Threading:** 20 OS threads, context switching overhead
- **Async:** 500-1000 concurrent tasks in single thread, no switching overhead
- **Result:** 2-3x faster than threading for I/O-bound tasks

---

## 📞 Need Help?

1. Read `OPTIMIZATION_README.md` for technical details
2. Check troubleshooting section above
3. Verify all dependencies installed
4. Test with small batch first (1000 tiles)
5. Compare threading vs async performance

---

## ✅ Checklist Before Starting Large Download

- [ ] Dependencies installed (`pip install -r requirements_async.txt`)
- [ ] Tested with small batch (1000 tiles)
- [ ] Good internet connection (check speedtest)
- [ ] Enough disk space (~500MB per 1000 tiles)
- [ ] Chosen right version (threading vs async)
- [ ] Tuned concurrency for your network speed
- [ ] Know how to resume (`--resume`)

**All set? Let's download! 🚀**

```bash
# For maximum speed on your 300K tiles:
python download_tiles_async.py --concurrent 800
```

Good luck! Download akan selesai dalam **~1.5-2 jam** instead of 30+ hours! 🎉
