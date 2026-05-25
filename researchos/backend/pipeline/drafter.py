import json
import os

import anthropic

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 6000

SYSTEM_PROMPT = """You are an expert IRB amendment drafter with deep knowledge of the Common Rule
(45 CFR 46) and institutional review board requirements. You are assisting a PI or study
coordinator at a research university draft a formal IRB protocol amendment.

CRITICAL RULES — follow without exception:
1. Write formal regulatory language appropriate for IRB submission review.
2. Do NOT infer procedures, risks, populations, or scientific rationale beyond what the researcher
   explicitly described. If it was not stated, do not invent it.
3. Insert [RESEARCHER TO CONFIRM: <specific question>] wherever information is ambiguous, missing,
   or requires researcher verification before submission.
4. Reference specific sections of the approved protocol when relevant (e.g., "Section 3.2 of the
   approved protocol").
5. Never speculate about scientific rationale not explicitly provided by the researcher.
6. Be specific and concrete — no vague generalities or boilerplate language.
7. Section A must be a precise bullet-point summary of ALL changes described.
8. Section C must assess risk impact based only on what was described, not assumed procedures.

Respond ONLY with valid JSON matching this exact schema — no markdown fences, no extra text:
{
  "section_a_summary": "<precise bullet-point summary of ALL changes, one per line starting •>",
  "section_b_justification": "<scientific/operational rationale — only what researcher provided>",
  "section_c_risk_impact": "<risk/benefit assessment — cite specific procedures described>",
  "section_d_reconsent": "<re-consent assessment and plan, or statement re-consent not required>",
  "section_e_consent_changes": "<consent form update description, or 'No changes required.'>",
  "key_changes_list": ["<3-7 short bullets for cover page, each under 100 chars>"]
}"""

FALLBACK = {
    "section_a_summary": (
        "• [RESEARCHER TO CONFIRM: Amendment drafting failed. Please describe all changes"
        " manually.]\n"
        "• [RESEARCHER TO CONFIRM: List all modified procedures, populations, or data collection"
        " methods.]"
    ),
    "section_b_justification": (
        "[RESEARCHER TO CONFIRM: Please provide the scientific or operational justification"
        " for this amendment.]"
    ),
    "section_c_risk_impact": (
        "[RESEARCHER TO CONFIRM: Please assess the impact on participant risk and benefit"
        " resulting from these changes.]"
    ),
    "section_d_reconsent": (
        "[RESEARCHER TO CONFIRM: Determine whether existing participants must be re-consented and "
        "describe the re-consent plan if required.]"
    ),
    "section_e_consent_changes": (
        "[RESEARCHER TO CONFIRM: Describe any required changes to the informed consent document, "
        "or confirm no changes are needed.]"
    ),
    "key_changes_list": [
        "Amendment draft generation failed — manual completion required",
        "[RESEARCHER TO CONFIRM: List key changes here]",
    ],
}


def draft_amendment(
    change_description: str,
    protocol_text: str,
    classification: dict,
) -> dict:
    """
    Stage 2: Draft all five IRB amendment sections using Claude.

    Injects the protocol text (first 5000 chars), the researcher's change description,
    and Stage 1 classification output (review type, re-consent flag, scope warning).
    Returns structured JSON with all five amendment sections and a key changes list.
    Falls back to a safe placeholder dict if the API call or JSON parsing fails.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    review_type = classification.get("review_type", "EXPEDITED")
    re_consent = classification.get("re_consent_required", False)
    scope_warning = classification.get("scope_warning", False)

    user_message = f"""Draft all five IRB amendment sections for this protocol change.

CHANGE DESCRIPTION (researcher's words):
{change_description}

APPROVED PROTOCOL CONTEXT (first 5000 chars):
{protocol_text[:5000]}

CLASSIFICATION RESULTS:
- Review Type: {review_type}
- Re-consent Required: {re_consent}
- Scope Warning: {scope_warning}

Draft all five sections and return JSON only."""

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
