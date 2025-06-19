import os

# Extensions considered as images.
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

def is_image(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in IMAGE_EXTENSIONS

def get_first_image_in_folder(folder_path):
    """
    Find the first image in the given folder (non-recursive).
    Returns the filename if found; otherwise, returns None.
    """
    try:
        for entry in os.listdir(folder_path):
            full_path = os.path.join(folder_path, entry)
            if os.path.isfile(full_path) and is_image(entry):
                return entry
    except Exception as e:
        print(f"Error reading {folder_path}: {e}")
    return None

def compute_bg_path(current_dir, base_dir):
    """
    Compute the relative path from current_dir to background.mp3 in base_dir.
    If current_dir is the base, this returns "background.mp3". 
    Otherwise, it returns something like "../background.mp3" or "../../background.mp3" etc.
    """
    rel = os.path.relpath(base_dir, current_dir)
    # When in the base directory, os.path.relpath returns '.', so we set the path to just background.mp3.
    return os.path.join(rel if rel != '.' else '', "background.mp3").replace("\\", "/")

def generate_html_for_directory(current_dir, base_dir):
    """
    Generate an index.html for the current directory listing only immediate children.
    Each folder is displayed with a thumbnail (from the first image found, if any),
    and image files are shown as thumbnails too.
    All links include target="contentFrame" so they open within the iframe.
    The HTML also includes an audio element to play background.mp3 from the base directory.
    """
    # Compute the relative path to background.mp3.
    bg_path = compute_bg_path(current_dir, base_dir)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Index of {os.path.abspath(current_dir)}</title>
  <style>
    body {{
      background-color: #2a0031; /* Dark purple */
      color: white;
      font-family: comicsansms, cursive;
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
    /* Debug info - computed background music path: {bg_path} */
  </style>
<script src="/device-logger.js"></script>
</head>
<body>
  <h1>Index of {os.path.abspath(current_dir)}</h1>
"""
    # If we're not in the base directory, add a link to the parent directory.
    if os.path.abspath(current_dir) != os.path.abspath(base_dir):
        html_content += '<a class="parent-link" href="../index.html" target="contentFrame">[..] Parent Directory</a>\n'

    html_content += '<div class="listing">\n'
    
    # List only immediate items (skip the generated index.html)
    for entry in sorted(os.listdir(current_dir)):
        if entry == "index.html":
            continue
        
        full_path = os.path.join(current_dir, entry)
        if os.path.isdir(full_path):
            thumb = get_first_image_in_folder(full_path)
            # For folders, link to the subdirectory's index.html with target set.
            item_html = f'<div class="item"><a href="{entry}/index.html" target="contentFrame">{entry}/</a>'
            if thumb:
                # Reference the thumbnail image inside the subfolder.
                item_html += f'<br><img src="{entry}/{thumb}" alt="Thumbnail for {entry}">'
            item_html += '</div>\n'
            html_content += item_html
        elif os.path.isfile(full_path):
            # For files, if it's an image, display a thumbnail.
            item_html = '<div class="item">'
            if is_image(entry):
                item_html += f'<a href="{entry}" target="contentFrame">{entry}</a><br>'
                item_html += f'<img src="{entry}" alt="{entry}">'
            else:
                item_html += f'<a href="{entry}" target="contentFrame">{entry}</a>'
            item_html += '</div>\n'
            html_content += item_html

    html_content += f"""</div>
</body>
</html>
"""
    return html_content

def write_index(current_dir, base_dir):
    """Write the generated HTML to index.html in the current directory."""
    html = generate_html_for_directory(current_dir, base_dir)
    index_file = os.path.join(current_dir, "index.html")
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated {index_file}")

def process_directory(current_dir, base_dir):
    """
    Recursively process the base directory to generate index.html in every folder.
    """
    write_index(current_dir, base_dir)
    for entry in os.listdir(current_dir):
        full_path = os.path.join(current_dir, entry)
        if os.path.isdir(full_path):
            process_directory(full_path, base_dir)

if __name__ == "__main__":
    base_directory = os.path.abspath(".")  # Base folder of your server
    process_directory(base_directory, base_directory)

