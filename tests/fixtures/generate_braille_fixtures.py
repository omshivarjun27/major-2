"""
Generate synthetic braille test fixture images.

Run once to create test/fixtures/braille/*.png
Uses OpenCV to draw dots at braille-standard spacing.
"""

import os

import numpy as np

try:
    import cv2
    CV2 = True
except ImportError:
    CV2 = False


def _draw_dots(img, dots_list, origin, spacing=15, dot_r=4):
    """Draw braille cells starting at origin."""
    x0, y0 = origin
    for cell_idx, dots in enumerate(dots_list):
        cx = x0 + cell_idx * int(spacing * 2.5)
        for i, active in enumerate(dots):
            if not active:
                continue
            col = 0 if i < 3 else 1
            row = i % 3
            px = cx + col * spacing
            py = y0 + row * spacing
            if CV2:
                cv2.circle(img, (px, py), dot_r, 0, -1)
            else:
                img[py - dot_r:py + dot_r, px - dot_r:px + dot_r] = 0


def generate_fixtures(output_dir: str = "tests/fixtures/braille"):
    os.makedirs(output_dir, exist_ok=True)

    # Braille patterns for "a" through "f"
    patterns = {
        "sample_a": [[True, False, False, False, False, False]],  # a
        "sample_ab": [
            [True, False, False, False, False, False],  # a
            [True, True, False, False, False, False],   # b
        ],
        "sample_hello": [
            [True, True, False, False, True, False],    # h
            [True, False, False, False, True, False],    # e
            [True, True, True, False, False, False],     # l
            [True, True, True, False, False, False],     # l
            [True, False, True, False, True, False],     # o
        ],
        "sample_dots_6": [
            [True, True, True, True, True, True],       # all dots
        ],
        "sample_empty": [],  # no dots
        "sample_noisy": [   # a with noise (still valid)
            [True, False, False, False, False, False],
            [False, True, False, True, False, False],   # i
        ],
    }

    for name, cells in patterns.items():
        h, w = 120, max(200, len(cells) * 50 + 60)
        img = np.ones((h, w), dtype=np.uint8) * 240  # Light gray background

        if cells:
            _draw_dots(img, cells, origin=(30, 20), spacing=15, dot_r=4)

        path = os.path.join(output_dir, f"{name}.png")
        if CV2:
            cv2.imwrite(path, img)
        else:
            # Fallback: save as raw numpy
            np.save(path.replace(".png", ".npy"), img)

        print(f"  Created: {path}")

    print(f"Generated {len(patterns)} braille fixture images in {output_dir}/")


if __name__ == "__main__":
    generate_fixtures()
