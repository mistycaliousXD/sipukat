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

# Import untuk GUI file selection
try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

# Default folder untuk file selection
DEFAULT_FOLDER = r"D:\Ayah\sipukat\merged"


def select_file_gui(initial_dir=None, multiple=False):
    """
    Pilih file menggunakan GUI dialog (tkinter)

    Parameters:
    -----------
    initial_dir : str
        Folder awal untuk file dialog
    multiple : bool
        Jika True, bisa memilih multiple files

    Returns:
    --------
    str or list : Path file yang dipilih, atau None jika dibatalkan
    """
    if not TKINTER_AVAILABLE:
        return None

    root = tk.Tk()
    root.withdraw()  # Sembunyikan main window
    root.attributes('-topmost', True)  # Bring dialog to front

    if initial_dir is None or not os.path.exists(initial_dir):
        initial_dir = os.path.expanduser("~")

    filetypes = [
        ('GeoTIFF files', '*.tif *.tiff'),
        ('All files', '*.*')
    ]

    if multiple:
        files = filedialog.askopenfilenames(
            title='Pilih File GeoTIFF',
            initialdir=initial_dir,
            filetypes=filetypes
        )
        root.destroy()
        return list(files) if files else None
    else:
        file = filedialog.askopenfilename(
            title='Pilih File GeoTIFF',
            initialdir=initial_dir,
            filetypes=filetypes
        )
        root.destroy()
        return file if file else None


def select_file_console(folder_path, multiple=False):
    """
    Pilih file menggunakan console menu (fallback jika tkinter tidak ada)

    Parameters:
    -----------
    folder_path : str
        Path ke folder yang berisi file
    multiple : bool
        Jika True, bisa memilih multiple files

    Returns:
    --------
    str or list : Path file yang dipilih, atau None jika dibatalkan
    """
    if not os.path.exists(folder_path):
        print(f"ERROR: Folder tidak ditemukan: {folder_path}")
        return None

    # Cari semua file TIFF di folder
    tiff_files = []
    for ext in ['*.tif', '*.tiff', '*.TIF', '*.TIFF']:
        tiff_files.extend(Path(folder_path).glob(ext))

    tiff_files = sorted(tiff_files)

    if not tiff_files:
        print(f"Tidak ada file TIFF ditemukan di: {folder_path}")
        return None

    print(f"\n{'='*60}")
    print(f"File TIFF di folder: {folder_path}")
    print(f"{'='*60}")

    for i, file in enumerate(tiff_files, 1):
        size_mb = os.path.getsize(file) / (1024 * 1024)
        print(f"{i:3d}. {file.name:50s} ({size_mb:8.2f} MB)")

    print(f"{'='*60}")

    if multiple:
        print("\nMasukkan nomor file yang ingin dikonversi (pisahkan dengan koma)")
        print("Contoh: 1,3,5 atau 1-5 atau ketik 'all' untuk semua file")
        choice = input("Pilihan Anda: ").strip()

        if choice.lower() == 'all':
            return [str(f) for f in tiff_files]

        selected_files = []
        try:
            # Parse input (support comma separated dan ranges)
            parts = choice.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    # Range (e.g., 1-5)
                    start, end = map(int, part.split('-'))
                    for i in range(start, end + 1):
                        if 1 <= i <= len(tiff_files):
                            selected_files.append(str(tiff_files[i - 1]))
                else:
                    # Single number
                    idx = int(part)
                    if 1 <= idx <= len(tiff_files):
                        selected_files.append(str(tiff_files[idx - 1]))

            return selected_files if selected_files else None
        except ValueError:
            print("ERROR: Input tidak valid")
            return None
    else:
        choice = input("\nMasukkan nomor file (atau 0 untuk batal): ").strip()

        try:
            idx = int(choice)
            if idx == 0:
                return None
            if 1 <= idx <= len(tiff_files):
                return str(tiff_files[idx - 1])
            else:
                print(f"ERROR: Nomor harus antara 1-{len(tiff_files)}")
                return None
        except ValueError:
            print("ERROR: Input harus berupa angka")
            return None


def select_files_interactive(folder_path=None, multiple=False, use_gui=True):
    """
    Pilih file secara interaktif (GUI atau console)

    Parameters:
    -----------
    folder_path : str
        Folder default untuk pencarian file
    multiple : bool
        Jika True, bisa memilih multiple files
    use_gui : bool
        Jika True, gunakan GUI (tkinter) jika tersedia

    Returns:
    --------
    str or list : Path file yang dipilih
    """
    if folder_path is None:
        folder_path = DEFAULT_FOLDER

    # Coba gunakan GUI jika tersedia dan diminta
    if use_gui and TKINTER_AVAILABLE:
        print("Membuka file dialog...")
        result = select_file_gui(folder_path, multiple)
        if result:
            return result

    # Fallback ke console selection
    return select_file_console(folder_path, multiple)


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
  # Mode interaktif - pilih file dari dialog/menu
  python geotiff_to_ecw.py -i

  # Mode interaktif - pilih multiple files
  python geotiff_to_ecw.py -i -m

  # Mode interaktif - pilih dari folder spesifik
  python geotiff_to_ecw.py -i -f "D:\\Data\\GeoTIFF"

  # Mode interaktif - console only (tanpa GUI)
  python geotiff_to_ecw.py -i --no-gui

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

    # Argument untuk mode interaktif
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='Mode interaktif untuk memilih file')
    parser.add_argument('-f', '--folder', default=DEFAULT_FOLDER,
                       help=f'Folder default untuk file selection (default: {DEFAULT_FOLDER})')
    parser.add_argument('-m', '--multiple', action='store_true',
                       help='Pilih multiple files dalam mode interaktif')
    parser.add_argument('--no-gui', action='store_true',
                       help='Disable GUI, gunakan console selection')

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

    # Mode Interaktif
    if args.interactive:
        print("\n" + "="*60)
        print("MODE INTERAKTIF - KONVERSI GEOTIFF KE ECW")
        print("="*60)

        selected_files = select_files_interactive(
            folder_path=args.folder,
            multiple=args.multiple,
            use_gui=not args.no_gui
        )

        if not selected_files:
            print("\nTidak ada file yang dipilih. Keluar.")
            return 0

        # Konversi ke list jika single file
        if isinstance(selected_files, str):
            selected_files = [selected_files]

        print(f"\n{len(selected_files)} file dipilih untuk dikonversi")

        # Tanya output directory
        if args.output_directory:
            output_dir = args.output_directory
        else:
            print("\nPilih lokasi output:")
            print("1. Sama dengan folder input")
            print("2. Folder lain (akan ditanyakan)")
            choice = input("Pilihan (1/2, default=1): ").strip() or "1"

            if choice == "2":
                if not args.no_gui and TKINTER_AVAILABLE:
                    root = tk.Tk()
                    root.withdraw()
                    output_dir = filedialog.askdirectory(
                        title='Pilih Folder Output',
                        initialdir=args.folder
                    )
                    root.destroy()
                    if not output_dir:
                        print("Tidak ada folder dipilih. Menggunakan folder input.")
                        output_dir = None
                else:
                    output_dir = input("Masukkan path folder output: ").strip()
                    if not output_dir or not os.path.exists(output_dir):
                        print("Path tidak valid. Menggunakan folder input.")
                        output_dir = None
            else:
                output_dir = None

        # Proses setiap file
        success_count = 0
        failed_count = 0

        for i, input_file in enumerate(selected_files, 1):
            print(f"\n{'='*60}")
            print(f"[{i}/{len(selected_files)}] Processing: {os.path.basename(input_file)}")
            print(f"{'='*60}")

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir,
                                          os.path.splitext(os.path.basename(input_file))[0] + '.ecw')
            else:
                output_file = os.path.splitext(input_file)[0] + '.ecw'

            if convert_geotiff_to_ecw(input_file, output_file, **kwargs):
                success_count += 1
            else:
                failed_count += 1

        # Summary
        print(f"\n{'='*60}")
        print("KONVERSI SELESAI")
        print(f"{'='*60}")
        print(f"Berhasil : {success_count}")
        print(f"Gagal    : {failed_count}")
        print(f"Total    : {len(selected_files)}")
        print(f"{'='*60}\n")

        return 0 if failed_count == 0 else 1

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
