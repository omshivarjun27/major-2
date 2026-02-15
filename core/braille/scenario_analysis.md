# Scenario Analysis: Braille Engine for Visually Impaired Users

> How braille capture, recognition, and embossing guidance transforms everyday literacy access across **12 real-world scenarios**.

---

## 1. Reading Medicine Labels

**Environment:** Home medicine cabinet, pharmacy counter. Pills in small boxes with braille labels.

**How braille engine helps:**
- Camera captures medicine box → segmenter extracts dot cells → classifier decodes Grade 1 braille.
- Cross-references decoded text with memory engine ("This is the same ibuprofen from last week").
- Embossing guide verifies whether the label is properly raised for future tactile reads.

**What to store:** Decoded text, bounding-box coordinates, confidence score, timestamp.

**Example dialogue:**
> **User:** "What does the braille on this box say?"
> **Assistant:** "It reads I-B-U-P-R-O-F-E-N, 200 milligrams. This matches the medicine you scanned last Tuesday."

**Safety:** Always warn if confidence < 80%. Recommend pharmacist confirmation for new prescriptions. Never give dosage advice.

---

## 2. Elevator Floor Buttons

**Environment:** Elevator panel with braille labels next to floor buttons. Typically low lighting, metallic surfaces.

**How braille engine helps:**
- `BrailleCapture.analyse_frame()` checks contrast and brightness on reflective metal.
- Deskew compensates for angled camera shots.
- Classifier maps dot patterns to floor numbers and letters (L, G, B).

**Challenges:** High specular reflections on metal. Adaptive threshold + CLAHE handle this.

**Example dialogue:**
> **User:** "Which button is floor 5?"
> **Assistant:** "I can see braille labels. From top to bottom: 12, 11, 10… Floor 5 is the sixth button from the bottom, on the right column."

**Safety:** Re-verify with the user by reading back the detected label before they press.

---

## 3. Restaurant Menu (Braille Edition)

**Environment:** Sit-down restaurant providing braille menus. Typically embossed on thick paper or plastic sheets.

**How braille engine helps:**
- Segmenter handles multi-line braille across the full page.
- Grid-fitting groups cells into lines → classifier reads line by line.
- Memory engine stores previous restaurant visits ("Last time you ordered the pasta which was item 3").

**What to store:** Menu items decoded, restaurant name / GPS if available, timestamp.

**Example dialogue:**
> **User:** "Read me the braille menu, just the mains."
> **Assistant:** "Main courses: 1. Grilled salmon with herbs — 18 dollars. 2. Pasta primavera — 14 dollars. 3. Chicken tikka masala — 16 dollars."

**Safety:** Warn if embossing quality is poor (dots worn down → low circularity score).

---

## 4. Library Book Identification

**Environment:** Public library shelf. Books with braille title labels on the spine.

**How braille engine helps:**
- Narrow spine requires tight framing → `CaptureHints` warns if field of view is insufficient.
- Small dot pitch on book spines → segmenter auto-adjusts `min_dot_area`.
- Decoded title cross-referenced with memory ("You checked out this book on March 5th").

**Example dialogue:**
> **User:** "What is this book?"
> **Assistant:** "The braille on the spine reads 'To Kill a Mockingbird'. I also see a Grade 1 author label below: 'Harper Lee'."

**Safety:** Confidence may be lower on aged/worn labels. State uncertainty clearly.

---

## 5. ATM / Kiosk Keypad

**Environment:** Bank ATM or vending machine keypad with braille on number keys.

**How braille engine helps:**
- Metal/rubber key surfaces → capture checks contrast and focus.
- Small cell size → classifier uses trained model mode for sub-2mm dots.
- Spatial mapping: links each braille label to its physical key position.

**Example dialogue:**
> **User:** "Describe the ATM keypad layout."
> **Assistant:** "Standard 3-by-4 grid. Top row left to right: 1, 2, 3. Middle row: 4, 5, 6. Bottom row: 7, 8, 9. Bottom centre: 0. Star on left, hash on right. The braille dots are well embossed."

**Safety:** Never read or store PIN input. Guide to button positions only.

---

## 6. Museum Exhibit Plaques

**Environment:** Museum with braille information plaques beside exhibits. Often behind glass or at waist height.

**How braille engine helps:**
- Deskew handles oblique camera angle (plaque may be tilted or behind glass).
- Multi-line reading for descriptive text (up to 50+ cells per line).
- Memory stores previously read exhibits for later "What did that dinosaur plaque say?"

**Example dialogue:**
> **User:** "Read the plaque next to this exhibit."
> **Assistant:** "It says: 'Tyrannosaurus Rex. Late Cretaceous period, approximately 68 million years ago. This specimen was discovered in Montana in 1902.'"

**Safety:** Glass reflections may reduce quality. Warn the user to move for better angle if `contrast_ok` is False.

---

## 7. Medication Dosage Sheets (Grade 2 Braille)

**Environment:** Hospital or home care. Printed dosage schedules in contracted (Grade 2) braille.

**How braille engine helps:**
- Grade 2 support (planned): contracted words like "the" = single cell, "and" = single cell.
- OCR pipeline reads Grade 1 subset now; flags unknown contractions for user.
- Timestamps dosage reads for memory: "You last read this at 8 AM — it says take 2 pills at noon."

**What to store:** Decoded schedule text, timestamp, confidence score.

**Safety:** CRITICAL — always state "Confidence is X percent" for medical text. Recommend professional verification for any confidence below 90%.

---

## 8. Braille Teaching / Learning Aid

**Environment:** Classroom or home. Student learning braille by writing cells with a stylus.

**How braille engine helps:**
- `EmbossingGuide.text_to_layout()` generates expected dot positions for a word.
- `verify_layout()` compares student's written dots against expected.
- Real-time feedback: "Your letter B is missing dot 2 in the second position."

**Example dialogue:**
> **User:** "I just wrote 'hello' in braille. Did I get it right?"
> **Assistant:** "Almost! The H, E, L, L are correct. The O is missing dot 3 — it should have dots 1, 3, 5. Try again on the O."

**Safety:** Encourage, don't criticise. Use positive reinforcement phrasing.

---

## 9. Product Labels in a Grocery Store

**Environment:** Grocery aisle. Some products (mandated in certain countries) have braille on packaging.

**How braille engine helps:**
- Flexible packaging → `analyse_frame()` warns if image is blurry (low focus).
- Small label areas → segmenter crops to region of interest.
- Product name decoded and stored for future shopping comparison.

**Example dialogue:**
> **User:** "What does the braille on this can say?"
> **Assistant:** "It reads 'Tomato Soup, 400 grams'. This is the same brand you bought two weeks ago."

**Safety:** Nutrition/allergen info should not rely solely on braille OCR — recommend checking with store staff for allergen-critical decisions.

---

## 10. Public Transit Signage

**Environment:** Bus stop, train platform. Braille plates on route signs, platform numbers, handrails.

**How braille engine helps:**
- Outdoor conditions → capture validates brightness (might be too bright/glare or too dark).
- Metal plates → CLAHE + bilateral filter handle high-contrast steel engravings.
- Memory stores route numbers for frequent commute sessions.

**Example dialogue:**
> **User:** "What does the braille sign on this bus stop say?"
> **Assistant:** "It reads 'Route 14, Downtown Express'. The next braille plate below says 'Bay 3'."

**Safety:** Always confirm with live transit data if available. Braille signs may reference outdated route info.

---

## 11. Embossing Quality Verification

**Environment:** Braille printing office, school production facility. QA of freshly embossed documents.

**How braille engine helps:**
- `EmbossingGuide.verify_layout()` compares printed dots against expected source text.
- Reports misaligned dots, missing dots, and crushed (flat) dots with cell coordinates.
- Batch mode: process an entire page, return quality score per line.

**Example dialogue:**
> **User:** "Check this embossed page for errors."
> **Assistant:** "Page quality: 96%. Line 3 has a missing dot at cell 8 position 4. Line 7, cell 12 — dot 6 appears too faint. The rest is within tolerance."

**Safety:** Human proofreader should confirm all flagged errors before distribution.

---

## 12. Multi-Language Braille (International Travel)

**Environment:** Airport, hotel, or foreign pharmacy. Braille in non-English alphabets (French, Spanish, German, Arabic Braille).

**How braille engine helps:**
- Classifier supports configurable lookup tables per language.
- Detects script mismatch ("These dots don't match English Grade 1 — possibly French").
- Falls back to raw dot notation (e.g., "dots 1-2-4") when language is unknown.

**Example dialogue:**
> **User:** "Read this sign — I think it's in French."
> **Assistant:** "Switching to French braille table. It reads 'Sortie de secours' — that means 'Emergency exit'."

**Safety:** Language detection is best-effort. Always state the assumed language and ask user to confirm.

---

## Summary Matrix

| # | Scenario | Primary Module | Key Challenge | Safety Level |
|---|----------|----------------|---------------|--------------|
| 1 | Medicine labels | classifier + memory | Small text, high stakes | 🔴 Critical |
| 2 | Elevator buttons | capture + classifier | Metallic reflections | 🟡 Medium |
| 3 | Restaurant menus | segmenter + classifier | Multi-line, worn paper | 🟢 Low |
| 4 | Library books | capture + segmenter | Narrow spine, worn labels | 🟢 Low |
| 5 | ATM keypads | capture + classifier | Metal surface, small cells | 🟠 High |
| 6 | Museum plaques | deskew + segmenter | Glass, oblique angle | 🟢 Low |
| 7 | Dosage sheets | classifier (Grade 2) | Contracted braille | 🔴 Critical |
| 8 | Teaching aids | embossing_guidance | Student verification | 🟢 Low |
| 9 | Grocery labels | capture + segmenter | Flexible packaging | 🟡 Medium |
| 10 | Transit signs | capture + classifier | Outdoor conditions | 🟡 Medium |
| 11 | QA verification | embossing_guidance | Batch accuracy | 🟠 High |
| 12 | Multi-language | classifier (tables) | Unknown script | 🟡 Medium |
