// Global Mapper Batch Convert Script
// Template untuk konversi otomatis GeoTIFF ke ECW
// Script ini akan di-generate oleh global_mapper_batch.py

// Clear workspace
UNLOAD_ALL

// Set global options untuk ECW export
GLOBAL_SETTINGS
	EXPORT_ECW_COMPRESSION_RATIO=10
	EXPORT_ECW_VERSION=3
	EXPORT_ECW_FORMAT=LOSSLESS
END_GLOBAL_SETTINGS

// ===== FILE PROCESSING LOOP =====
// Setiap file akan memiliki blok IMPORT dan EXPORT_ECW
// Format:
// IMPORT "path/to/input.tif"
// EXPORT_ECW "path/to/output.ecw"
// UNLOAD_ALL

// ===== MARKER: FILES_START =====
// Files akan diinsert di sini oleh Python script
// ===== MARKER: FILES_END =====

// Script selesai
SHOW_MESSAGE_BOX "Batch conversion selesai!"
