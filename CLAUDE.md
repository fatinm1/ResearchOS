# ResearchOS — Claude Code Project Memory

## What this project is
ResearchOS is an AI-powered IRB amendment drafting platform for university research labs.
Researchers describe a protocol change in plain English, upload their approved IRB
protocol PDF, and receive a submission-ready amendment document in under 90 seconds.

Target users: Principal Investigators and PhD study coordinators at UMBC and other
research universities. First pilot: UMBC (University of Maryland, Baltimore County).

## Repository
https://github.com/fatinm1/ResearchOS.git

## Tech stack
- Backend: FastAPI + Python 3.12
- AI: Anthropic Claude API (claude-sonnet-4-20250514)
- PDF: PyMuPDF (fitz)
- Documents: python-docx
- Frontend: Vanilla HTML/CSS/JS — no frameworks, no build step

## Running locally
```bash
cd researchos
pip install -r requirements.txt
cp .env.example .env  # then add your ANTHROPIC_API_KEY
uvicorn backend.main:app --reload --port 8000
# Landing: http://localhost:8000
# App:     http://localhost:8000/app
# Health:  http://localhost:8000/api/health
```

## Project structure
```
researchos/
├── backend/
│   ├── main.py              # FastAPI server and routes
│   ├── pipeline/
│   │   ├── __init__.py      # empty
│   │   ├── extractor.py     # PDF text extraction
│   │   ├── classifier.py    # Stage 1: review type classification
│   │   ├── drafter.py       # Stage 2: amendment drafting
│   │   ├── verifier.py      # Stage 3: consistency verification
│   │   └── docgen.py        # Word document generation
│   └── models.py            # Pydantic schemas
├── frontend/
│   ├── index.html           # Landing/marketing page
│   ├── app.html             # Product app
│   └── static/
│       └── .gitkeep
├── outputs/                 # Generated .docx files (gitignored)
├── CLAUDE.md                # This file
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Git conventions
- Branch strategy: main → develop → feature/* → fix/*
- NEVER commit directly to main or develop
- NEVER commit .env or any file containing an API key
- NEVER commit outputs/*.docx or __pycache__
- Commit after each logical unit of work (not at the very end)
- Use conventional commits: feat:, fix:, refactor:, docs:, chore:, ci:
- Subject lines: max 72 chars, imperative mood, no period
- Push feature branch after every commit: git push -u origin feature/branch-name

## Code conventions — Python
- Python 3.12
- Type hints on ALL function signatures
- Docstrings on ALL functions (explain WHY, not just WHAT)
- No hardcoded values — use constants defined at module top
- All Claude API calls have try/except with a safe fallback return
- Strip markdown fences before JSON parsing in all pipeline stages
- Max context sent to Claude: 12000 chars for extractor, 4000 for classifier,
  5000 for drafter, 3000 for verifier (to fit safely in context windows)
- Claude model: claude-sonnet-4-20250514 (never change without updating this file)

## Code conventions — Frontend
- Vanilla HTML/CSS/JS only — no React, Vue, Tailwind, Bootstrap
- All CSS inline in <style> tags — no external CSS files
- Google Fonts: DM Serif Display (headings) + DM Sans (body)
- CSS variables defined in :root for all colors (see design system)
- app.html must only be accessed via FastAPI server — never as a raw file
- All fetch calls go to relative paths (/api/...) — no hardcoded localhost

## Design system — colors
```css
--zinc-950: #09090b  --zinc-900: #18181b  --zinc-800: #27272a
--zinc-700: #3f3f46  --zinc-600: #52525b  --zinc-400: #a1a1aa
--zinc-200: #e4e4e7  --teal: #1D9E75      --teal-dark: #085041
--teal-light: rgba(29,158,117,0.12)       --amber: #FAEEDA
--amber-dark: #633806  --red-light: #FCEBEB  --red-dark: #791F1F
```

## Pipeline architecture
Three separate Claude API calls, each in its own module:
1. extractor.py  → PDF bytes → plain text (PyMuPDF, capped at 12000 chars)
2. classifier.py → text + description → JSON (review type, confidence, flags)
3. drafter.py    → text + description + classification → JSON (5 sections)
4. verifier.py   → draft + protocol + description → JSON (flags, score)
5. docgen.py     → all JSON → .docx file (python-docx, saved to outputs/)

All pipeline modules return safe fallback dicts on JSON parse failure — never raise.

## Key domain knowledge
- IRB = Institutional Review Board (approves human subjects research protocols)
- Amendment = formal document required whenever an approved protocol changes
- Kuali Research = UMBC's IRB submission system (umbc.kuali.co)
- ORPC = UMBC's Office of Research Protections & Compliance
- Review types: MINOR_ADMINISTRATIVE (days), EXPEDITED (1-2 weeks), FULL_BOARD (4-6 weeks)
- Common Rule = 45 CFR 46, the federal regulation governing human subjects research
- The 5 amendment sections: A=Summary, B=Justification, C=Risk, D=Reconsent, E=Consent changes

## What this is NOT
- Not legal advice — all outputs are AI-generated drafts for PI review only
- Not a Kuali replacement — submission still happens in Kuali
- Not an authentication system — no login for MVP
- Not a database-backed app — file output only for MVP

## Important disclaimer (appears on every generated document)
"DRAFT FOR RESEARCHER REVIEW — This document was generated by ResearchOS AI.
The PI must review all content for accuracy before submission to ORPC.
ResearchOS does not guarantee IRB approval."

## Current version
v0.1.0 — MVP, IRB amendment drafting only
Next: v1.1 — grant budget compliance monitoring
