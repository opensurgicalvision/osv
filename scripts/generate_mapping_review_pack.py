"""Generate deterministic Clinical Review Pack for anatomical class mapping verification."""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ZIP_PATH = Path(
    r"C:\Users\aleksandr_stefanin\AppData\Local\Temp\claude\c--Users-aleksandr-stefanin-projects-ai-community\d5ec600b-1ecd-472e-b914-82ce9d672edd\scratchpad\cholecseg8k_work\raw\data\CholecSeg8k.zip"
)

OUT_DIR = Path(r"c:\Users\aleksandr_stefanin\projects\ai-community\scratchpad\mapping_review")
BRAIN_DIR = Path(
    r"C:\Users\aleksandr_stefanin\.gemini\antigravity\brain\ee6eeaa3-d01a-4230-98a5-5698f66b2e66\mapping_review"
)

CLASS_DEFINITIONS: dict[int, dict[str, Any]] = {
    0: {"name": "Black Background", "ws": 50, "rgb": (127, 127, 127), "hex": "#7F7F7F"},
    1: {"name": "Abdominal Wall", "ws": 11, "rgb": (210, 140, 140), "hex": "#D28C8C"},
    2: {"name": "Liver", "ws": 21, "rgb": (255, 114, 114), "hex": "#FF7272"},
    3: {"name": "Gastrointestinal Tract", "ws": 13, "rgb": (231, 70, 156), "hex": "#E7469C"},
    4: {"name": "Fat", "ws": 12, "rgb": (186, 183, 75), "hex": "#BAB74B"},
    5: {"name": "Grasper", "ws": 31, "rgb": (170, 255, 0), "hex": "#AAFF00"},
    6: {"name": "Connective Tissue", "ws": 23, "rgb": (255, 85, 0), "hex": "#FF5500"},
    7: {"name": "Blood", "ws": 24, "rgb": (255, 0, 0), "hex": "#FF0000"},
    8: {"name": "Cystic Duct", "ws": 25, "rgb": (255, 255, 0), "hex": "#FFFF00"},
    9: {"name": "L-hook Electrocautery", "ws": 32, "rgb": (169, 255, 184), "hex": "#A9FFB8"},
    10: {"name": "Gallbladder", "ws": 22, "rgb": (255, 160, 165), "hex": "#FFA0A5"},
    11: {"name": "Hepatic Vein", "ws": 33, "rgb": (0, 50, 128), "hex": "#003280"},
    12: {"name": "Liver Ligament", "ws": 5, "rgb": (111, 74, 0), "hex": "#6F4A00"},
}

WS_TO_CLASS = {info["ws"]: (cid, info) for cid, info in CLASS_DEFINITIONS.items()}

WS_RE = re.compile(r"^CholecSeg8k/(video\d+)/(video\d+_\d+)/frame_(\d+)_endo_watershed_mask\.png$")


def scan_and_select_frames(zf: zipfile.ZipFile) -> list[dict[str, Any]]:
    """Scan all frames and select clean, stratified high-area candidates."""
    records: list[dict[str, Any]] = []

    names = [n for n in zf.namelist() if WS_RE.match(n)]
    print(f"Total masks in zip: {len(names)}")

    frame_data: list[dict[str, Any]] = []

    for name in names:
        match = WS_RE.match(name)
        assert match is not None
        vid, clip, fid = match.groups()
        with zf.open(name) as fh:
            arr = np.array(Image.open(io.BytesIO(fh.read())))
            ch0 = arr[:, :, 0] if len(arr.shape) == 3 else arr
            vals, counts = np.unique(ch0, return_counts=True)
            cd = dict(zip(vals.tolist(), counts.tolist()))
            frame_data.append({
                "video": vid,
                "clip": clip,
                "frame": fid,
                "mask_path": name,
                "counts": cd,
            })

    # Strategy: Select representative cases with significant pixel areas
    # 1. ws=5 (Liver Ligament) - video09
    f_ws5 = max([f for f in frame_data if 5 in f["counts"] and f["video"] == "video09"], key=lambda f: f["counts"][5])
    
    # 2. ws=25 (Cystic Duct) - video17
    f_cd_v17 = max([f for f in frame_data if 25 in f["counts"] and f["video"] == "video17"], key=lambda f: f["counts"][25])

    # 3. ws=25 (Cystic Duct) + ws=32 (L-hook) + ws=24 (Blood) in video01
    f_v01 = max([f for f in frame_data if 25 in f["counts"] and f["video"] == "video01"], key=lambda f: f["counts"][25])

    # 4. ws=33 (Hepatic Vein) - video12 (top vascular structure)
    f_hv_v12 = max([f for f in frame_data if 33 in f["counts"] and f["video"] == "video12"], key=lambda f: f["counts"][33])

    # 5. ws=23 (Connective Tissue) + ws=22 (Gallbladder) - video12
    f_ct_v12 = max([f for f in frame_data if 23 in f["counts"] and f["video"] == "video12"], key=lambda f: f["counts"][23])

    # 6. ws=31 (Grasper) + ws=13 (GI Tract) + ws=11 (Abdominal Wall) - video28
    f_gr_v28 = max([f for f in frame_data if 31 in f["counts"] and f["video"] == "video28"], key=lambda f: f["counts"][31])

    # 7. ws=24 (Blood) - video01 (high hemorrhage area)
    f_bl_v01 = max([f for f in frame_data if 24 in f["counts"] and f["video"] == "video01"], key=lambda f: f["counts"][24])

    selected = [
        {"tag": "01_cystic_duct_lhook_v01", "title": "Frame 1: Cystic Duct, L-hook, Grasper & Blood (video01)", "f": f_v01},
        {"tag": "02_cystic_duct_v17", "title": "Frame 2: High-Area Cystic Duct in Calot's Triangle (video17)", "f": f_cd_v17},
        {"tag": "03_hepatic_vein_v12", "title": "Frame 3: Hepatic Vein Vascular Segment (video12)", "f": f_hv_v12},
        {"tag": "04_liver_ligament_v09", "title": "Frame 4: Liver Ligament Falciforme / Teres (video09)", "f": f_ws5},
        {"tag": "05_connective_tissue_v12", "title": "Frame 5: Connective Tissue, Gallbladder & Liver (video12)", "f": f_ct_v12},
        {"tag": "06_grasper_gi_fat_v28", "title": "Frame 6: Grasper, GI Tract, Abdominal Wall & Fat (video28)", "f": f_gr_v28},
        {"tag": "07_blood_hemorrhage_v01", "title": "Frame 7: Blood Pool & Surgical Field (video01)", "f": f_bl_v01},
    ]

    return selected


def render_composite(
    zf: zipfile.ZipFile,
    item: dict[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    f = item["f"]
    vid, clip, fid = f["video"], f["clip"], f["frame"]

    # Image paths in zip
    raw_img_path = f"CholecSeg8k/{vid}/{clip}/frame_{fid}_endo.png"
    color_mask_path = f"CholecSeg8k/{vid}/{clip}/frame_{fid}_endo_color_mask.png"
    ws_mask_path = f"CholecSeg8k/{vid}/{clip}/frame_{fid}_endo_watershed_mask.png"

    raw_img = Image.open(io.BytesIO(zf.read(raw_img_path))).convert("RGB")
    color_mask = Image.open(io.BytesIO(zf.read(color_mask_path))).convert("RGB")
    ws_img = Image.open(io.BytesIO(zf.read(ws_mask_path)))

    ws_arr = np.array(ws_img)
    ch0 = ws_arr[:, :, 0] if len(ws_arr.shape) == 3 else ws_arr

    # Compute EXACT pixel counts and percentages directly from ch0
    vals, counts = np.unique(ch0, return_counts=True)
    total_px = ch0.size

    pixel_table: list[dict[str, Any]] = []
    for val, cnt in sorted(zip(vals.tolist(), counts.tolist()), key=lambda x: -x[1]):
        pct = (cnt / total_px) * 100.0
        if val in WS_TO_CLASS:
            cid, cinfo = WS_TO_CLASS[val]
            pixel_table.append({
                "class_id": cid,
                "name": cinfo["name"],
                "raw_ws": val,
                "rgb": cinfo["rgb"],
                "hex": cinfo["hex"],
                "pixel_count": cnt,
                "area_percent": round(pct, 2),
            })
        else:
            label = "Void / Boundary" if val == 0 else ("Watershed Line" if val == 255 else f"Unknown ({val})")
            pixel_table.append({
                "class_id": -1,
                "name": label,
                "raw_ws": val,
                "rgb": (0, 0, 0) if val == 0 else (255, 255, 255),
                "hex": "#000000" if val == 0 else "#FFFFFF",
                "pixel_count": cnt,
                "area_percent": round(pct, 2),
            })

    # Create 3-panel image (Raw, Color Mask, Overlay)
    w, h = raw_img.size  # 854, 480
    
    # Create overlay on raw
    overlay_arr = np.array(raw_img).copy()
    for row in pixel_table:
        if row["class_id"] >= 0:
            mask_bin = (ch0 == row["raw_ws"])
            color_rgb = np.array(row["rgb"], dtype=np.uint8)
            overlay_arr[mask_bin] = (overlay_arr[mask_bin] * 0.45 + color_rgb * 0.55).astype(np.uint8)
    overlay_img = Image.fromarray(overlay_arr)

    # Layout: Top header (60px), 3 panels side by side (854*3 = 2562), Bottom info table (260px)
    comp_w = 2562
    header_h = 70
    table_h = 240
    comp_h = header_h + h + table_h

    composite = Image.new("RGB", (comp_w, comp_h), color=(24, 26, 27))
    draw = ImageDraw.Draw(composite)

    # Load default font
    font_large = ImageFont.load_default()
    font_med = ImageFont.load_default()

    # Draw Header
    draw.rectangle([(0, 0), (comp_w, header_h)], fill=(32, 35, 38))
    header_text = f"{item['title']}  |  Path: CholecSeg8k/{vid}/{clip}/frame_{fid}_endo.png  |  Total Pixels: {total_px:,} ({w}x{h})"
    draw.text((20, 22), header_text, fill=(255, 255, 255), font=font_large)

    # Paste 3 panels
    composite.paste(raw_img, (0, header_h))
    composite.paste(color_mask, (854, header_h))
    composite.paste(overlay_img, (854 * 2, header_h))

    # Panel Subtitles
    draw.rectangle([(10, header_h + 10), (280, header_h + 38)], fill=(0, 0, 0, 180))
    draw.text((20, header_h + 15), "1. RAW ENDOSCOPIC FRAME", fill=(255, 255, 255), font=font_med)

    draw.rectangle([(854 + 10, header_h + 10), (854 + 280, header_h + 38)], fill=(0, 0, 0, 180))
    draw.text((854 + 20, header_h + 15), "2. ORIGINAL COLOR MASK", fill=(255, 255, 255), font=font_med)

    draw.rectangle([(854 * 2 + 10, header_h + 10), (854 * 2 + 300, header_h + 38)], fill=(0, 0, 0, 180))
    draw.text((854 * 2 + 20, header_h + 15), "3. ANNOTATED MAPPING OVERLAY", fill=(255, 255, 255), font=font_med)

    # Draw bottom Table
    table_top = header_h + h + 10
    draw.rectangle([(10, table_top), (comp_w - 10, comp_h - 10)], fill=(18, 20, 22), outline=(60, 64, 68))
    draw.text((30, table_top + 10), "EXACT GROUND-TRUTH CLASS INVENTORY (Computed directly from watershed mask numpy array):", fill=(0, 220, 255), font=font_med)

    col_x = [30, 80, 320, 480, 680, 860, 1020]
    headers = ["ID", "CLASS NAME", "RAW WS VALUE", "RGB COLOR", "PIXEL COUNT", "FRAME AREA %", "COLOR SWATCH"]
    y_pos = table_top + 35

    draw.line([(25, y_pos - 3), (comp_w - 25, y_pos - 3)], fill=(70, 75, 80), width=1)
    for cx, htext in zip(col_x, headers):
        draw.text((cx, y_pos), htext, fill=(180, 185, 190), font=font_med)
    draw.line([(25, y_pos + 18), (comp_w - 25, y_pos + 18)], fill=(70, 75, 80), width=1)

    y_pos += 24
    for row in pixel_table:
        cid_str = str(row["class_id"]) if row["class_id"] >= 0 else "-"
        draw.text((col_x[0], y_pos), cid_str, fill=(255, 255, 255), font=font_med)
        draw.text((col_x[1], y_pos), row["name"], fill=(255, 255, 255), font=font_med)
        draw.text((col_x[2], y_pos), f"ws = {row['raw_ws']}", fill=(255, 220, 100), font=font_med)
        draw.text((col_x[3], y_pos), f"RGB {row['rgb']}", fill=(200, 200, 200), font=font_med)
        draw.text((col_x[4], y_pos), f"{row['pixel_count']:,} px", fill=(100, 255, 150), font=font_med)
        draw.text((col_x[5], y_pos), f"{row['area_percent']}%", fill=(255, 255, 255), font=font_med)
        
        # Draw color swatch box
        draw.rectangle([(col_x[6], y_pos + 1), (col_x[6] + 60, y_pos + 13)], fill=row["rgb"], outline=(255, 255, 255))
        y_pos += 18
        if y_pos > comp_h - 25:
            break

    metadata = {
        "tag": item["tag"],
        "title": item["title"],
        "video": vid,
        "clip": clip,
        "frame": fid,
        "path": f"CholecSeg8k/{vid}/{clip}/frame_{fid}_endo.png",
        "total_pixels": total_px,
        "classes": pixel_table,
    }

    return composite, metadata


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Opening {ZIP_PATH}...")
    with zipfile.ZipFile(ZIP_PATH) as zf:
        selected_items = scan_and_select_frames(zf)
        print(f"Selected {len(selected_items)} representative frames.")

        all_metadata = []

        for item in selected_items:
            comp_img, meta = render_composite(zf, item)
            out_file = OUT_DIR / f"{item['tag']}.png"
            brain_file = BRAIN_DIR / f"{item['tag']}.png"

            comp_img.save(out_file, quality=95)
            comp_img.save(brain_file, quality=95)

            all_metadata.append(meta)
            print(f"Saved: {out_file.name}")

    # Write inventory JSON
    inv_path = OUT_DIR / "inventory.json"
    inv_path.write_text(json.dumps(all_metadata, indent=2), encoding="utf-8")
    (BRAIN_DIR / "inventory.json").write_text(json.dumps(all_metadata, indent=2), encoding="utf-8")
    print(f"Saved inventory: {inv_path}")


if __name__ == "__main__":
    main()
