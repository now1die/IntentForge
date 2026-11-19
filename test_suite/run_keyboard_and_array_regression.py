from __future__ import annotations
import argparse
import csv, json
from pathlib import Path
from ai.error_predictor import MLCorrectionPredictor
from ai.correction_options import suggest_correction_options
from ai.correction_orchestrator import CorrectionOrchestrator
from ai.correction_safety import repair_key

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'models'/'syntax_error_classifier.joblib'
OUT=ROOT/'test_suite'/'keyboard_array_regression_results.csv'

cases=[]
def add(group, name, source, expected):
    cases.append((group,name,source,expected))

# Keyboard-originated cases: US keyboard Shift omissions and delimiter slips.
add('comparison','dot_to_gt','int main(){ if(x.5){return 0;} }','int main(){ if(x> 5){return 0;} }')
add('comparison','comma_to_lt','int main(){ if(x,5){return 0;} }','int main(){ if(x<5){return 0;} }')
add('comparison','dot_in_while','int main(){ while(x.5){x=x-1;} }','int main(){ while(x> 5){x=x-1;} }')
add('comparison','dot_in_for','int main(){ for(i=0;i.5;i++){x=x+1;} }','int main(){ for(i=0;i> 5;i++){x=x+1;} }')
add('operator','plus_to_assign','int main(){ int x + 5; return 0; }','int main(){ int x = 5; return 0; }')
add('delimiter','array_open_paren','int main(){ int arr(5]; return 0; }','int main(){ int arr[5]; return 0; }')
add('delimiter','array_close_paren','int main(){ int arr[5); return 0; }','int main(){ int arr[5]; return 0; }')
add('delimiter','array_index_paren','int main(){ int arr[5]; arr(i) = 10; return 0; }','int main(){ int arr[5]; arr[i] = 10; return 0; }')
add('delimiter','array_call_mixed','int main(){ int arr[5]; arr(i] = 10; return 0; }','int main(){ int arr[5]; arr[i] = 10; return 0; }')
add('lexical','colon_to_semicolon','int main(){ int x: return 0; }','int main(){ int x; return 0; }')
add('number_shift','nine_to_lparen','int main(){ if 9x > 5) { return 0; } }','int main(){ if (x > 5) { return 0; } }')
add('number_shift','eight_to_times','int main(){ x 8 8; return 0; }','int main(){ x * 8; return 0; }')
add('delimiter','if_bracket_mismatch','int main(){ if [true) { return 0; } }','int main(){ if (true) { return 0; } }')
add('delimiter','while_bracket_mismatch','int main(){ while [true) { return 0; } }','int main(){ while (true) { return 0; } }')
add('delimiter','for_bracket_mismatch','int main(){ for [i=0;i<5;i++) { return 0; } }','int main(){ for (i=0;i<5;i++) { return 0; } }')

# Array-specific correction cases.
for i in range(1, 21):
    add('array',f'missing_close_{i}',f'int main(){{ int arr[{i}; return 0; }}',f'int main(){{ int arr[{i}]; return 0; }}')
    add('array',f'wrong_close_{i}',f'int main(){{ int arr[{i}); return 0; }}',f'int main(){{ int arr[{i}]; return 0; }}')
for i in range(5):
    add('array','index_wrong_open_'+str(i),f'int main(){{ int arr[5]; arr({i}] = 10; return 0; }}',f'int main(){{ int arr[5]; arr[{i}] = 10; return 0; }}')
    add('array','index_wrong_close_'+str(i),f'int main(){{ int arr[5]; arr[{i}) = 10; return 0; }}',f'int main(){{ int arr[5]; arr[{i}] = 10; return 0; }}')

def main():
    parser = argparse.ArgumentParser(description="Check automatic and review-required keyboard repairs.")
    parser.add_argument("--verify", action="store_true", help="fail on crashes or a lost expected correction")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    predictor = MLCorrectionPredictor.load(MODEL)
    orchestrator = CorrectionOrchestrator(predictor)
    rows = []
    for group, name, source, expected in cases:
        row = {"group": group, "name": name, "source": source, "expected": expected}
        try:
            result = orchestrator.correct(source)
            actual = result.corrected_source
            outcome = "AUTOMATIC_EXACT" if actual == expected else "UNEXPECTED"
            if result.stop_reason in {"correction_requires_review", "ambiguous_valid_candidates"} and actual != expected:
                options = suggest_correction_options(source, predictor, use_ollama=False)["options"]
                reviewed_sources = [option["corrected_code"] for option in options]
                for entry in result.history:
                    if entry.validation and entry.validation.valid:
                        reviewed_sources.append(entry.validation.corrected_source)
                expected_key = repair_key(expected)
                if any(repair_key(value) == expected_key for value in reviewed_sources):
                    outcome = "EXPECTED_WITHHELD_REFERENCE_VISIBLE"
                elif repair_key(orchestrator.correct(source, preview=True).corrected_source) == expected_key:
                    outcome = "EXPECTED_ONLY_IN_SIMULATION"
            row.update(actual=actual, success=result.success, exact=actual == expected, stop_reason=result.stop_reason, outcome=outcome)
        except Exception as exc:
            row.update(actual="", success=False, exact=False, stop_reason=f"CRASH:{type(exc).__name__}:{exc}", outcome="CRASH")
        rows.append(row)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "total": len(rows),
        "exact": sum(row["exact"] for row in rows),
        "successful_but_not_exact": sum(row["success"] and not row["exact"] for row in rows),
        "failed": sum(not row["success"] for row in rows),
        "crashes": sum(row["outcome"] == "CRASH" for row in rows),
        "expected_withheld_reference_visible": sum(row["outcome"] == "EXPECTED_WITHHELD_REFERENCE_VISIBLE" for row in rows),
        "expected_only_in_simulation": sum(row["outcome"] == "EXPECTED_ONLY_IN_SIMULATION" for row in rows),
        "unexpected": sum(row["outcome"] == "UNEXPECTED" for row in rows),
    }
    args.out.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return int(args.verify and any(summary[key] for key in ("crashes", "expected_only_in_simulation", "unexpected")))


if __name__ == "__main__":
    raise SystemExit(main())
