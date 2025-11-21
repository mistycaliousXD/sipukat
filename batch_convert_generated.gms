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

// Processing: merged_batch_001.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_001.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_001.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL


// Processing: merged_batch_002.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_002.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_002.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL


// Processing: merged_batch_003.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_003.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_003.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL


// Processing: merged_batch_004.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_004.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_004.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL


// Processing: merged_batch_005.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_005.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_005.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL


// Processing: merged_batch_006.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_006.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_006.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL


// Processing: merged_batch_007.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_007.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_007.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL


// Processing: merged_batch_008.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_008.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_008.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL


// Processing: merged_batch_009.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_009.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_009.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL


// Processing: merged_batch_010.tif
IMPORT FILENAME="D:\Ayah\sipukat\merged_prioritas_batch_1\merged_batch_010.tif"

EXPORT_ECW FILENAME="D:\Ayah\sipukat\ECW_prioritas_batch_1\merged_batch_010.ecw" \
    SPATIAL_RES_METERS=CURRENT \
    FILL_GAPS=NO \
    GEN_WORLD_FILE=NO

UNLOAD_ALL

// ===== MARKER: FILES_END =====

// Script selesai
SHOW_MESSAGE_BOX "Batch conversion selesai!"
