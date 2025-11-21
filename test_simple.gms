// Simple test script
UNLOAD_ALL

// Import first file only
IMPORT FILENAME="D:\Ayah\sipukat\merged\merged_batch_007.tif"

// Export to ECW
EXPORT_ECW FILENAME="D:\Ayah\sipukat\merged\test_output.ecw" SPATIAL_RES_METERS=CURRENT

UNLOAD_ALL

SHOW_MESSAGE_BOX "Test conversion complete!"
