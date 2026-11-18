import json
import re
from pathlib import Path
from typing import Callable, Awaitable, Dict, List, Any

APP_DIR = Path(__file__).resolve().parents[2]
SCENARIOS_PATH = (
    APP_DIR / "data" / "synthetic" / "scenarios" / "test_scenarios.jsonl"
    if (APP_DIR / "data").exists()
    else APP_DIR.parent / "data" / "synthetic" / "scenarios" / "test_scenarios.jsonl"
)
GROUND_TRUTH_PATH = APP_DIR / "data" / "synthetic" / "scenarios" / "test_ground_truth.jsonl"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Δεν βρέθηκε το αρχείο: {path}")
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _extract_risk_level(text: str) -> str:
    text_l = text.lower()
    for level in ["critical", "high", "medium", "low"]:
        if re.search(rf"\b{level}\b", text_l):
            return level
    return "unknown"


def _token_overlap(expected: str, actual: str) -> float:
    stop = {"the", "and", "to", "of", "a", "in", "is", "for", "on", "with", "as", "by", "at", "or", "if", "it", "be"}
    exp_tokens = {w for w in re.findall(r"[a-z0-9]+", expected.lower()) if w not in stop and len(w) > 2}
    act_tokens = {w for w in re.findall(r"[a-z0-9]+", actual.lower()) if w not in stop and len(w) > 2}
    if not exp_tokens:
        return 1.0
    return len(exp_tokens & act_tokens) / len(exp_tokens)


async def run_evaluation(
    twin_fn: Callable[[str], Awaitable[Dict[str, Any]]],
    limit: int | None = None,
) -> Dict[str, Any]:
    """
    Τρέχει τα test_scenarios απέναντι στη συνάρτηση του Twin και τα συγκρίνει με το test_ground_truth.
    """
    scenarios = _load_jsonl(SCENARIOS_PATH)
    gt_list = _load_jsonl(GROUND_TRUTH_PATH)
    gt_map = {item["scenario_id"]: item for item in gt_list}

    if limit:
        scenarios = scenarios[:limit]

    results = []
    risk_hits = 0
    rule_hits = 0
    decision_scores = []

    for sc in scenarios:
        sid = sc["scenario_id"]
        gt = gt_map.get(sid)
        if not gt:
            continue

        prompt = f"Context ({sc['domain']} - {sc['date']}): {sc['situation']}\nQuestion: {sc['question']}"
        twin_out = await twin_fn(prompt)

        twin_reply = twin_out.get("twin_reply", "")
        applied_rules = " ".join(twin_out.get("explanation", {}).get("applied_rules", []))
        full_output = f"{twin_reply} {applied_rules}"

        predicted_risk = _extract_risk_level(full_output)
        risk_match = predicted_risk == gt["risk_level"].lower()
        if risk_match:
            risk_hits += 1

        # Έλεγχος αν εντοπίστηκε ο κανόνας (π.χ. M1 ή C-FI)
        base_rule = gt["rule_id"].rstrip("0123456789") if not gt["rule_id"].startswith("M") else gt["rule_id"]
        rule_match = (gt["rule_id"].lower() in full_output.lower()) or (base_rule.lower() in full_output.lower())
        if rule_match:
            rule_hits += 1

        overlap = _token_overlap(f"{gt['decision']} {gt['rationale']}", twin_reply)
        decision_scores.append(overlap)

        scenario_score = round(
            ((1.0 if risk_match else 0.0) * 0.45 + (1.0 if rule_match else 0.0) * 0.25 + overlap * 0.30) * 100,
            1,
        )

        results.append({
            "scenario_id": sid,
            "domain": sc["domain"],
            "situation": sc["situation"],
            "expected_risk": gt["risk_level"],
            "predicted_risk": predicted_risk,
            "risk_match": risk_match,
            "expected_rule": gt["rule_id"],
            "rule_match": rule_match,
            "human_decision": gt["decision"],
            "human_rationale": gt["rationale"],
            "twin_reply": twin_reply,
            "fidelity_score": scenario_score,
        })

    total = len(results) or 1
    risk_acc = round((risk_hits / total) * 100, 1)
    rule_acc = round((rule_hits / total) * 100, 1)
    semantic_acc = round((sum(decision_scores) / total) * 100, 1)
    overall_fidelity = round(risk_acc * 0.45 + rule_acc * 0.25 + semantic_acc * 0.30, 1)

    return {
        "summary": {
            "total_scenarios": len(results),
            "overall_fidelity": overall_fidelity,
            "risk_accuracy": risk_acc,
            "rule_match_rate": rule_acc,
            "decision_alignment": semantic_acc,
        },
        "cases": results,
    }