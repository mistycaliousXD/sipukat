#!/usr/bin/env python3
"""
Script untuk konversi GeoTIFF ke ECW menggunakan GDAL
Convert GeoTIFF files to ECW (Enhanced Compression Wavelet) format

Requirements:
    - GDAL dengan dukungan ECW driver
    - Python 3.x
"""

import os
import sys
import argparse
from pathlib import Path
from osgeo import gdal, osr


def check_ecw_support():
    """
    Cek apakah GDAL mendukung format ECW
    Check if GDAL supports ECW format
    """
    driver = gdal.GetDriverByName('ECW')
    if driver is None:
        print("ERROR: Driver ECW tidak tersedia dalam instalasi GDAL Anda.")
        print("ECW driver requires ERDAS ECW/JP2 SDK.")
        print("\nAlternatif format yang bisa digunakan:")
        print("- JPEG2000 (.jp2) - kompresi tinggi, open source")
        print("- GeoTIFF dengan kompresi (.tif) - JPEG, LZW, atau DEFLATE")
        return False
    return True


def convert_geotiff_to_ecw(input_file, output_file=None, compression_ratio=10,
                           compression_type='JPEG2000', resampling='AVERAGE'):
    """
    Konversi file GeoTIFF ke ECW

    Parameters:
    -----------
    input_file : str
        Path ke file GeoTIFF input
    output_file : str, optional
        Path ke file ECW output (default: sama dengan input dengan ekstensi .ecw)
    compression_ratio : int
        Rasio kompresi (1-100, default: 10)
        Nilai lebih tinggi = kompresi lebih besar = ukuran file lebih kecil
    compression_type : str
        Tipe kompresi: 'JPEG2000' atau 'YUV' (default: 'JPEG2000')
    resampling : str
        Metode resampling: 'NEAREST', 'AVERAGE', 'BILINEAR', 'CUBIC' (default: 'AVERAGE')

    Returns:
    --------
    bool : True jika berhasil, False jika gagal
    """

    # Validasi input file
    if not os.path.exists(input_file):
        print(f"ERROR: File input tidak ditemukan: {input_file}")
        return False

    # Set output file jika tidak ditentukan
    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + '.ecw'

    print(f"\n{'='*60}")
    print(f"Konversi GeoTIFF ke ECW")
    print(f"{'='*60}")
    print(f"Input  : {input_file}")
    print(f"Output : {output_file}")
    print(f"Rasio kompresi: {compression_ratio}:1")
    print(f"Tipe kompresi : {compression_type}")
    print(f"Resampling    : {resampling}")
    print(f"{'='*60}\n")

    try:
        # Buka dataset input
        print("Membuka file input...")
        src_ds = gdal.Open(input_file, gdal.GA_ReadOnly)
        if src_ds is None:
            print(f"ERROR: Tidak dapat membuka file: {input_file}")
            return False

        # Dapatkan informasi dataset
        cols = src_ds.RasterXSize
        rows = src_ds.RasterYSize
        bands = src_ds.RasterCount
        projection = src_ds.GetProjection()
        geotransform = src_ds.GetGeoTransform()

        print(f"Dimensi: {cols} x {rows} pixels, {bands} bands")
        print(f"Proyeksi: {projection[:50]}..." if len(projection) > 50 else f"Proyeksi: {projection}")

        # Set options untuk ECW
        creation_options = [
            f'TARGET={compression_ratio}',  # Rasio kompresi
            f'ECW_FORMAT_VERSION=3',         # Versi ECW (2 atau 3)
        ]

        # Tambahan options
        if compression_type:
            creation_options.append(f'ECW_ENCODE_KEY={compression_type}')

        print(f"\nMemulai konversi...")
        print(f"Creation options: {creation_options}")

        # Translate ke ECW
        translate_options = gdal.TranslateOptions(
            format='ECW',
            creationOptions=creation_options,
            resampleAlg=resampling
        )

        # Lakukan konversi
        dst_ds = gdal.Translate(output_file, src_ds, options=translate_options)

        if dst_ds is None:
            print("ERROR: Konversi gagal!")
            return False

        # Tutup dataset
        dst_ds = None
        src_ds = None

        # Cek hasil
        if os.path.exists(output_file):
            input_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
            output_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            compression_achieved = (1 - output_size / input_size) * 100

            print(f"\n{'='*60}")
            print("KONVERSI BERHASIL!")
            print(f"{'='*60}")
            print(f"Ukuran input  : {input_size:.2f} MB")
            print(f"Ukuran output : {output_size:.2f} MB")
            print(f"Kompresi      : {compression_achieved:.1f}%")
            print(f"File output   : {output_file}")
            print(f"{'='*60}\n")
            return True
        else:
            print("ERROR: File output tidak ditemukan setelah konversi")
            return False

    except Exception as e:
        print(f"ERROR: Terjadi kesalahan saat konversi: {str(e)}")
        return False


def batch_convert(input_dir, output_dir=None, pattern="*.tif", **kwargs):
    """
    Konversi batch multiple GeoTIFF files ke ECW

    Parameters:
    -----------
    input_dir : str
        Directory yang berisi file GeoTIFF
    output_dir : str, optional
        Directory output (default: sama dengan input_dir)
    pattern : str
        Pattern file untuk diproses (default: "*.tif")
    **kwargs : dict
        Parameter tambahan untuk convert_geotiff_to_ecw
    """

    if output_dir is None:
        output_dir = input_dir

    # Buat output directory jika belum ada
    os.makedirs(output_dir, exist_ok=True)

    # Cari semua file yang match pattern
    input_path = Path(input_dir)
    files = list(input_path.glob(pattern))

    if not files:
        print(f"Tidak ada file yang ditemukan dengan pattern: {pattern}")
        return

    print(f"\nDitemukan {len(files)} file untuk dikonversi")
    print(f"{'='*60}\n")

    success_count = 0
    failed_count = 0

    for i, input_file in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] Processing: {input_file.name}")

        output_file = os.path.join(output_dir, input_file.stem + '.ecw')

        if convert_geotiff_to_ecw(str(input_file), output_file, **kwargs):
            success_count += 1
        else:
            failed_count += 1

    print(f"\n{'='*60}")
    print("BATCH CONVERSION SELESAI")
    print(f"{'='*60}")
    print(f"Berhasil: {success_count}")
    print(f"Gagal   : {failed_count}")
    print(f"Total   : {len(files)}")
    print(f"{'='*60}\n")


def main():
    """Main function"""

    parser = argparse.ArgumentParser(
        description='Konversi GeoTIFF ke ECW menggunakan GDAL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  # Konversi single file
  python geotiff_to_ecw.py input.tif

  # Konversi dengan output file spesifik
  python geotiff_to_ecw.py input.tif -o output.ecw

  # Konversi dengan rasio kompresi tinggi
  python geotiff_to_ecw.py input.tif -c 20

  # Batch convert semua file di directory
  python geotiff_to_ecw.py -d ./input_folder -od ./output_folder

  # Batch convert dengan pattern spesifik
  python geotiff_to_ecw.py -d ./data -p "*.tif" -c 15
        """
    )

    # Argument untuk single file atau batch
    parser.add_argument('input', nargs='?', help='File GeoTIFF input')
    parser.add_argument('-o', '--output', help='File ECW output')
    parser.add_argument('-d', '--directory', help='Directory input untuk batch conversion')
    parser.add_argument('-od', '--output-directory', help='Directory output untuk batch conversion')
    parser.add_argument('-p', '--pattern', default='*.tif',
                       help='Pattern file untuk batch conversion (default: *.tif)')

    # Parameter konversi
    parser.add_argument('-c', '--compression', type=int, default=10,
                       help='Rasio kompresi 1-100 (default: 10)')
    parser.add_argument('-t', '--type', default='JPEG2000',
                       choices=['JPEG2000', 'YUV'],
                       help='Tipe kompresi (default: JPEG2000)')
    parser.add_argument('-r', '--resampling', default='AVERAGE',
                       choices=['NEAREST', 'AVERAGE', 'BILINEAR', 'CUBIC'],
                       help='Metode resampling (default: AVERAGE)')

    args = parser.parse_args()

    # Cek dukungan ECW
    print("Mengecek dukungan ECW dalam GDAL...")
    if not check_ecw_support():
        print("\nMenggunakan alternatif: konversi ke JPEG2000 (.jp2)")
        print("Untuk menggunakan script ini dengan format JP2, ubah output extension ke .jp2")
        return 1

    # Konversi kwargs
    kwargs = {
        'compression_ratio': args.compression,
        'compression_type': args.type,
        'resampling': args.resampling
    }

    # Batch mode
    if args.directory:
        batch_convert(
            args.directory,
            args.output_directory,
            args.pattern,
            **kwargs
        )
    # Single file mode
    elif args.input:
        success = convert_geotiff_to_ecw(
            args.input,
            args.output,
            **kwargs
        )
        return 0 if success else 1
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
