#!/usr/bin/python3

import os
import subprocess
from sys import stdout
from tqdm import tqdm
from PIL import Image, ImageFont, ImageDraw

# Ensure working directories exist
os.makedirs("frames-bad-apple", exist_ok=True)
os.makedirs("ascii-frames", exist_ok=True)
os.makedirs("ascii-images", exist_ok=True)

# 1) Extract PNG frames from video using ffmpeg
print("Extracting frames from video...")
subprocess.run([
    "ffmpeg", "-y", "-i", "bad-apple.mp4", "-vf", "fps=30", "frames-bad-apple/frame_%04d.png"
])

# 2) Convert PNG frames to ASCII text
frames = sorted(os.listdir("frames-bad-apple"))
for index, frame in enumerate(tqdm(frames, desc="Converting frames to ASCII"), start=1):
    proc = subprocess.run(["ascii-image-converter", f"frames-bad-apple/{frame}"], capture_output=True)
    text = proc.stdout.decode("utf-8")
    # write ascii output with numeric filenames
    with open(f"ascii-frames/{index}.txt", "w") as f:
        f.write(text)

# 3) Render ASCII text files to PNG images using Pillow
print("Rendering ASCII text to PNG images...")
font_paths = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]
font = None
for p in font_paths:
    if os.path.exists(p):
        try:
            font = ImageFont.truetype(p, size=12)
            break
        except Exception:
            font = None
if font is None:
    font = ImageFont.load_default()

ascii_files = sorted(
    [f for f in os.listdir("ascii-frames") if f.endswith(".txt") and os.path.splitext(f)[0].isdigit()],
    key=lambda n: int(os.path.splitext(n)[0])
)
for fname in tqdm(ascii_files, desc="Rendering ASCII -> PNG"):
    path = os.path.join("ascii-frames", fname)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read().rstrip("\n")
    lines = content.splitlines() or [""]
    # derive output stem: numeric filename without extension
    stem = os.path.splitext(fname)[0]
    # estimate size
    max_cols = max(len(line) for line in lines)
    # get character size using ImageDraw.textbbox where available,
    # fall back to font.getsize or a safe default for older/newer Pillow
    _tmp_img = Image.new("RGB", (1, 1))
    _tmp_draw = ImageDraw.Draw(_tmp_img)
    try:
        bbox = _tmp_draw.textbbox((0, 0), "A", font=font)
        char_w = bbox[2] - bbox[0]
        char_h = bbox[3] - bbox[1]
    except AttributeError:
        try:
            char_w, char_h = font.getsize("A")
        except Exception:
            char_w, char_h = (8, 16)
    img_w = max(1, max_cols * char_w)
    img_h = max(1, len(lines) * char_h)
    # Ensure dimensions are divisible by 2 for libx264/ffmpeg
    if img_w % 2 != 0:
        img_w += 1
    if img_h % 2 != 0:
        img_h += 1
    img = Image.new("RGB", (img_w, img_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # draw text
    draw.multiline_text((0, 0), content, font=font, fill=(0, 0, 0), spacing=0)
    out_path = os.path.join("ascii-images", f"{stem}.png")
    img.save(out_path)

# 4) Assemble PNG images into video with ffmpeg
print("Assembling PNG images into video with ffmpeg...")
subprocess.run([
    "ffmpeg", "-y", "-framerate", "30", "-i", "ascii-images/frame_%04d.png",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "output.mp4"
])

print("Done: output.mp4")
        
