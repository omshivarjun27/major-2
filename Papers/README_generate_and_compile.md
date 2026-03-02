# VVA Paper — Generate and Compile Runbook

## Files Produced

| File | Description |
|------|-------------|
| `VVA_Paper_Combined_filled.tex` | Main LaTeX paper (all sections filled) |
| `survey_table.tex` | 53-row literature survey table |
| `refs.bib` | BibTeX with 53 entries |
| `fig/block_diagram_prompt.txt` | Image prompt for architecture diagram |
| `fig/survey_outcomes_prompt.txt` | Image prompt for survey bar chart |

## Step 1: Generate Figures

Use an image generation tool (Paperbanana, Nanobanana, DALL-E, etc.) with the exact prompts in:
- `fig/block_diagram_prompt.txt` → save as `fig/block_diagram.png`
- `fig/survey_outcomes_prompt.txt` → save as `fig/survey_outcomes.png`

## Step 2: Run Local Evaluations

Fill the `<<TODO>>` placeholders in the paper with real measured values:

```bash
# Activate environment
cd C:\Voice-Vision-Assistant-for-Blind
.venv\Scripts\activate

# Run all tests (verify 429+ pass)
pytest tests/ --timeout=180 -v --tb=short

# Run performance benchmarks
pytest tests/performance/ --timeout=300

# Detection latency
pytest tests/performance/ -k detection --timeout=60

# Depth latency
pytest tests/performance/ -k depth --timeout=60

# Capture baseline metrics
python scripts/capture_baseline.py
```

## Step 3: Compile LaTeX

### Option A: Overleaf (recommended)
1. Create a new blank project
2. Upload `VVA_Paper_Combined_filled.tex` as `main.tex`
3. Upload `survey_table.tex` to the project root
4. Upload `refs.bib` to the project root
5. Create a `fig/` folder and upload generated PNGs
6. Set compiler to pdfLaTeX
7. Compile — Overleaf handles the bibtex cycle automatically

### Option B: Local compilation
```bash
cd C:\Voice-Vision-Assistant-for-Blind\Papers
pdflatex VVA_Paper_Combined_filled.tex
bibtex VVA_Paper_Combined_filled
pdflatex VVA_Paper_Combined_filled.tex
pdflatex VVA_Paper_Combined_filled.tex
```

## Step 4: Review TODOs

Search for `TODO` in the compiled paper. A consolidated list is at the bottom of the `.tex` file. Key items:

1. **Performance numbers** — fill after running benchmarks
2. **Figure generation** — replace placeholders with real PNGs
3. **Survey table verification** — cross-check NA entries against original PDFs
4. **Survey bar chart values** — compute real aggregates from table data

## Notes

- The `\todo{}` command renders as red bold text in the PDF
- `%% SOURCE:` comments trace text back to codebase files
- `%% INFERENCE:` comments mark paragraphs where content was inferred
- Author and guide metadata is preserved exactly from the original file
