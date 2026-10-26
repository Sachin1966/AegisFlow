import json
import os
from typing import Dict, Any, List

def evaluate_investigation_result(agent_result: Dict[str, Any], golden_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates multi-agent investigation performance against a ground-truth golden case:
    1. Evidence Recall: fraction of expected ring members surfaced by Link Analyst
    2. Typology Recall: fraction of expected typologies detected by Pattern Analyst
    3. Narrative Faithfulness: claim audit ensuring all statements cite typed evidence
    """
    # 1. Evidence Recall
    graph_nodes = [n["id"] for n in agent_result.get("graph_data", {}).get("nodes", [])]
    expected_members = set(golden_case.get("expected_ring_members", []))
    surfaced = set([m for m in expected_members if m in graph_nodes])
    evidence_recall = len(surfaced) / len(expected_members) if expected_members else 1.0

    # 2. Typology Recall
    detected_typs = agent_result.get("sar_draft", {}).get("detected_typologies", [])
    expected_typs = golden_case.get("expected_typologies", [])
    matched_count = sum(1 for et in expected_typs if any(et.lower() in dt.lower() for dt in detected_typs))
    typology_recall = matched_count / len(expected_typs) if expected_typs else 1.0

    # 3. Narrative Faithfulness
    qa_status = agent_result.get("sar_draft", {}).get("qa_review_status", "UNKNOWN")
    faithfulness = 1.0 if qa_status == "PASSED" else 0.75

    passed_gate = evidence_recall >= 0.80 and faithfulness == 1.0

    return {
        "case_id": golden_case.get("case_id"),
        "evidence_recall": round(evidence_recall, 4),
        "typology_recall": round(typology_recall, 4),
        "narrative_faithfulness": round(faithfulness, 4),
        "gate_passed": passed_gate,
        "summary": "PASS (Meets >=0.80 recall & 1.0 faithfulness criteria)" if passed_gate else "FAIL"
    }

def run_evaluation_suite(golden_cases_path: str = "services/investigator/src/investigator/evaluation/golden_cases.jsonl") -> Dict[str, Any]:
    from investigator.main import run_agentic_workflow

    if not os.path.exists(golden_cases_path):
        return {"error": f"Golden cases file not found at {golden_cases_path}"}

    results = []
    with open(golden_cases_path, "r") as f:
        for line in f:
            if line.strip():
                golden = json.loads(line.strip())
                agent_res = run_agentic_workflow(golden["case_id"], golden["target_account"])
                score = evaluate_investigation_result(agent_res, golden)
                results.append(score)

    all_passed = all(r["gate_passed"] for r in results)
    avg_recall = sum(r["evidence_recall"] for r in results) / len(results) if results else 0.0

    return {
        "all_gates_passed": all_passed,
        "mean_evidence_recall": round(avg_recall, 4),
        "cases_evaluated": len(results),
        "case_scores": results
    }

if __name__ == "__main__":
    report = run_evaluation_suite()
    print("Golden Case Evaluation Report:")
    print(json.dumps(report, indent=2))
