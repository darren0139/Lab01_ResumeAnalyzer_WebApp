# Day 4 Resume Analyzer — Track A Starter

> **Track A** — you write the Python. Start here if you're comfortable with Python classes, lists, and `try/except`.

## Quick setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy .env.example and fill in your API key
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or your preferred provider)
```

## Run the analyzer

```bash
python main.py \
  --resume path/to/your_resume.pdf \
  --jd     inputs/job_rtis_systems_engineer.txt \
  --degree RTIS
```

Reports are saved to `outputs/` as both `.json` and `.md`.

## File guide

| File | Your job |
|---|---|
| `parse.py` | ✏️ **Write this** — Task 1 |
| `prompts.py` | ✏️ **Write this** — Task 3 |
| `analyzer.py` | ✏️ **Write this** — Task 4 |
| `main.py` | ✏️ **Write this** — Task 5 |
| `llm.py` | ✅ Pre-provided — read it, don't edit |
| `report.py` | ✅ Pre-provided — read it, don't edit |

## Check your progress

```bash
# Test parse.py
python -c "from parse import read_jd_text; print(read_jd_text('inputs/job_rtis_systems_engineer.txt')[:200])"

# Test prompts.py
python -c "from prompts import RESUME_PROFILE_PROMPT; print(RESUME_PROFILE_PROMPT[:100])"

# Test analyzer.py
python -c "from analyzer import extract_jd_profile; from parse import read_jd_text; print(extract_jd_profile(read_jd_text('inputs/job_rtis_systems_engineer.txt')))"
```

## Stretch goals

- Route to a local Ollama model by changing `MODEL=` in `.env` — no code changes needed.
- Add a thin Streamlit UI (`pip install streamlit`) that accepts file uploads.
- Add a second JD comparison run with `inputs/job_unrelated.txt` and compare scores.
