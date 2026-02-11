import zipfile
import os
from collections import Counter
from pathlib import Path

def analyze_food_photos(zip_path='food.zip'):
    """
    Parse the food.zip file and collect statistics on photos.
    
    Args:
        zip_path: Path to the zip file (default: 'food.zip')
    
    Returns:
        dict: Statistics about the photos
    """
    
    if not os.path.exists(zip_path):
        print(f"Error: {zip_path} not found!")
        return None
    
    stats = {
        'total_files': 0,
        'total_photos': 0,
        'file_types': Counter(),
        'photo_extensions': Counter(),
        'folders': set(),
        'file_list': []
    }
    
    # Common image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif'}
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            # Get list of all files in the zip
            file_list = zip_file.namelist()
            
            for file_path in file_list:
                # Skip directories
                if file_path.endswith('/'):
                    stats['folders'].add(file_path)
                    continue
                
                stats['total_files'] += 1
                
                # Get file extension
                ext = Path(file_path).suffix.lower()
                stats['file_types'][ext] += 1
                
                # Check if it's an image
                if ext in image_extensions:
                    stats['total_photos'] += 1
                    stats['photo_extensions'][ext] += 1
                
                # Store file info
                file_info = zip_file.getinfo(file_path)
                stats['file_list'].append({
                    'name': file_path,
                    'size': file_info.file_size,
                    'compressed_size': file_info.compress_size,
                    'extension': ext
                })
    
    except zipfile.BadZipFile:
        print(f"Error: {zip_path} is not a valid zip file!")
        return None
    except Exception as e:
        print(f"Error reading zip file: {e}")
        return None
    
    return stats


def print_stats(stats):
    """Print formatted statistics about the photos."""
    
    if stats is None:
        return
    
    print("=" * 60)
    print("FOOD.ZIP PHOTO ANALYSIS")
    print("=" * 60)
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total photos: {stats['total_photos']}")
    print(f"  Folders: {len(stats['folders'])}")
    
    print(f"\n📷 PHOTO TYPES:")
    if stats['photo_extensions']:
        for ext, count in stats['photo_extensions'].most_common():
            percentage = (count / stats['total_photos'] * 100) if stats['total_photos'] > 0 else 0
            print(f"  {ext:10} : {count:4} photos ({percentage:.1f}%)")
    else:
        print("  No photos found!")
    
    print(f"\n📁 ALL FILE TYPES:")
    for ext, count in stats['file_types'].most_common():
        print(f"  {ext if ext else '(no extension)':10} : {count:4} files")
    
    if stats['folders']:
        print(f"\n📂 FOLDERS:")
        for folder in sorted(stats['folders'])[:10]:  # Show first 10 folders
            print(f"  {folder}")
        if len(stats['folders']) > 10:
            print(f"  ... and {len(stats['folders']) - 10} more")
    
    # Calculate total size
    total_size = sum(f['size'] for f in stats['file_list'])
    total_compressed = sum(f['compressed_size'] for f in stats['file_list'])
    
    print(f"\n💾 STORAGE:")
    print(f"  Uncompressed: {total_size / (1024*1024):.2f} MB")
    print(f"  Compressed: {total_compressed / (1024*1024):.2f} MB")
    print(f"  Compression ratio: {(1 - total_compressed/total_size)*100:.1f}%" if total_size > 0 else "  N/A")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Analyze the food.zip file
    print("Analyzing food.zip...\n")
    stats = analyze_food_photos('food.zip')
    
    if stats:
        print_stats(stats)
        
        # Optional: Save detailed file list to a text file
        save_report = input("\nSave detailed report to file? (y/n): ").lower()
        if save_report == 'y':
            with open('food_photos_report.txt', 'w') as f:
                f.write("DETAILED FILE LIST\n")
                f.write("=" * 80 + "\n\n")
                for file_info in stats['file_list']:
                    f.write(f"{file_info['name']}\n")
                    f.write(f"  Size: {file_info['size']:,} bytes\n")
                    f.write(f"  Type: {file_info['extension']}\n\n")
            print("Report saved to: food_photos_report.txt")