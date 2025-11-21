#!/usr/bin/env python3
"""
Global Mapper Batch Converter - Helper Script
Membuat dan execute Global Mapper script untuk batch convert GeoTIFF ke ECW

Requirements:
    - Global Mapper 25+ terinstall
    - Python 3.x
    - File template: global_mapper_batch_template.gms

Author: Claude Code
Date: 2025-11-11
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

# Default paths
DEFAULT_INPUT_FOLDER = r"D:\Ayah\sipukat\merged"
DEFAULT_OUTPUT_FOLDER = None  # None = sama dengan input folder
TEMPLATE_FILE = "global_mapper_batch_template.gms"
OUTPUT_SCRIPT = "batch_convert_generated.gms"

# Global Mapper executable paths (common locations)
GLOBAL_MAPPER_PATHS = [
    r"C:\Program Files\GlobalMapper25\global_mapper.exe",
    r"C:\Program Files\GlobalMapper24\global_mapper.exe",
    r"C:\Program Files\GlobalMapper23\global_mapper.exe",
    r"C:\Program Files\GlobalMapper22.1_64bit\global_mapper.exe",
    r"C:\Program Files\GlobalMapper22\global_mapper.exe",
    r"C:\Program Files (x86)\GlobalMapper25\global_mapper.exe",
    r"C:\Program Files (x86)\GlobalMapper24\global_mapper.exe",
    r"C:\Program Files (x86)\GlobalMapper23\global_mapper.exe",
    r"C:\Program Files (x86)\GlobalMapper22.1_64bit\global_mapper.exe",
    r"C:\Program Files (x86)\GlobalMapper22\global_mapper.exe",
]


def find_global_mapper_exe() -> Optional[str]:
    """
    Cari executable Global Mapper di lokasi umum

    Returns:
        str: Path ke global_mapper.exe atau None jika tidak ditemukan
    """
    for path in GLOBAL_MAPPER_PATHS:
        if os.path.exists(path):
            return path

    # Coba cari di PATH
    try:
        result = subprocess.run(['where', 'global_mapper.exe'],
                              capture_output=True,
                              text=True,
                              check=True)
        if result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except:
        pass

    return None


def find_geotiff_files(input_folder: str, recursive: bool = False) -> List[Path]:
    """
    Cari semua file GeoTIFF di folder

    Parameters:
        input_folder: Path ke folder input
        recursive: Jika True, cari di semua subfolder

    Returns:
        List of Path objects untuk file GeoTIFF
    """
    input_path = Path(input_folder)

    if not input_path.exists():
        raise FileNotFoundError(f"Folder tidak ditemukan: {input_folder}")

    extensions = ['*.tif', '*.tiff', '*.TIF', '*.TIFF']
    files = []

    for ext in extensions:
        if recursive:
            files.extend(input_path.rglob(ext))
        else:
            files.extend(input_path.glob(ext))

    return sorted(set(files))  # Remove duplicates and sort


def generate_gms_script(input_files: List[Path],
                       output_folder: Optional[str] = None,
                       compression_ratio: int = 10,
                       ecw_version: int = 3,
                       template_file: str = TEMPLATE_FILE,
                       output_script: str = OUTPUT_SCRIPT) -> str:
    """
    Generate Global Mapper script (.gms) dari template

    Parameters:
        input_files: List of input GeoTIFF files
        output_folder: Folder untuk output ECW (None = sama dengan input)
        compression_ratio: Rasio kompresi ECW (default: 10)
        ecw_version: Versi ECW format (2 atau 3, default: 3)
        template_file: Path ke template .gms
        output_script: Path untuk output .gms yang di-generate

    Returns:
        str: Path ke generated script file
    """

    # Baca template
    if not os.path.exists(template_file):
        raise FileNotFoundError(f"Template file tidak ditemukan: {template_file}")

    with open(template_file, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Update compression settings di template
    template_content = template_content.replace(
        'EXPORT_ECW_COMPRESSION_RATIO=10',
        f'EXPORT_ECW_COMPRESSION_RATIO={compression_ratio}'
    )
    template_content = template_content.replace(
        'EXPORT_ECW_VERSION=3',
        f'EXPORT_ECW_VERSION={ecw_version}'
    )

    # Generate file processing blocks
    file_blocks = []

    for input_file in input_files:
        # Tentukan output path
        if output_folder:
            output_path = Path(output_folder) / (input_file.stem + '.ecw')
        else:
            output_path = input_file.parent / (input_file.stem + '.ecw')

        # Convert ke Windows path format untuk Global Mapper
        input_str = str(input_file).replace('/', '\\')
        output_str = str(output_path).replace('/', '\\')

        # Create block untuk file ini
        block = f'''
// Processing: {input_file.name}
IMPORT FILENAME="{input_str}"

EXPORT_ECW FILENAME="{output_str}" \\
    SPATIAL_RES_METERS=CURRENT \\
    FILL_GAPS=NO \\
    GEN_WORLD_FILE=NO

UNLOAD_ALL
'''
        file_blocks.append(block)

    # Insert file blocks ke template
    files_content = '\n'.join(file_blocks)

    # Replace marker di template
    generated_content = template_content.replace(
        '// ===== MARKER: FILES_START =====\n// Files akan diinsert di sini oleh Python script\n// ===== MARKER: FILES_END =====',
        f'// ===== MARKER: FILES_START =====\n{files_content}\n// ===== MARKER: FILES_END ====='
    )

    # Write generated script
    with open(output_script, 'w', encoding='utf-8') as f:
        f.write(generated_content)

    print(f"\n{'='*70}")
    print(f"Generated Global Mapper script: {output_script}")
    print(f"{'='*70}")
    print(f"Total files to process: {len(input_files)}")
    print(f"Compression ratio: {compression_ratio}:1")
    print(f"ECW version: {ecw_version}")
    print(f"{'='*70}\n")

    return output_script


def execute_global_mapper(script_path: str,
                         global_mapper_exe: Optional[str] = None,
                         wait: bool = True) -> bool:
    """
    Execute Global Mapper dengan script

    Parameters:
        script_path: Path ke .gms script
        global_mapper_exe: Path ke global_mapper.exe (None = auto-detect)
        wait: Jika True, tunggu sampai selesai

    Returns:
        bool: True jika berhasil execute
    """

    # Find Global Mapper executable
    if global_mapper_exe is None:
        global_mapper_exe = find_global_mapper_exe()

    if not global_mapper_exe:
        print("ERROR: Global Mapper executable tidak ditemukan!")
        print("\nCoba install Global Mapper atau tentukan path manual dengan:")
        print(f"  python {sys.argv[0]} --gm-path \"C:\\path\\to\\global_mapper.exe\"")
        return False

    if not os.path.exists(global_mapper_exe):
        print(f"ERROR: Global Mapper executable tidak ada: {global_mapper_exe}")
        return False

    print(f"\n{'='*70}")
    print(f"Executing Global Mapper...")
    print(f"{'='*70}")
    print(f"Executable: {global_mapper_exe}")
    print(f"Script: {script_path}")
    print(f"{'='*70}\n")

    try:
        # Execute Global Mapper dengan script
        # Format command: global_mapper.exe script_file.gms
        cmd = [global_mapper_exe, os.path.abspath(script_path)]

        if wait:
            result = subprocess.run(cmd, check=True)
            print("\n[OK] Global Mapper execution selesai!")
            return result.returncode == 0
        else:
            subprocess.Popen(cmd)
            print("\n[OK] Global Mapper started (running in background)")
            return True

    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Global Mapper execution failed: {e}")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False


def main():
    """Main function"""

    parser = argparse.ArgumentParser(
        description='Global Mapper Batch Converter - Generate dan execute batch conversion script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:

  # Generate script untuk semua file di folder default
  python global_mapper_batch.py

  # Generate dan langsung execute
  python global_mapper_batch.py --execute

  # Specify folder input dan output
  python global_mapper_batch.py -i "D:\\Data\\Input" -o "D:\\Data\\Output"

  # Generate dengan kompresi tinggi
  python global_mapper_batch.py -c 20 --execute

  # Recursive scan (include subfolder)
  python global_mapper_batch.py -i "D:\\Data" --recursive

  # Manual specify Global Mapper path
  python global_mapper_batch.py --gm-path "C:\\Program Files\\GlobalMapper25\\global_mapper.exe" --execute

  # Hanya generate script (tidak execute)
  python global_mapper_batch.py -i "D:\\Data" --no-execute
        """
    )

    # Input/Output arguments
    parser.add_argument('-i', '--input', default=DEFAULT_INPUT_FOLDER,
                       help=f'Folder input berisi GeoTIFF (default: {DEFAULT_INPUT_FOLDER})')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT_FOLDER,
                       help='Folder output untuk ECW (default: sama dengan input)')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='Scan subfolder juga')

    # Conversion parameters
    parser.add_argument('-c', '--compression', type=int, default=10,
                       help='Rasio kompresi ECW (default: 10)')
    parser.add_argument('-v', '--ecw-version', type=int, default=3, choices=[2, 3],
                       help='Versi ECW format (default: 3)')

    # Script generation
    parser.add_argument('-t', '--template', default=TEMPLATE_FILE,
                       help=f'Template .gms file (default: {TEMPLATE_FILE})')
    parser.add_argument('-s', '--script-output', default=OUTPUT_SCRIPT,
                       help=f'Output .gms file (default: {OUTPUT_SCRIPT})')

    # Execution control
    parser.add_argument('-e', '--execute', action='store_true',
                       help='Execute Global Mapper dengan script setelah generate')
    parser.add_argument('--no-execute', action='store_true',
                       help='Hanya generate script, jangan execute')
    parser.add_argument('--gm-path', default=None,
                       help='Path manual ke global_mapper.exe')
    parser.add_argument('--no-wait', action='store_true',
                       help='Jangan tunggu Global Mapper selesai (run in background)')

    # List files only
    parser.add_argument('-l', '--list-only', action='store_true',
                       help='Hanya tampilkan list file yang akan diproses')

    args = parser.parse_args()

    try:
        # Find GeoTIFF files
        print(f"\n{'='*70}")
        print(f"Scanning untuk GeoTIFF files...")
        print(f"{'='*70}")
        print(f"Input folder: {args.input}")
        print(f"Recursive: {'Yes' if args.recursive else 'No'}")
        print(f"{'='*70}\n")

        input_files = find_geotiff_files(args.input, args.recursive)

        if not input_files:
            print("ERROR: Tidak ada file GeoTIFF ditemukan!")
            return 1

        print(f"Ditemukan {len(input_files)} file GeoTIFF:\n")

        total_size = 0
        for i, file in enumerate(input_files, 1):
            size_mb = os.path.getsize(file) / (1024 * 1024)
            total_size += size_mb
            print(f"  {i:3d}. {file.name:50s} ({size_mb:8.2f} MB)")

        print(f"\n{'='*70}")
        print(f"Total: {len(input_files)} files, {total_size:.2f} MB")
        print(f"{'='*70}\n")

        # List only mode
        if args.list_only:
            return 0

        # Generate script
        script_path = generate_gms_script(
            input_files=input_files,
            output_folder=args.output,
            compression_ratio=args.compression,
            ecw_version=args.ecw_version,
            template_file=args.template,
            output_script=args.script_output
        )

        print(f"[OK] Script berhasil di-generate: {script_path}\n")

        # Execute Global Mapper?
        if args.no_execute:
            print("Script generation selesai. Untuk execute:")
            print(f"  1. Buka Global Mapper")
            print(f"  2. File > Run Script")
            print(f"  3. Pilih: {os.path.abspath(script_path)}")
            return 0

        # Auto-execute jika --execute flag
        if args.execute:
            success = execute_global_mapper(
                script_path=script_path,
                global_mapper_exe=args.gm_path,
                wait=not args.no_wait
            )
            return 0 if success else 1

        # Default: tanya user
        print("\nScript sudah siap. Pilihan:")
        print("  1. Execute Global Mapper sekarang (otomatis)")
        print("  2. Manual - Jalankan dari Global Mapper (File > Run Script)")
        print("  0. Batal")

        choice = input("\nPilihan Anda (1/2/0): ").strip()

        if choice == '1':
            success = execute_global_mapper(
                script_path=script_path,
                global_mapper_exe=args.gm_path,
                wait=not args.no_wait
            )
            return 0 if success else 1
        elif choice == '2':
            print(f"\nUntuk execute manual:")
            print(f"  1. Buka Global Mapper")
            print(f"  2. File > Run Script")
            print(f"  3. Pilih: {os.path.abspath(script_path)}")
            return 0
        else:
            print("\nBatal.")
            return 0

    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: Terjadi kesalahan: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
