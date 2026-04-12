"""
deep_scan/annotator.py — Screenshot annotation with Pillow.

Draws semi-transparent red rectangles on screenshots to highlight
detected dark pattern elements. Each box includes a category label.
"""

from __future__ import annotations

import base64
import io
import logging

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    logger.warning("Pillow not installed — screenshot annotation disabled")


# Annotation colors
HIGHLIGHT_COLOR = (220, 38, 38, 80)   # Semi-transparent red fill
BORDER_COLOR = (220, 38, 38, 255)     # Solid red border
LABEL_BG = (220, 38, 38, 200)         # Dark red label background
LABEL_TEXT = (255, 255, 255, 255)      # White label text


def annotate_screenshot(
    screenshot_b64: str,
    detections: list[dict],
    viewport_width: int = 1280,
    viewport_height: int = 800,
) -> str:
    """Annotate a screenshot with red highlight boxes on detected elements.

    Args:
        screenshot_b64: Base64-encoded PNG screenshot.
        detections: List of detection dicts (must have 'bounding_rect' and 'category').
        viewport_width: Browser viewport width used during capture.
        viewport_height: Browser viewport height used during capture.

    Returns:
        Base64-encoded annotated PNG screenshot.
    """
    if not HAS_PILLOW or not screenshot_b64:
        return screenshot_b64

    try:
        # Decode the screenshot
        img_bytes = base64.b64decode(screenshot_b64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        img_w, img_h = img.size

        # Scale factors (screenshot pixel size may differ from viewport)
        scale_x = img_w / viewport_width
        scale_y = img_h / viewport_height

        # Create overlay for semi-transparent boxes
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Try to load a font, fall back to default
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except (OSError, IOError):
            font = ImageFont.load_default()

        annotations_drawn = 0

        for det in detections:
            rect = det.get("bounding_rect")
            if not rect:
                continue

            x = float(rect.get("x", 0)) * scale_x
            y = float(rect.get("y", 0)) * scale_y
            w = float(rect.get("width", 0)) * scale_x
            h = float(rect.get("height", 0)) * scale_y

            # Skip elements outside viewport or too small
            if w < 2 or h < 2 or x + w < 0 or y + h < 0:
                continue
            if x > img_w or y > img_h:
                continue

            # Draw semi-transparent fill
            draw.rectangle([x, y, x + w, y + h], fill=HIGHLIGHT_COLOR, outline=BORDER_COLOR, width=2)

            # Draw category label
            category = det.get("category", "unknown").replace("_", " ").title()
            label = f" {category} "

            bbox = font.getbbox(label)
            label_w = bbox[2] - bbox[0]
            label_h = bbox[3] - bbox[1]

            label_x = max(0, x)
            label_y = max(0, y - label_h - 4)

            draw.rectangle(
                [label_x, label_y, label_x + label_w + 4, label_y + label_h + 4],
                fill=LABEL_BG,
            )
            draw.text((label_x + 2, label_y + 1), label, fill=LABEL_TEXT, font=font)

            annotations_drawn += 1

        # Composite overlay onto original
        result = Image.alpha_composite(img, overlay)

        # Encode back to base64
        buf = io.BytesIO()
        result.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    except Exception as e:
        logger.warning("Failed to annotate screenshot: %s", e)
        return screenshot_b64
