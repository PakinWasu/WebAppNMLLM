from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List
import re
import statistics

router = APIRouter(prefix="/api/llm", tags=["LLM Evaluation"])


# ---------------------------
# Request / Response Models
# ---------------------------

class LLMEvaluationRequest(BaseModel):
    scope: str  # global | device | issues
    parsed_data: Dict[str, Any]
    llm_output: str


class LLMEvaluationResponse(BaseModel):
    consistency_score: float
    coverage_score: float
    quality_score: float
    overall_score: float
    issues: List[str]
    summary: str


# ---------------------------
# Core Evaluation Logic
# ---------------------------

IMPORTANT_KEYS = [
    "interfaces",
    "vlan",
    "trunk",
    "stp",
    "ospf",
    "bgp",
    "routing",
    "neighbor",
    "cpu",
    "memory",
    "security"
]


def evaluate_consistency(parsed_data: Dict[str, Any], llm_text: str):
    """
    Check if LLM mentions values that do not exist in parsed data
    """
    mismatches = []

    # Example checks (extendได้เรื่อย ๆ)
    if "OSPF" in llm_text.upper():
        ospf_data = parsed_data.get("routing", {}).get("ospf", {})
        if not ospf_data or not ospf_data.get("neighbors"):
            mismatches.append("LLM mentioned OSPF but no OSPF data exists.")

    if "BGP" in llm_text.upper():
        bgp_data = parsed_data.get("routing", {}).get("bgp", {})
        if not bgp_data or not bgp_data.get("peers"):
            mismatches.append("LLM mentioned BGP but no BGP configuration exists.")

    score = max(0.0, 1.0 - (len(mismatches) * 0.2))
    return round(score * 100, 2), mismatches


def evaluate_coverage(parsed_data: Dict[str, Any], llm_text: str):
    """
    Check if important areas that exist in data are mentioned by LLM
    """
    missing = []

    text_lower = llm_text.lower()

    for key in IMPORTANT_KEYS:
        if key in parsed_data or key in str(parsed_data):
            if key not in text_lower:
                missing.append(f"LLM did not mention {key}")

    covered = len(IMPORTANT_KEYS) - len(missing)
    score = covered / len(IMPORTANT_KEYS)

    return round(score * 100, 2), missing


def evaluate_quality(llm_text: str):
    """
    Simple heuristic-based quality scoring (LLM-as-a-judge lite)
    """
    sentences = re.split(r"[.!?]", llm_text)
    sentence_count = len([s for s in sentences if s.strip()])

    if sentence_count < 3:
        score = 4
    elif sentence_count < 6:
        score = 6
    elif sentence_count < 10:
        score = 8
    else:
        score = 9

    return score


def generate_human_summary(consistency, coverage, quality, issues):
    if consistency >= 80 and coverage >= 70:
        status = "The LLM output is generally reliable and suitable for operational use."
    elif consistency >= 60:
        status = "The LLM output is usable but requires manual verification in some areas."
    else:
        status = "The LLM output contains significant issues and should not be trusted without review."

    issue_text = " ".join(issues) if issues else "No critical issues were detected."

    return f"""
Overall assessment:
{status}

Key observations:
- Consistency score reflects how well the summary aligns with real network data.
- Coverage score indicates whether important network aspects were mentioned.
- Quality score represents readability and clarity for human operators.

Detected issues:
{issue_text}
""".strip()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/evaluate", response_model=LLMEvaluationResponse)
def evaluate_llm_output(payload: LLMEvaluationRequest):
    consistency_score, consistency_issues = evaluate_consistency(
        payload.parsed_data, payload.llm_output
    )

    coverage_score, coverage_issues = evaluate_coverage(
        payload.parsed_data, payload.llm_output
    )

    quality_score = evaluate_quality(payload.llm_output)

    overall_score = round(
        (0.45 * consistency_score) +
        (0.35 * coverage_score) +
        (0.20 * (quality_score * 10)),
        2
    )

    all_issues = consistency_issues + coverage_issues

    summary = generate_human_summary(
        consistency_score,
        coverage_score,
        quality_score,
        all_issues
    )

    return LLMEvaluationResponse(
        consistency_score=consistency_score,
        coverage_score=coverage_score,
        quality_score=quality_score,
        overall_score=overall_score,
        issues=all_issues,
        summary=summary
    )
