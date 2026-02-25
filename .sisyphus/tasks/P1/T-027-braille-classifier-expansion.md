# T-027: braille-classifier-expansion

> Phase: P1 | Cluster: CL-OCR | Risk: Low | State: not_started

## Objective

Expand `BrailleClassifier` in `core/braille/braille_classifier.py` to support the
complete Grade 1 Braille character set. The current `BRAILLE_MAP` (221 lines) has 26
lowercase letters, 3 digits (1-3), and space. This task adds: all 10 digit mappings
(0-9) with the number indicator prefix, common punctuation marks (period, comma,
exclamation, question, colon, semicolon, hyphen, apostrophe), the capital letter
indicator, and 10 common Grade 1 contractions (and, for, of, the, with, ch, sh, th,
wh, ou).

These additions make the classifier production-ready for the most common English
Braille documents: medicine labels, elevator buttons, transit signage, and menu items.

## Current State (Codebase Audit 2026-02-25)

- `core/braille/braille_classifier.py` (221 lines):
  - `BRAILLE_MAP` dict (line 18): maps 6-dot tuples to characters.
    - Contains: a-z (26 letters), digits 1-3, space.
    - Missing: digits 0, 4-9, all punctuation, number indicator, capital indicator.
  - `BrailleChar` dataclass (line 85): `dots` (tuple), `char` (str), `confidence` (float).
  - `BrailleClassifier` class (line 95):
    - `classify_cell()` (line 110): looks up dot pattern in BRAILLE_MAP, falls back to
      PyTorch model if pattern not found (model is a stub, always returns "?").
    - `classify_sequence()` (line 135): iterates cells, calls classify_cell for each.
    - `_model_classify()` (line 155): stub that logs warning and returns "?".
  - `DATASET_FORMAT` dict (line 200): describes expected training data format.
- No number indicator handling. In Braille, digits share patterns with letters a-j;
  the number indicator (dots 3-4-5-6) signals that the following cells are digits.
- No capital indicator handling. Capital indicator (dot 6) prefixes uppercase letters.
- No punctuation mappings at all.
- No Grade 1 contractions.
- `core/braille/__init__.py` exports `BrailleClassifier`, `BrailleChar`.

## Implementation Plan

### Step 1: Add complete digit mappings with number indicator

Braille digits 1-9 share dot patterns with letters a-i. Digit 0 shares pattern with j.
Add the number indicator cell `(3,4,5,6)` and implement state tracking in
`classify_sequence()` to toggle number mode on/off.

```python
NUMBER_INDICATOR = (3, 4, 5, 6)
DIGIT_MAP = {
    (1,): "1", (1,2): "2", (1,4): "3", (1,4,5): "4", (1,5): "5",
    (1,2,4): "6", (1,2,4,5): "7", (1,2,5): "8", (2,4): "9", (2,4,5): "0",
}
```

### Step 2: Add capital indicator

Add capital indicator cell `(6,)`. When encountered, the next letter cell is uppercased.

```python
CAPITAL_INDICATOR = (6,)
```

### Step 3: Add punctuation mappings

```python
PUNCTUATION_MAP = {
    (2,5,6): ".",
    (2,): ",",
    (2,3,5): "!",
    (2,3,6): "?",
    (2,5): ":",
    (2,3): ";",
    (3,6): "-",
    (3,): "'",
}
```

### Step 4: Add Grade 1 contractions

Add the 10 most common single-cell contractions that map to whole words in context.

### Step 5: Update classify_sequence with state machine

Refactor `classify_sequence()` to maintain state: `number_mode` and `capital_next`.
When number indicator is seen, switch to digit lookups until a letter/space resets.
When capital indicator is seen, uppercase the next character.

### Step 6: Write 8 unit tests

Cover digits, punctuation, capital indicator, number indicator toggle, contractions,
and mixed sequences.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_braille_classifier.py` | 8 unit tests for expanded Braille mappings |

## Files to Modify

| File | Change |
|------|--------|
| `core/braille/braille_classifier.py` | Add DIGIT_MAP, PUNCTUATION_MAP, CONTRACTIONS, indicators, state machine in classify_sequence |
| `core/braille/AGENTS.md` | Document expanded character set and state machine behavior |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_braille_classifier.py` | `test_digits_1_through_9` - number indicator + digit cells produce correct digits |
| | `test_digit_0` - number indicator + j-pattern produces "0" |
| | `test_capital_indicator` - capital indicator + letter cell produces uppercase |
| | `test_punctuation_period` - dot pattern (2,5,6) maps to "." |
| | `test_punctuation_question` - dot pattern (2,3,6) maps to "?" |
| | `test_number_mode_resets_on_space` - number mode deactivates after space cell |
| | `test_mixed_sequence` - sequence with letters, number indicator, digits, punctuation |
| | `test_contraction_the` - single cell for "the" contraction recognized in sequence |

## Acceptance Criteria

- [ ] All 10 digits (0-9) correctly classified after number indicator
- [ ] Number indicator toggles digit mode; space or letter pattern resets it
- [ ] Capital indicator causes next letter to be uppercased
- [ ] 8 punctuation marks mapped and classified correctly
- [ ] 10 Grade 1 contractions added to lookup table
- [ ] `classify_sequence()` handles mixed letter/digit/punctuation input
- [ ] Backward-compatible: existing a-z and 1-3 mappings unchanged
- [ ] All 8 tests pass: `pytest tests/unit/test_braille_classifier.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean
- [ ] `core/braille/AGENTS.md` updated

## Upstream Dependencies

None (entry point task for the OCR cluster).

## Downstream Unblocks

T-029 (face-consent-integration) — consent cascade reuses classifier validation patterns.

## Estimated Scope

- New code: ~80 LOC (digit/punctuation/contraction maps ~40, state machine ~40)
- Modified code: ~30 lines in braille_classifier.py (refactor classify_sequence)
- Tests: ~100 LOC
- Risk: Low. Additive mappings. Existing letter lookups preserved exactly.
