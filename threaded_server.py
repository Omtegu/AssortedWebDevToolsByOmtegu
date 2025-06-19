import os
import time
import threading
import difflib
import psutil
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuration ---
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
FOLDER_SIZES_FILE = "folder_sizes.json"

# --- Global Counters & Stats ---
stats = {
    "dirs": 0,
    "changed": 0,
    "same": 0,
    "errors": 0,
}
eval_times = {}           # {folder: evaluation time in sec}
similarities = {}         # {folder: similarity ratio (if index existed)}
folder_cpu_cycles = {}    # {folder: estimated CPU cycles used}
folder_mem_diff = {}      # {folder: memory difference in bytes during processing}
folder_size_diff = {}     # {folder: absolute difference in bytes from cached size}
folder_act_log = {}       # {folder: "acted" or "skipped"}

# Group changes by parent folder (only counting acted folders)
changes_by_parent = {}

# Global counter for estimated CPU cycles totals
total_cpu_cycles = 0

# Locks for thread safety.
stats_lock = threading.Lock()
counter_lock = threading.Lock()

# Get our process handle for memory and CPU timing.
process = psutil.Process(os.getpid())

def is_image(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in IMAGE_EXTENSIONS

def get_first_image_in_folder(folder_path):
    try:
        with os.scandir(folder_path) as it:
            for entry in it:
                if entry.is_file() and is_image(entry.name):
                    return entry.name
    except Exception as e:
        print(f"Error reading {folder_path}: {e}")
    return None

def compute_bg_path(current_dir, base_dir):
    rel = os.path.relpath(base_dir, current_dir)
    return os.path.join(rel if rel != '.' else '', "background.mp3").replace("\\", "/")

def generate_html_for_directory(current_dir, base_dir):
    bg_path = compute_bg_path(current_dir, base_dir)
    current_abs = os.path.abspath(current_dir)
    base_abs = os.path.abspath(base_dir)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Index of {current_abs}</title>
  <style>
    body {{
      background-color: #2a0031;
      color: white;
      font-family: Arial, sans-serif;
      padding: 20px;
    }}
    h1 {{
      text-align: center;
    }}
    .item {{
      margin: 15px;
      padding: 10px;
      border: 1px solid #555;
      display: inline-block;
      vertical-align: top;
      width: 200px;
      text-align: center;
    }}
    .item img {{
      max-width: 180px;
      max-height: 180px;
      display: block;
      margin: 0 auto 10px;
    }}
    a {{
      color: white;
      text-decoration: none;
      font-weight: bold;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .parent-link {{
      margin-bottom: 20px;
      display: block;
    }}
    /* Background music path: {bg_path} */
  </style>
</head>
<body>
  <h1>Index of {current_abs}</h1>
"""
    if current_abs != base_abs:
        html_content += '<a class="parent-link" href="../index.html" target="contentFrame">[..] Parent Directory</a>\n'
    html_content += '<div class="listing">\n'
    try:
        entries = sorted(os.scandir(current_dir), key=lambda e: e.name.lower())
    except Exception as e:
        print(f"Error listing directory {current_dir}: {e}")
        entries = []
    for entry in entries:
        if entry.name == "index.html":
            continue
        if entry.is_dir():
            thumb = get_first_image_in_folder(os.path.join(current_dir, entry.name))
            item_html = f'<div class="item"><a href="{entry.name}/index.html" target="contentFrame">{entry.name}/</a>'
            if thumb:
                item_html += f'<br><img src="{entry.name}/{thumb}" alt="Thumbnail for {entry.name}">'
            item_html += '</div>\n'
            html_content += item_html
        elif entry.is_file():
            item_html = '<div class="item">'
            if is_image(entry.name):
                item_html += f'<a href="{entry.name}" target="contentFrame">{entry.name}</a><br>'
                item_html += f'<img src="{entry.name}" alt="{entry.name}">'
            else:
                item_html += f'<a href="{entry.name}" target="contentFrame">{entry.name}</a>'
            item_html += '</div>\n'
            html_content += item_html
    html_content += """</div>
</body>
</html>
"""
    return html_content

def compute_folder_size(folder_path):
    """Compute total size (in bytes) of immediate files in a folder."""
    total = 0
    try:
        with os.scandir(folder_path) as it:
            for entry in it:
                if entry.is_file():
                    try:
                        total += entry.stat().st_size
                    except Exception as e:
                        print(f"Error getting size for {entry.path}: {e}")
    except Exception as e:
        print(f"Error scanning folder {folder_path}: {e}")
    return total

# --- Load/Save Folder Size Cache ---
def load_folder_sizes():
    if os.path.exists(FOLDER_SIZES_FILE):
        try:
            with open(FOLDER_SIZES_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {FOLDER_SIZES_FILE}: {e}")
    return {}

def save_folder_sizes(sizes):
    try:
        with open(FOLDER_SIZES_FILE, "w") as f:
            json.dump(sizes, f, indent=2)
    except Exception as e:
        print(f"Error saving {FOLDER_SIZES_FILE}: {e}")

# --- Main Processing Function ---
def write_index(current_dir, base_dir, folder_sizes):
    global total_cpu_cycles
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    start_mem = process.memory_info().rss

    current_folder_size = compute_folder_size(current_dir)
    skip_folder = False
    prev_size = folder_sizes.get(current_dir, None)
    # Determine bytes changed (if previous size exists)
    if prev_size is not None:
        size_diff = abs(current_folder_size - prev_size)
    else:
        size_diff = current_folder_size

    # Check if folder size is unchanged.
    if prev_size is not None and current_folder_size == prev_size:
        skip_folder = True

    if skip_folder:
        with stats_lock:
            stats["same"] += 1
        folder_act_log[current_dir] = "skipped"
        duration = time.perf_counter() - start_wall
        eval_times[current_dir] = duration
        similarities[current_dir] = 1.0  # Assume 100% similarity
        folder_size_diff[current_dir] = 0
    else:
        # Process the folder normally: generate and write index.html.
        html = generate_html_for_directory(current_dir, base_dir)
        index_file = os.path.join(current_dir, "index.html")
        sim_ratio = None
        try:
            # Update folder size cache immediately since size has changed
            folder_sizes[current_dir] = current_folder_size
            if os.path.exists(index_file):
                with open(index_file, "r", encoding="utf-8") as f:
                    existing = f.read()
                sim_ratio = difflib.SequenceMatcher(None, existing, html).ratio()
                if existing == html:
                    with stats_lock:
                        stats["same"] += 1
                    folder_act_log[current_dir] = "skipped"
                    duration = time.perf_counter() - start_wall
                    eval_times[current_dir] = duration
                    similarities[current_dir] = sim_ratio
                    folder_size_diff[current_dir] = size_diff
                    return
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(html)
            with stats_lock:
                stats["changed"] += 1
            parent = os.path.dirname(current_dir)
            with stats_lock:
                changes_by_parent[parent] = changes_by_parent.get(parent, 0) + 1
            folder_act_log[current_dir] = "acted"
            sim_ratio = sim_ratio if sim_ratio is not None else 0.0
            eval_times[current_dir] = time.perf_counter() - start_wall
            similarities[current_dir] = sim_ratio
            folder_size_diff[current_dir] = size_diff
            print(f"Generated {index_file} in {eval_times[current_dir]:.6f} sec (sim: {similarities[current_dir]:.6f}), bytes changed: {size_diff}", flush=True)
        except Exception as e:
            print(f"Error writing {index_file}: {e}", flush=True)
            with stats_lock:
                stats["errors"] += 1

    end_cpu = time.process_time()
    end_mem = process.memory_info().rss
    cpu_time = end_cpu - start_cpu
    # Estimate CPU cycles: cpu_time (sec) * CPU frequency in Hz.
    try:
        freq_info = psutil.cpu_freq()
        if freq_info is not None and freq_info.current is not None:
            freq = freq_info.current * 1e6  # MHz to Hz
        else:
            freq = 2.5e9  # Default to 2.5 GHz if unavailable
    except Exception as e:
        print(f"Error retrieving CPU frequency: {e}, using default 2.5 GHz", flush=True)
        freq = 2.5e9
    cpu_cycles = cpu_time * freq
    mem_diff = max(0, end_mem - start_mem)
    folder_cpu_cycles[current_dir] = cpu_cycles
    folder_mem_diff[current_dir] = mem_diff
    with counter_lock:
        total_cpu_cycles += cpu_cycles

# --- Main Execution ---
if __name__ == "__main__":
    overall_start = time.time()
    base_directory = os.path.abspath(".")
    # Load folder sizes cache.
    folder_sizes = load_folder_sizes()

    # Gather all directories using os.walk.
    directories = []
    for root, dirs, _ in os.walk(base_directory):
        directories.append(root)

    futures = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for d in directories:
            futures.append(executor.submit(write_index, d, base_directory, folder_sizes))
        # Simple polling loop to print progress.
        total = len(futures)
        try:
            while True:
                done_count = sum(1 for f in futures if f.done())
                print(f"Progress: {done_count}/{total} tasks completed", flush=True)
                if done_count >= total:
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Exiting progress loop...", flush=True)

    overall_time = time.time() - overall_start
    # Save updated folder sizes cache.
    save_folder_sizes(folder_sizes)

    # Compute summary stats.
    top_longest = sorted(eval_times.items(), key=lambda x: x[1], reverse=True)[:3]
    top_cpu = sorted(folder_cpu_cycles.items(), key=lambda x: x[1], reverse=True)[:3]
    top_mem = sorted(folder_mem_diff.items(), key=lambda x: x[1], reverse=True)[:3]
    top_size_diff = sorted(folder_size_diff.items(), key=lambda x: x[1], reverse=True)[:3]
    top_similar = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:3]
    most_changes_parent = max(changes_by_parent.items(), key=lambda x: x[1]) if changes_by_parent else ("N/A", 0)
    max_ram_mb = process.memory_info().rss / (1024 * 1024)

    acted = [folder for folder, action in folder_act_log.items() if action == "acted"]
    skipped = [folder for folder, action in folder_act_log.items() if action == "skipped"]

    print("\n--- Processing Complete ---", flush=True)
    print(f"Total Time Taken: {overall_time:.6f} seconds", flush=True)
    print(f"Total Directories Processed: {len(directories)}", flush=True)
    print(f"Index Files Changed/Created: {stats['changed']}", flush=True)
    print(f"Index Files Unchanged: {stats['same']}", flush=True)
    print(f"Errors Encountered: {stats['errors']}", flush=True)
    print(f"Parent folder with most index file changes: '{most_changes_parent[0]}' with {most_changes_parent[1]} changes", flush=True)
    print(f"Total Estimated CPU Cycles: {total_cpu_cycles:.0f}", flush=True)
    print(f"Peak Process RAM Usage: {max_ram_mb:.2f} MB", flush=True)
    print("\nFolders Acted On (processed):", flush=True)
    for folder in acted:
        print(f"  {folder}", flush=True)
    print("\nFolders Skipped (unchanged):", flush=True)
    for folder in skipped:
        print(f"  {folder}", flush=True)
    print("\nTop 3 Longest Evaluation Times:")
    for folder, duration in top_longest:
        print(f"  {folder}: {duration:.6f} sec", flush=True)
    print("\nTop 3 Folders by Estimated CPU Cycles:")
    for folder, cycles in top_cpu:
        print(f"  {folder}: {cycles:.0f} cycles", flush=True)
    print("\nTop 3 Folders by Memory Increase:")
    for folder, mem in top_mem:
        print(f"  {folder}: {mem} bytes", flush=True)
    print("\nTop 3 Folders by Bytes Changed:")
    for folder, diff in top_size_diff:
        print(f"  {folder}: {diff} bytes", flush=True)
    print("\nTop 3 Most Similar Folders (unchanged or nearly unchanged):")
    for folder, sim in top_similar:
        print(f"  {folder}: Similarity Ratio = {sim:.6f}", flush=True)
