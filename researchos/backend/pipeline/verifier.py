import json
import os

import anthropic

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1500

SYSTEM_PROMPT = """You are a rigorous IRB reviewer conducting a consistency check on a proposed
protocol amendment. Your job is adversarial — find inconsistencies, contradictions, scope issues,
or regulatory concerns that could cause the amendment to be returned or delayed.

Check for:
- Contradictions between the draft sections and the approved protocol
- Claims or procedures described in the draft that exceed the scope of the researcher's description
- Missing information that IRB reviewers will flag (e.g., undescribed risks, missing re-consent plan)
- Regulatory concerns under the Common Rule (45 CFR 46)
- Internal inconsistencies between draft sections (e.g., Section A says X but Section C ignores X)
- Scope creep — amendment claims more or less than the change description supports

Severity definitions:
- ERROR: Will likely cause the amendment to be returned. Must be fixed before submission.
- WARNING: May cause delays or questions from reviewers. Should be addressed.
- INFO: Minor suggestion or clarification that would strengthen the submission.

Respond ONLY with valid JSON matching this exact schema — no markdown fences, no extra text:
{
  "overall_status": "CLEAN" | "WARNINGS" | "ERRORS",
  "flags": [
    {
      "severity": "ERROR" | "WARNING" | "INFO",
      "section": "<section name, e.g. Section A or Section C>",
      "issue": "<specific issue found>",
      "recommendation": "<specific action to resolve>"
    }
  ],
  "consistency_score": <integer 1-10>,
  "ready_to_submit": <true | false>,
  "reviewer_notes": "<overall assessment in 1-2 sentences>"
}"""

FALLBACK = {
    "overall_status": "WARNINGS",
    "flags": [
        {
            "severity": "WARNING",
            "section": "All Sections",
            "issue": "Automated consistency check could not be completed due to a processing error.",
            "recommendation": (
                "Manually review all sections for consistency with the approved protocol before submission."
            ),
        }
    ],
    "consistency_score": 5,
    "ready_to_submit": False,
    "reviewer_notes": (
        "Automated verification failed. Manual review by PI is required before submission to ORPC."
    ),
}


def verify_consistency(
    draft: dict,
    protocol_text: str,
    change_description: str,
) -> dict:
    """
    Stage 3: Adversarial consistency check of the drafted amendment.

    Uses a separate Claude call with an adversarial reviewer persona to identify
    inconsistencies, scope issues, and regulatory concerns. Injects the first 3000
    chars of the approved protocol, the change description, and draft Sections A-D.
    Returns a structured verification report with severity-tagged flags and a 1-10 score.
    Falls back to a safe default dict if the API call or JSON parsing fails.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    section_a = draft.get("section_a_summary", "")
    section_b = draft.get("section_b_justification", "")
    section_c = draft.get("section_c_risk_impact", "")
    section_d = draft.get("section_d_reconsent", "")

    user_message = f"""Perform a consistency check on this IRB amendment draft.

ORIGINAL CHANGE DESCRIPTION:
{change_description}

APPROVED PROTOCOL CONTEXT (first 3000 chars):
{protocol_text[:3000]}

DRAFT SECTION A — Description of Changes:
{section_a}

DRAFT SECTION B — Justification:
{section_b}

DRAFT SECTION C — Risk/Benefit Impact:
{section_c}

DRAFT SECTION D — Re-consent Assessment:
{section_d}

Identify all inconsistencies, scope issues, and regulatory concerns. Return JSON only."""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return FALLBACK
    except Exception:
        return FALLBACK
