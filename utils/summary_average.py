import os
import glob
import re

def parse_txt_file(filepath):
    """Parse a single txt file and extract dominant frequencies."""
    freqs = []
    with open(filepath, 'r') as f:
        for line in f.readlines():
            match = re.search(r'Dominant freq [XYZ] \(Hz\):\s*([\d.]+)', line)
            if match:
                freqs.append(float(match.group(1)))
    return freqs

def get_average_dominant_freq(folder):
    """Find the txt file in a folder and return average of all dominant frequencies."""
    txt_files = glob.glob(os.path.join(folder, '*.txt'))
    if len(txt_files) == 0:
        return None, "No .txt file found"
    if len(txt_files) > 1:
        return None, f"Multiple .txt files found: {txt_files}"
    
    freqs = parse_txt_file(txt_files[0])
    if not freqs:
        return None, "No dominant frequencies found in file"
    
    return sum(freqs) / len(freqs), None

def process_all_subfolders(root_dir):
    """Walk through all subfolders and compute average dominant frequency per subfolder."""
    results = {}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip the root folder itself
        if dirpath == root_dir:
            continue
        
        txt_files = [f for f in filenames if f.endswith('.txt')]
        if not txt_files:
            continue

        avg_freq, error = get_average_dominant_freq(dirpath)
        rel_path = os.path.relpath(dirpath, root_dir)

        if error:
            print(f"[SKIP] {rel_path}: {error}")
        else:
            results[rel_path] = avg_freq
            print(f"{rel_path}: Average dominant frequency = {avg_freq:.3f} Hz")

    return results

if __name__ == "__main__":
    root_dir = "E:/IMU_only/results/standardized/frac"  # CHANGE THIS to your root folder

    print(f"Scanning subfolders in: {root_dir}\n")
    results = process_all_subfolders(root_dir)

    print(f"\n--- Summary ---")
    for folder, avg in results.items():
        print(f"{folder}: {avg:.3f} Hz")