#!/usr/bin/env python3
"""
Terminal YouTube ASCII Player with Color, Audio, Subtitles, and Scaling

Enhancements include:
- Color output (256-color or 24-bit truecolor)
- Expanded Unicode character options
- Actual audio playback with aplay
"""

import cv2
import numpy as np
import shutil
import subprocess
import sys
import time
import wave
import os

def rgb_to_256(r, g, b):
    """Convert RGB values to xterm-256 color code."""
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + int((r - 8) / 247 * 24)
    r = max(0, min(5, int((r / 255) * 5)))
    g = max(0, min(5, int((g / 255) * 5)))
    b = max(0, min(5, int((b / 255) * 5)))
    return 16 + 36 * r + 6 * g + b

def download_video(url, download_subs):
    """Download video and subtitles using yt-dlp."""
    cmd = ["yt-dlp", "-o", "video.mp4", "--recode-video", "mp4", url]
    if download_subs:
        cmd.extend(["--write-sub", "--sub-lang", "en", "--convert-subs", "srt"])
    subprocess.run(cmd, check=True)

def extract_audio():
    """Extract audio to WAV file."""
    subprocess.run(["ffmpeg", "-y", "-i", "video.mp4", "-ac", "1", "-ar", "44100", "audio.wav"], check=True)

def frame_to_ascii(frame, term_cols, term_rows, ascii_chars, color_mode):
    """Convert frame to ASCII with color codes."""
    h, w = frame.shape[:2]
    aspect = 0.55
    scale_w = term_cols / w
    scale_h = term_rows / (h * aspect)
    scale = min(scale_w, scale_h)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale * aspect))
    
    color_resized = cv2.resize(frame, (new_w, new_h))
    gray = cv2.cvtColor(color_resized, cv2.COLOR_BGR2GRAY)
    chars = []
    num_chars = len(ascii_chars)
    
    for y in range(new_h):
        line = []
        for x in range(new_w):
            val = gray[y, x]
            idx = min(int(val / 256 * num_chars), num_chars - 1)
            char = ascii_chars[idx]
            b, g, r = color_resized[y, x]
            
            if color_mode == "truecolor":
                line.append(f"\033[38;2;{r};{g};{b}m{char}")
            elif color_mode == "256":
                code = rgb_to_256(r, g, b)
                line.append(f"\033[38;5;{code}m{char}")
            else:
                line.append(char)
        chars.append("".join(line) + "\033[0m")
    return "\n".join(chars)

def main():
    url = input("Enter YouTube URL: ").strip()
    if not url:
        sys.exit("No URL provided")

    # Character set selection
    print("\nChoose character set:")
    print("A) Basic  B) Unicode Blocks  C) Detailed Unicode")
    choice = input("Choice [A/B/C]: ").upper()
    ascii_chars = (
        "1234567890-=~!@#$%^&*()_+`qwertyuiop[]\\asdfghjkl;'zxcvbnm,./" 
        if choice == "A" else
        " ░▒▓█" if choice == "B" else
        " ▁▂▃▄▅▆▇█"
    )

    # Color mode selection
    print("\nColor mode:")
    print("A) None  B) 256-color  C) Truecolor")
    color_mode = ["none", "256", "truecolor"][
        min(2, ord(input("Choice [A/B/C]: ").upper()) - ord('A'))
    ]

    # Audio method
    print("\nAudio method:")
    print("A) Beep  B) Sox  C) Eject  D) None  E) Play audio")
    audio_choice = input("Choice [A-E]: ").upper()
    if audio_choice not in "ABCDE":
        audio_choice = "D"

    # Subtitles
    subs = []
    if input("\nDownload subtitles? [y/N]: ").lower() == "y":
        download_video(url, True)
        for f in ["video.en.srt", "video.srt"]:
            if os.path.exists(f):
                subs = parse_srt(f)
                break

    # Video processing
    download_video(url, False)
    extract_audio()

    # Audio playback setup
    audio_proc = None
    if audio_choice == "E":
        audio_proc = subprocess.Popen(["aplay", "audio.wav"])

    cap = cv2.VideoCapture("video.mp4")
    fps = cap.get(cv2.CAP_PROP_FPS)
    delay = 1 / fps if fps > 0 else 1/24

    try:
        while cap.isOpened():
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            # Generate ASCII art with color
            term_cols, term_rows = shutil.get_terminal_size()
            term_rows -= 3 if subs else 0
            ascii_art = frame_to_ascii(frame, term_cols, term_rows, ascii_chars, color_mode)

            # Display
            print("\033[H\033[J" + ascii_art)
            
            # Timing control
            elapsed = time.time() - start_time
            if elapsed < delay:
                time.sleep(delay - elapsed)
    finally:
        cap.release()
        if audio_proc:
            audio_proc.terminate()
        for f in ["video.mp4", "audio.wav"]:
            os.remove(f)

if __name__ == "__main__":
    main()
