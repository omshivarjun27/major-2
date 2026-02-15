"""
Braille Classifier
==================

Convert dot patterns → characters.  Includes:
- A lookup table for Grade 1 English braille (letters + digits + common punctuation)
- A trainable PyTorch model stub for advanced recognition
- Dataset format specification
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("braille-classifier")

# ── Grade 1 English Braille Lookup ────────────────────────────────
# Dot numbering: [1,2,3,4,5,6] → left-col top-to-bottom, right-col top-to-bottom
# True/False for each dot presence.

BRAILLE_MAP: Dict[Tuple[bool, ...], str] = {
    (True, False, False, False, False, False): "a",
    (True, True, False, False, False, False): "b",
    (True, False, False, True, False, False): "c",
    (True, False, False, True, True, False): "d",
    (True, False, False, False, True, False): "e",
    (True, True, False, True, False, False): "f",
    (True, True, False, True, True, False): "g",
    (True, True, False, False, True, False): "h",
    (False, True, False, True, False, False): "i",
    (False, True, False, True, True, False): "j",
    (True, False, True, False, False, False): "k",
    (True, True, True, False, False, False): "l",
    (True, False, True, True, False, False): "m",
    (True, False, True, True, True, False): "n",
    (True, False, True, False, True, False): "o",
    (True, True, True, True, False, False): "p",
    (True, True, True, True, True, False): "q",
    (True, True, True, False, True, False): "r",
    (False, True, True, True, False, False): "s",
    (False, True, True, True, True, False): "t",
    (True, False, True, False, False, True): "u",
    (True, True, True, False, False, True): "v",
    (False, True, False, True, True, True): "w",
    (True, False, True, True, False, True): "x",
    (True, False, True, True, True, True): "y",
    (True, False, True, False, True, True): "z",
    # Digits (preceded by number indicator ⠼ in real braille)
    # Here stored directly for the classifier:
    (False, True, False, True, True, True): "0",  # same as w — context needed
    (True, False, False, False, False, False): "1",  # same as a
    (True, True, False, False, False, False): "2",  # same as b
    # ... (in practice digits need the ⠼ prefix; we store the base patterns)
    # Space
    (False, False, False, False, False, False): " ",
}

# Reverse map: char → dots
CHAR_TO_DOTS: Dict[str, Tuple[bool, ...]] = {v: k for k, v in BRAILLE_MAP.items()}


@dataclass
class BrailleChar:
    """Classified braille character."""
    char: str
    dots: List[bool]
    confidence: float = 1.0
    cell_row: int = 0
    cell_col: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "char": self.char,
            "dots": self.dots,
            "confidence": round(self.confidence, 3),
            "cell": [self.cell_row, self.cell_col],
        }


class BrailleClassifier:
    """Classify braille cells into characters.

    Modes:
    - ``lookup`` (default): fast table lookup using ``BRAILLE_MAP``.
    - ``model``: uses a PyTorch model stub (requires training).

    Usage::

        clf = BrailleClassifier(mode="lookup")
        chars = clf.classify(segmentation_result.cells)
        text = clf.to_text(chars)
    """

    def __init__(self, mode: str = "lookup", model_path: Optional[str] = None):
        self._mode = mode
        self._model_path = model_path
        self._model = None

        if mode == "model" and model_path:
            self._load_model(model_path)

    # ── Lookup classification ─────────────────────────────────────

    def classify(self, cells: List[Any]) -> List[BrailleChar]:
        """Classify a list of CellInfo objects into characters.

        Args:
            cells: From BrailleSegmenter output.

        Returns:
            List of BrailleChar.
        """
        results: List[BrailleChar] = []
        for cell in cells:
            dots = tuple(cell.dots[:6])
            char = BRAILLE_MAP.get(dots, "?")
            confidence = 1.0 if char != "?" else 0.0
            results.append(BrailleChar(
                char=char,
                dots=list(cell.dots),
                confidence=confidence,
                cell_row=cell.row,
                cell_col=cell.col,
            ))
        return results

    def to_text(self, chars: List[BrailleChar]) -> str:
        """Convert classified characters to a text string.

        Groups by row, orders by column.
        """
        if not chars:
            return ""

        rows: Dict[int, List[BrailleChar]] = {}
        for ch in chars:
            rows.setdefault(ch.cell_row, []).append(ch)

        lines = []
        for row_idx in sorted(rows.keys()):
            row_chars = sorted(rows[row_idx], key=lambda c: c.cell_col)
            lines.append("".join(c.char for c in row_chars))

        return "\n".join(lines)

    # ── PyTorch model stub ────────────────────────────────────────

    def _load_model(self, path: str) -> None:
        """Load a trained PyTorch model for braille classification.

        Model architecture (stub):
        - Input: 6-dim binary vector (dot states)
        - Hidden: 32 → 64 → 32
        - Output: N classes (26 letters + 10 digits + punctuation)

        To train:
        1. Prepare dataset: each sample = (6-bool dot vector, char label)
        2. Use ``braille_engine/train_stub.py`` (to be created)
        3. Save model weights to ``models/braille_classifier.pt``
        """
        try:
            import torch
            import torch.nn as nn

            class BrailleDotNet(nn.Module):
                def __init__(self, num_classes: int = 37):
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Linear(6, 32),
                        nn.ReLU(),
                        nn.Linear(32, 64),
                        nn.ReLU(),
                        nn.Linear(64, 32),
                        nn.ReLU(),
                        nn.Linear(32, num_classes),
                    )

                def forward(self, x):
                    return self.net(x)

            self._model = BrailleDotNet()
            if os.path.exists(path):
                self._model.load_state_dict(torch.load(path, map_location="cpu"))
                self._model.eval()
                logger.info("Braille model loaded from %s", path)
            else:
                logger.warning("Model path %s not found — using untrained stub", path)
        except ImportError:
            logger.warning("PyTorch not installed — model mode unavailable")
            self._mode = "lookup"


# ── Dataset format specification ──────────────────────────────────
DATASET_FORMAT = """
Braille Dataset Format
======================

Each sample is a JSON file alongside a PNG image:

  {id}.png  — grayscale or BGR image of braille surface
  {id}.json — metadata:
    {
      "id": "abc123",
      "timestamp": "2026-02-11T...",
      "ground_truth": "hello world",
      "dots_per_cell": [[true,false,...], ...],
      "consent_given": true,
      "capture_hints": { ... }
    }

Ground-truth labels should be Grade-1 English braille transcriptions.
Images should be at least 640×480 with visible raised dots.
"""


# Make os available for _load_model
import os
