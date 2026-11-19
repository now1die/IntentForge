from __future__ import annotations
import csv, json
from pathlib import Path
from ai.error_predictor import MLCorrectionPredictor
from ai.correction_orchestrator import CorrectionOrchestrator

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

predictor=MLCorrectionPredictor.load(MODEL)
rows=[]
for group,name,source,expected in cases:
    try:
        result=CorrectionOrchestrator(predictor).correct(source, auto_apply=True)
        actual=result.corrected_source
        rows.append({'group':group,'name':name,'source':source,'expected':expected,'actual':actual,'success':result.success,'exact':actual==expected,'stop_reason':result.stop_reason})
    except Exception as exc:
        rows.append({'group':group,'name':name,'source':source,'expected':expected,'actual':'','success':False,'exact':False,'stop_reason':f'CRASH:{type(exc).__name__}:{exc}'})

with OUT.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
summary={
    'total':len(rows),
    'exact':sum(r['exact'] for r in rows),
    'successful_but_not_exact':sum(bool(r['success']) and not bool(r['exact']) for r in rows),
    'failed':sum(not bool(r['success']) for r in rows),
    'crashes':sum(str(r['stop_reason']).startswith('CRASH:') for r in rows),
}
(OUT.with_suffix('.json')).write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
