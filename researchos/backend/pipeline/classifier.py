import json
import os

import anthropic

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1000

SYSTEM_PROMPT = """You are an IRB (Institutional Review Board) compliance expert specializing in
the Common Rule (45 CFR 46). Your task is to classify the review type required for a protocol
amendment based on the change description and existing protocol context.

REVIEW TYPE DEFINITIONS:

MINOR_ADMINISTRATIVE:
- Changes to personnel contact information, administrative staff, or coordinator names
- Typographical corrections that do not affect scientific content
- Minor clarifications that do not change procedures, risks, or participant interactions
- Updates to study title or branding that do not affect scientific aims
- Correction of formatting or organizational issues in documents
- Turnaround: typically 1-5 business days via expedited administrative review

EXPEDITED (45 CFR 46.110 — one or more of the 9 categories must apply):
Category 1: Clinical studies of drugs/medical devices (Phase I/II, no significant risk devices)
Category 2: Collection of blood by venipuncture from healthy adults — routine amounts
Category 3: Prospective collection of biological specimens (hair, saliva, excreta, etc.)
Category 4: Collection of data through noninvasive procedures
Category 5: Research involving materials collected solely for non-research purposes
Category 6: Collection of data from voice, video, digital, or image recordings
Category 7: Research on individual or group characteristics or behavior
Category 8: Research involving surveys, interviews, focus groups on non-sensitive topics
Category 9: Continuing review of previously approved research
Risk level: Minimal risk only. Turnaround: 1-2 weeks.

FULL_BOARD:
- Research involving more than minimal risk to participants
- Research involving vulnerable populations (children, prisoners, pregnant women, cognitively impaired)
- Research involving major changes to study aims or scientific objectives
- Addition of invasive procedures beyond venipuncture
- Changes to recruitment that could introduce coercion or undue influence
- Significant changes to data handling for sensitive information (mental health, genetics, HIV status)
- Turnaround: 4-6 weeks (next scheduled board meeting).

Respond ONLY with valid JSON matching this exact schema — no markdown fences, no extra text:
{
  "review_type": "MINOR_ADMINISTRATIVE" | "EXPEDITED" | "FULL_BOARD",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "estimated_turnaround": "<human-readable string>",
  "reasoning": "<2-3 sentence explanation referencing specific regulatory criteria>",
  "risk_flags": ["<flag1>", "<flag2>"],
  "scope_warning": true | false,
  "scope_warning_detail": "<detail or empty string>",
  "re_consent_required": true | false,
  "re_consent_detail": "<detail or empty string>"
}"""

FALLBACK = {
    "review_type": "EXPEDITED",
    "confidence": "LOW",
    "estimated_turnaround": "1-2 weeks (classification failed — verify manually)",
    "reasoning": (
        "Classification could not be completed due to a processing error. Default to EXPEDITED "
        "review. Researcher must verify the appropriate review type with ORPC."
    ),
    "risk_flags": ["Classification failed — manual review required"],
    "scope_warning": False,
    "scope_warning_detail": "",
    "re_consent_required": False,
    "re_consent_detail": "",
}


def classify_amendment(change_description: str, protocol_text: str) -> dict:
    """
    Stage 1: Classify the IRB review type required for this amendment.

    Sends the change description and protocol context to Claude with a detailed
    system prompt containing Common Rule (45 CFR 46) definitions. Returns structured
    JSON identifying review type, confidence, turnaround time, and risk flags.
    Falls back to a safe default dict if the API call or JSON parsing fails.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    user_message = f"""Classify the IRB review type for this protocol amendment.

CHANGE DESCRIPTION:
{change_description}

EXISTING PROTOCOL CONTEXT (first 4000 chars):
{protocol_text[:4000]}

Classify the review type and return JSON only."""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return FALLBACK
    except Exception:
        return FALLBACK
