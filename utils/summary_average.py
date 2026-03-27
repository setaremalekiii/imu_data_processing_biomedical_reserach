import os
import re

def parse_txt_file(filepath):
    data = {
        'mean_ax': None, 'mean_ay': None, 'mean_az': None,
        'freq_X': None, 'freq_Y': None, 'freq_Z': None
    }
    with open(filepath, 'r') as f:
        content = f.read()
    
    patterns = {
        'mean_ax': r'Mean ax \(m/s\^2\):\s*([-\d.]+)',
        'mean_ay': r'Mean ay \(m/s\^2\):\s*([-\d.]+)',
        'mean_az': r'Mean az \(m/s\^2\):\s*([-\d.]+)',
        'freq_X':  r'Dominant freq X \(Hz\):\s*([\d.]+)',
        'freq_Y':  r'Dominant freq Y \(Hz\):\s*([\d.]+)',
        'freq_Z':  r'Dominant freq Z \(Hz\):\s*([\d.]+)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            data[key] = float(match.group(1))
        else:
            print(f"  WARNING: could not find '{key}' in {filepath}")
    
    return data

if __name__ == "__main__":
    root_dir = "E:/IMU_only/results/standardized/softCal"

    all_data = {
        'mean_ax': [], 'mean_ay': [], 'mean_az': [],
        'freq_X': [], 'freq_Y': [], 'freq_Z': []
    }

    txt_files_found = []

    # find all txt files one level deep (each subfolder has one txt)
    for subfolder in os.listdir(root_dir):
        subfolder_path = os.path.join(root_dir, subfolder)
        if os.path.isdir(subfolder_path):
            for f in os.listdir(subfolder_path):
                if f.endswith('.txt'):
                    full_path = os.path.join(subfolder_path, f)
                    txt_files_found.append(full_path)
                    print(f"Found: {full_path}")
                    parsed = parse_txt_file(full_path)
                    for key in all_data:
                        if parsed[key] is not None:
                            all_data[key].append(parsed[key])

    print(f"\nTotal txt files parsed: {len(txt_files_found)}\n")

    for key, values in all_data.items():
        print(f"  {key}: {values}")
    output_path = os.path.join(root_dir, "averages_summary_over_10_trials.txt")
    with open(output_path, 'w') as f:
        f.write(f"Total txt files parsed: {len(txt_files_found)}\n\n")
        f.write(f"Average ax:          {sum(all_data['mean_ax']) / len(all_data['mean_ax']):.4f} m/s^2\n")
        f.write(f"Average ay:          {sum(all_data['mean_ay']) / len(all_data['mean_ay']):.4f} m/s^2\n")
        f.write(f"Average az:          {sum(all_data['mean_az']) / len(all_data['mean_az']):.4f} m/s^2\n")
        f.write(f"Average Dominant X:  {sum(all_data['freq_X']) / len(all_data['freq_X']):.3f} Hz\n")
        f.write(f"Average Dominant Y:  {sum(all_data['freq_Y']) / len(all_data['freq_Y']):.3f} Hz\n")
        f.write(f"Average Dominant Z:  {sum(all_data['freq_Z']) / len(all_data['freq_Z']):.3f} Hz\n")
    
    print(f"Results saved to: {output_path}")