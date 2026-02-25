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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    import torch
    import torch.nn as nn

logger = logging.getLogger("braille-classifier")

# ── Grade 1 English Braille Lookup ────────────────────────────────
# Dot numbering: [1,2,3,4,5,6] → left-col top-to-bottom, right-col top-to-bottom
# True/False for each dot presence.

BRAILLE_MAP: dict[tuple[bool, ...], str] = {
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
    # Note: Digits share patterns with letters a-j. They are disambiguated by
    # the number indicator prefix in classify_sequence(). The DIGIT_MAP is
    # defined separately below — do NOT duplicate patterns here.
    # Space
    # Space
    (False, False, False, False, False, False): " ",
}

# Reverse map: char → dots
CHAR_TO_DOTS: dict[str, tuple[bool, ...]] = {v: k for k, v in BRAILLE_MAP.items()}

# Indicators and Grade 1 expansions
NUMBER_INDICATOR: tuple[int, ...] = (3, 4, 5, 6)
CAPITAL_INDICATOR: tuple[int, ...] = (6,)

DIGIT_MAP: dict[tuple[int, ...], str] = {
    (1,): "1",
    (1, 2): "2",
    (1, 4): "3",
    (1, 4, 5): "4",
    (1, 5): "5",
    (1, 2, 4): "6",
    (1, 2, 4, 5): "7",
    (1, 2, 5): "8",
    (2, 4): "9",
    (2, 4, 5): "0",
}

PUNCTUATION_MAP: dict[tuple[int, ...], str] = {
    (2, 5, 6): ".",
    (2,): ",",
    (2, 3, 5): "!",
    (2, 3, 6): "?",
    (2, 5): ":",
    (2, 3): ";",
    (3, 6): "-",
    (3,): "'",
}

CONTRACTIONS: dict[tuple[int, ...], str] = {
    (1, 2, 3, 4, 6): "and",
    (1, 2, 3, 4, 5, 6): "for",
    (1, 2, 3, 5, 6): "of",
    (2, 3, 4, 6): "the",
    (2, 3, 4, 5, 6): "with",
    (1, 6): "ch",
    (1, 4, 6): "sh",
    (1, 4, 5, 6): "th",
    (1, 5, 6): "wh",
    (1, 2, 5, 6): "ou",
}

LETTER_MAP: dict[tuple[int, ...], str] = {
    (1,): "a",
    (1, 2): "b",
    (1, 4): "c",
    (1, 4, 5): "d",
    (1, 5): "e",
    (1, 2, 4): "f",
    (1, 2, 4, 5): "g",
    (1, 2, 5): "h",
    (2, 4): "i",
    (2, 4, 5): "j",
    (2, 4, 5, 6): "w",
}


def _dots_to_numbers(dots: tuple[bool, ...]) -> tuple[int, ...]:
    return tuple(idx + 1 for idx, active in enumerate(dots) if active)


class CellLike(Protocol):
    row: int
    col: int
    dots: list[bool]


@dataclass
class BrailleChar:
    """Classified braille character."""
    char: str
    dots: list[bool]
    confidence: float = 1.0
    cell_row: int = 0
    cell_col: int = 0

    def to_dict(self) -> dict[str, object]:
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

    def __init__(self, mode: str = "lookup", model_path: str | None = None):
        self._mode: str = mode
        self._model_path: str | None = model_path
        self._model: "nn.Module | None" = None

        if mode == "model" and model_path:
            self._load_model(model_path)

    # ── Lookup classification ─────────────────────────────────────

    def classify(self, cells: list[CellLike]) -> list[BrailleChar]:
        """Classify a list of CellInfo objects into characters.

        Args:
            cells: From BrailleSegmenter output.

        Returns:
            List of BrailleChar.
        """
        return self.classify_sequence(cells)

    def classify_cell(self, dots: tuple[bool, ...]) -> str:
        """Classify a single braille cell by lookup or model."""
        char = BRAILLE_MAP.get(dots)
        if char is not None:
            return char
        if self._mode == "model":
            return self._model_classify(dots)
        return "?"

    def classify_sequence(self, cells: list[CellLike]) -> list[BrailleChar]:
        """Classify a sequence of cells with number/capital state handling."""
        results: list[BrailleChar] = []
        number_mode = False
        capital_next = False

        for cell in cells:
            dots = tuple(cell.dots[:6])
            dot_numbers = _dots_to_numbers(dots)

            if dot_numbers == NUMBER_INDICATOR:
                number_mode = True
                capital_next = False
                continue

            if dot_numbers == CAPITAL_INDICATOR:
                capital_next = True
                continue

            if number_mode and dot_numbers in DIGIT_MAP:
                char = DIGIT_MAP[dot_numbers]
            else:
                if number_mode:
                    number_mode = False

                if dot_numbers in CONTRACTIONS:
                    char = CONTRACTIONS[dot_numbers]
                elif dot_numbers in PUNCTUATION_MAP:
                    char = PUNCTUATION_MAP[dot_numbers]
                elif dot_numbers in LETTER_MAP:
                    char = LETTER_MAP[dot_numbers]
                else:
                    char = self.classify_cell(dots)

            if char == " ":
                number_mode = False
                capital_next = False

            if capital_next and char.isalpha() and len(char) == 1:
                char = char.upper()
                capital_next = False

            confidence = 1.0 if char != "?" else 0.0
            results.append(BrailleChar(
                char=char,
                dots=list(cell.dots),
                confidence=confidence,
                cell_row=cell.row,
                cell_col=cell.col,
            ))

        return results

    def _model_classify(self, _: tuple[bool, ...]) -> str:
        """Stub for future ML-based classification."""
        logger.warning("Braille model classification not implemented")
        return "?"

    def to_text(self, chars: list[BrailleChar]) -> str:
        """Convert classified characters to a text string.

        Groups by row, orders by column.
        """
        if not chars:
            return ""

        rows: dict[int, list[BrailleChar]] = {}
        for ch in chars:
            rows.setdefault(ch.cell_row, []).append(ch)

        lines: list[str] = []
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
                    self.net: nn.Sequential = nn.Sequential(
                        nn.Linear(6, 32),
                        nn.ReLU(),
                        nn.Linear(32, 64),
                        nn.ReLU(),
                        nn.Linear(64, 32),
                        nn.ReLU(),
                        nn.Linear(32, num_classes),
                    )

                def forward(self, x: torch.Tensor) -> torch.Tensor:  # pyright: ignore[reportImplicitOverride]
                    return cast(torch.Tensor, self.net(x))

            self._model = BrailleDotNet()
            if os.path.exists(path):
                state_dict = cast(dict[str, torch.Tensor], torch.load(path, map_location="cpu"))
                _ = self._model.load_state_dict(state_dict)
                _ = self._model.eval()
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
import os  # noqa: E402
