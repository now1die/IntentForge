from __future__ import annotations
import csv, json, random, sys, time, traceback
from dataclasses import dataclass, asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parent.parent
# For running inside the user's project, prefer an explicit path argument.
PROJECT_ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
if PROJECT_ROOT is None:
    candidates = [
        HERE.parent / 'ai_compiler_project' / 'ai compiler',
        Path.cwd(),
    ]
    for candidate in candidates:
        if (candidate / 'compiler' / 'parser.py').exists():
            PROJECT_ROOT = candidate
            break
if PROJECT_ROOT is None or not (PROJECT_ROOT / 'compiler' / 'parser.py').exists():
    raise SystemExit('Pass the project root containing compiler/parser.py as the first argument.')
sys.path.insert(0, str(PROJECT_ROOT))
from compiler.parser import MiniCParser
from compiler.semantic_analyzer import analyze_semantics

@dataclass
class Case:
    case_id: str
    group: str
    title: str
    source: str
    expected: str = 'REJECT'
    rationale: str = ''

CASES: list[Case] = []
seen: set[tuple[str, str]] = set()
def add(group: str, title: str, source: str, expected: str = 'REJECT', rationale: str = ''):
    key = (group, source)
    if key in seen:
        return
    seen.add(key)
    CASES.append(Case(f'ST{len(CASES)+1:05d}', group, title, source, expected, rationale))

def wrap_expr(expr: str, context: str) -> str:
    if context == 'decl': return f'int main(){{ int a = {expr}; return 0; }}'
    if context == 'assign': return f'int main(){{ int a=1; a = {expr}; return a; }}'
    if context == 'return': return f'int main(){{ return {expr}; }}'
    if context == 'if': return f'int main(){{ if ({expr}) return 1; return 0; }}'
    if context == 'for': return f'int main(){{ int a=1; for(a=0; {expr}; a++) {{ break; }} return a; }}'
    if context == 'stmt': return f'int main(){{ int a=1; {expr}; return a; }}'
    return expr

# 1) User's specific examples and comment-adjacent controls.
for title, expr, expected, note in [
    ('Consecutive multiply then plus', '1**+8', 'REJECT', 'Two multiplication signs form an invalid binary-expression sequence.'),
    ('Plus then two multiplication signs', '1+**8', 'REJECT', 'Binary plus is followed by an operator where an operand is expected.'),
    ('Unterminated block comment after number', '1/**+8', 'REJECT', 'The comment starts after the number and never closes.'),
    ('Unterminated block comment after plus', '1+/**8', 'REJECT', 'The comment begins where an operand should follow.'),
    ('Closed comment between number and plus', '1/*x*/+8', 'ACCEPT', 'A closed comment acts like whitespace.'),
    ('Closed comment between plus and number', '1+/*x*/8', 'ACCEPT', 'A closed comment acts like whitespace.'),
    ('Closed comment before multiply plus unary plus', '1/*x*/*+8', 'ACCEPT', 'After removing the comment this is 1 * +8.'),
    ('Closed comment separating two stars', '1*/*x*/ *8', 'REJECT', 'After removing the comment, the expression has two consecutive multiplication operators.'),
    ('Comment between two additive operators', '1+/*x*/-8', 'ACCEPT', 'Unary minus is valid on the right operand.'),
    ('Comment between unary minus and operand', '-/*x*/8', 'ACCEPT', 'Unary minus can precede the operand across a comment.'),
]:
    src = wrap_expr(expr, 'decl')
    add('Target star/comment examples', title, src, expected, note)

# 2) Direct lexical edge cases for operators and punctuation.
lexemes = ['@', '$', '#', '`', '~', '^', '&', '|', '\\', '?', ':', '.', '...', '::', '->', '=>', '== =', '&&&', '|||', '!!=', '===', '!==', '%%%%', '////', '/*', '*/', '/*/', '/**/', '/***/', '/* **/', '/*/ */']
for i, bad in enumerate(lexemes, 1):
    add('Lexical punctuation', f'Unsupported or malformed punctuation {i}: {bad!r}', f'int main(){{ int a=1 {bad} 2; return a; }}', 'REJECT', 'Unsupported punctuation/operator or malformed comment sequence.')

# 3) Malformed and boundary numeric literals.
nums = [
    '1e','1E','1e+','1e-','1E+','1E-','0e','0e+','0e-','9e','9e+','9e-',
    '1.0e','1.0e+','1.0e-','1.2E','1.2E+','1.2E-','2.e','2.e+','2.e-',
    '.5e','.5e+','.5e-','1e++2','1e--2','1ee2','1e+-2','1e-+2',
    '00x10','0x','0X1F','0b101','12abc','12xyz','1.2.3','1..2','..5','3._4',
    '1_000','999999999999999999999999999999999999999999999999999999999999999999',
    '1e9999999999999999999999999999999999999999999999999999999',
]
for i, n in enumerate(nums, 1):
    if n.startswith('999999999999999999') or n.startswith('1e999999999999999999'):
        expected = 'REVIEW'
    else:
        expected = 'LEXICAL_ERROR' if any(c.isalpha() for c in n) or '_' in n or n.count('.') > 1 or n.startswith('0x') or n.startswith('0X') or n.startswith('0b') else 'REJECT'
    add('Malformed numeric literals', f'Malformed/boundary numeric literal {i}: {n}', f'int main(){{ float a = {n}; return 0; }}', expected, 'Tests number-token boundaries and incomplete exponents/suffixes.')

# 4) Malformed character and string literals.
char_literals = ["''", "'ab'", "'abc'", "'a", "'\\", "'\\x'", "'\\q'", "'\\u1234'", "'\n'", "'\t'", "'\\''", "'\\\\'", "'''", "'a''b'", "'0'", "' '"]
for i, literal in enumerate(char_literals, 1):
    if literal == "'\\q'": exp = 'REVIEW'
    else: exp = 'ACCEPT' if literal in (r"'\n'", r"'\t'", "'\t'", r"'\''", r"'\\'", "'0'", "' '") else 'REJECT'
    add('Character literal edge cases', f'Character literal {i}: {literal!r}', f'int main(){{ char c = {literal}; return 0; }}', exp, 'Malformed, escaped, empty, and multi-character character literals.')
string_literals = ['""','"hello"','"line\\nnext"','"quote: \\""','"\\q"','"\\x"','"\\x41"','"\\u1234"','"unfinished','"backslash at end\\','"multi\nline"','"nul\\0char"','"\\\\"','"\\\""']
for i, literal in enumerate(string_literals, 1):
    if literal == '"\\q"': exp = 'REVIEW'
    else: exp = 'ACCEPT' if literal in ('""','"hello"','"line\\nnext"','"quote: \\\""','"\\x41"','"\\u1234"','"nul\\0char"','"\\\\"','"\\""') else 'REJECT'
    add('String literal edge cases', f'String literal {i}: {literal!r}', f'int main(){{ {literal}; return 0; }}', exp, 'Escape validity, quotes, and termination boundaries.')

# 5) Delimiter and statement syntax mutations.
syntax_fragments = [
    'int main(){ int a=1 return a; }', 'int main(){ int a=1; a=2 return a; }',
    'int main( { return 0; }', 'int main){ return 0; }', 'int main( ){ return 0; ',
    'int main(){ return 0 }', 'int main(){ return ; }', 'int main(){ if(true) return 1; else }',
    'int main(){ if() return 1; }', 'int main(){ if(true { return 0; } }',
    'int main(){ while() { break; } return 0; }', 'int main(){ for(int i=0 i<4; i++){} return 0; }',
    'int main(){ for(int i=0; i<4 i++){} return 0; }', 'int main(){ for(int i=0; i<4; i++ {} return 0; }',
    'int main(){ int a[3; return 0; }', 'int main(){ int a[]; return 0; }',
    'int main(){ int a[3]; a[]=1; return 0; }', 'int main(){ f(,1); return 0; }',
    'int main(){ f(1,); return 0; }', 'int main(){ f(1 2); return 0; }',
    'int main(){ a + ; return 0; }', 'int main(){ *a; return 0; }',
    'int main(){ int a = ; return 0; }', 'int main(){ int = 1; return 0; }',
    'int main(){ bool b = ; return 0; }', 'int main(){ else return 0; }',
    'int main(){ break; }', 'int main(){ continue; }', 'return 0;',
    'int main(){ int a=1;; a=2;;; return a; }', # valid control: extra empty statements are legal
    'int main(){ ;;; return 0; }', # valid control
]
for i, src in enumerate(syntax_fragments, 1):
    exp = 'ACCEPT' if i in (30, 31) else 'REJECT'
    add('Syntax mutations', f'Syntax/delimiter case {i}', src, exp, 'Missing, misplaced, duplicated, or extra delimiters/keywords.')

# 6) Semantic error families (syntactically well-formed).
semantic_srcs = [
    ('Undeclared identifier read','int main(){ return missing; }'),
    ('Undeclared identifier assignment','int main(){ missing=1; return 0; }'),
    ('Duplicate local','int main(){ int a=1; int a=2; return 0; }'),
    ('Duplicate parameter','int f(int a,int a){return a;} int main(){return 0;}'),
    ('Duplicate function','int f(){return 1;} int f(){return 2;} int main(){return 0;}'),
    ('Call undeclared function','int main(){ return nofunc(2); }'),
    ('Call scalar as function','int main(){ int x=2; return x(); }'),
    ('Wrong argument count','int f(int a){return a;} int main(){return f(1,2);}'),
    ('Wrong argument type','int f(int a){return a;} int main(){return f(true);}'),
    ('Void parameter','int f(void a){return 0;} int main(){return 0;}'),
    ('Return wrong type','int f(){return true;} int main(){return 0;}'),
    ('Value returned from void','void f(){return 1;} int main(){return 0;}'),
    ('Missing value in nonvoid','int f(){return;} int main(){return 0;}'),
    ('Assign to literal','int main(){1=2; return 0;}'),
    ('Assign to expression','int main(){int a=1; (a+1)=2; return 0;}'),
    ('Increment literal','int main(){1++; return 0;}'),
    ('Increment expression','int main(){int a=1; (a+1)++; return 0;}'),
    ('Index nonarray','int main(){int a=1; return a[0];}'),
    ('Index noninteger','int main(){int a[2]; return a[true];}'),
    ('Assign array to scalar','int main(){int a[2]; int b=1; b=a; return b;}'),
    ('Use void expression','void f(){return;} int main(){int a=f();return a;}'),
    ('Float to int narrowing','int main(){int a=2.5;return a;}'),
    ('Bool to int assignment','int main(){int a=true;return a;}'),
    ('Arithmetic with bool','int main(){bool a=true; return a+1;}'),
    ('Logical AND integers','int main(){return 1&&2;}'),
    ('If condition nonbool','int main(){if(1) return 1; return 0;}'),
    ('While condition nonbool','int main(){while(1) break; return 0;}'),
    ('Array size wrong type','int main(){int a[true];return 0;}'),
    ('Array size undeclared','int main(){int a[n];return 0;}'),
    ('Use out of scope variable','int main(){{int a=1;} return a;}'),
    ('Break outside loop','int main(){break;return 0;}'),
    ('Continue outside loop','int main(){continue;return 0;}'),
    ('Recursive call with wrong arity','int f(int n){return f();} int main(){return 0;}'),
    ('Array function return unsupported','int main(){return 0;}'),
    ('Modulo float operands','int main(){float a=2.0; return a%1.0;}'),
    ('Compare void call','void f(){return;} int main(){return f()==f();}'),
]
for i, (title, src) in enumerate(semantic_srcs, 1):
    # This is a valid control, not an error case.
    expected = 'ACCEPT' if title == 'Array function return unsupported' else 'REJECT'
    add('Semantic error probes', title, src, expected, 'Well-formed syntax intended to trigger semantic validation.')

# 7) Unary/binary operator juxtaposition, all operator pairs, with whitespace-sensitive variants.
ops = ['+','-','*','/','%','=','+=','-=','*=','/=','%=','++','--','<','<=','>','>=','==','!=','&&','||','!','&','|','^','~','.','?']
styles = [('tight','{a}{b}'), ('spaced','{a} {b}'), ('leftsp','{a} {b}'), ('rightsp','{a}{b} ')]
contexts = ['decl','assign','return','if']
for oi, op1 in enumerate(ops):
    for oj, op2 in enumerate(ops):
        for style_name, templ in styles[:2]:
            expr = templ.format(a=op1, b=op2)
            # These probes intentionally explore whether adjacent operators are tokenized/parsed safely.
            for context in contexts[:2]:
                src = wrap_expr(f'7{expr}2', context)
                add('Operator-pair matrix', f'{style_name}: {op1!r} then {op2!r} in {context}', src, 'OBSERVE', 'Exploratory operator-pair/tokenization probe; result is recorded rather than assumed.')

# 8) A deterministic set of random triple-operator probes.
rng = random.Random(20261025)
for i in range(350):
    chosen = [rng.choice(ops) for _ in range(3)]
    sep = rng.choice(['', ' ', '  '])
    expr = sep.join(chosen)
    context = rng.choice(contexts)
    src = wrap_expr(f'7{expr}2', context)
    add('Random operator triples', f'Triple operator probe {i+1}: {chosen!r}', src, 'OBSERVE', 'Deterministic pseudo-random three-operator sequence.')

# 9) Comment patterns, including incomplete and line-ending cases.
comments = [
    '/*', '/*/', '/**', '/***', '/* *', '/* **', '/* comment', '/* comment\n',
    '/* comment */', '/**/', '/***/', '/* one */ /* two */', '/* one /* two */',
    '// line comment', '// line comment\n', '/* comment */ +', '+ /* comment */ 8',
    '/* comment */ *', '* /* comment */ +', '/*\nline1\nline2\n*/',
]
for i, c in enumerate(comments, 1):
    # embed before or within an expression while preserving each exact comment form
    src = f'int main(){{ int a=1; a = 1+{c}8; return a; }}'
    exp = 'ACCEPT' if c in ('/* comment */', '/**/', '/***/', '/* one */ /* two */', '/* one /* two */', '// line comment\n', '/*\nline1\nline2\n*/', '/* comment */ +') else 'REJECT'
    add('Comment edge cases', f'Comment pattern {i}: {c!r}', src, exp, 'Comment termination, operator adjacency, and newline handling.')

# 10) Common language-construction mutations: arrays, functions, loops, declarations, returns.
mutations = [
 ('Unclosed call','int main(){return f(1;}'),('Missing call argument','int main(){return f();}'),
 ('Trailing comma parameters','int f(int a,){return a;} int main(){return 0;}'),
 ('Missing parameter type','int f(int a, b){return a;} int main(){return 0;}'),
 ('Void with parameter','void f(int a){return;} int main(){return 0;}'),
 ('Type missing','main(){return 0;}'),('Unknown type','integer main(){return 0;}'),
 ('Extra declaration comma','int main(){int a=1,;return 0;}'),('Missing declarator name','int main(){int ;return 0;}'),
 ('Multiple initializer operators','int main(){int a=1=2;return 0;}'),
 ('Nested assignment to variable','int main(){int a=0;int b=0;a=b=3;return a;}'),
 ('Array index semicolon','int main(){int a[2];return a[1;];}'),
 ('Negative array size','int main(){int a[-1];return 0;}'),('Zero array size','int main(){int a[0];return 0;}'),
 ('Function body absent','int f(); int main(){return 0;}'),
 ('Nested function definition','int main(){int f(){return 1;}return 0;}'),
 ('Else without if','int main(){else {return 1;}return 0;}'),
 ('Multiple else','int main(){if(true){}else{}else{}return 0;}'),
 ('Duplicate loop separator','int main(){for(;;;)break;return 0;}'),
 ('Continue after loop','int main(){while(false){} continue;return 0;}'),
 ('Return outside function','return 1;'),('Statement between functions','int f(){return 1;} a=2; int main(){return 0;}'),
 ('Unsupported struct','struct A { int x; }; int main(){return 0;}'),
 ('Unsupported pointer','int main(){int *p;return 0;}'),('Unsupported sizeof','int main(){return sizeof(1); }'),
 ('Unsupported ternary','int main(){int a=1;return a?2:3;}'),
 ('Unsupported member access','int main(){int a=1;return a.b;}'),
 ('Unsupported preprocessor',' #include <stdio.h>\nint main(){return 0;}'),
]
for i, (title, src) in enumerate(mutations, 1):
    # two clearly valid control cases are observation probes, not failures
    exp = 'REVIEW' if title == 'Negative array size' else ('OBSERVE' if title in ('Missing call argument','Nested assignment to variable','Zero array size','Void with parameter','Function body absent') else 'REJECT')
    add('Construct mutation probes', title, src, exp, 'Mutates a declaration, control-flow construct, or unsupported C feature.')

# 11) Deep nesting and truncation stress.
for n in [1,2,3,5,10,20,50,100,200]:
    add('Nesting and truncation', f'{n} nested parentheses valid', 'int main(){return ' + '(' * n + '1' + ')' * n + ';}', 'ACCEPT', 'Valid nested expression; stresses parser nesting.')
    add('Nesting and truncation', f'{n} nested parentheses missing close', 'int main(){return ' + '(' * n + '1' + ')' * max(0,n-1) + ';}', 'REJECT', 'Malformed nested expression with one missing closing parenthesis.')
    add('Nesting and truncation', f'{n} nested braces missing close', 'int main(){' + '{' * n + 'return 0;' + '}' * max(0,n-1) + '}', 'REJECT', 'Malformed nested blocks with one missing closing brace.')
for tail in ['', 'int main()', 'int main(){', 'int main(){return', 'int main(){return 1+', 'int main(){int a=', 'int main(){if(true)', 'int main(){for(;;)', 'int main(){/*', 'int main(){"']:
    add('Nesting and truncation', f'Truncated input: {tail!r}', tail, 'REJECT', 'Empty or truncated source should not be accepted as a complete program.')

# 12) More malformed statement punctuation patterns.
for token in [';',',',')','(','{','}','[',']','+','-','*','/','%','=','==','!=','<','<=','&&','||','!','++','--','+=','*=','/=', 'break','continue','return','if','while','for','int','float','bool','true','false']:
    add('Single-token statement probes', f'Single token in function body: {token!r}', f'int main(){{ {token} return 0; }}', 'OBSERVE', 'Single-token statement boundary fuzz case.')

# Execute through the actual parser and semantic analyzer.
parser = MiniCParser()
results = []
start = time.time()
for index, case in enumerate(CASES, 1):
    t0 = time.time()
    try:
        parsed = parser.parse(case.source)
        sem = analyze_semantics(parsed.ast) if parsed.valid and parsed.ast is not None else None
        if parsed.lexical_errors:
            actual = 'LEXICAL_ERROR'
        elif parsed.syntax_errors:
            actual = 'SYNTAX_ERROR'
        elif parsed.ast is None:
            actual = 'PARSER_ABORT'
        elif sem is not None and sem.diagnostics:
            actual = 'SEMANTIC_ERROR'
        else:
            actual = 'ACCEPTED'
        lex_errors = [{'code': x.code, 'message': x.message, 'lexeme': x.lexeme, 'line': x.span.start.line, 'column': x.span.start.column} for x in parsed.lexical_errors]
        syn_errors = [{'code': x.code, 'message': x.message, 'line': x.span.start.line, 'column': x.span.start.column} for x in parsed.syntax_errors]
        sem_errors = [{'code': x.code, 'message': x.message} for x in (sem.diagnostics if sem is not None else [])]
        exc = ''
    except Exception as e:
        actual = 'CRASH'
        lex_errors, syn_errors, sem_errors = [], [], []
        exc = f'{type(e).__name__}: {e}'
    expected = case.expected
    if expected == 'OBSERVE':
        status = 'OBSERVED'
    elif expected == 'REVIEW':
        status = 'REVIEW_ACCEPTED' if actual == 'ACCEPTED' else 'REVIEW_REJECTED'
    elif expected == 'ACCEPT':
        status = 'PASS' if actual == 'ACCEPTED' else 'FAIL'
    elif expected == 'LEXICAL_ERROR':
        status = 'PASS' if actual == 'LEXICAL_ERROR' else ('WRONG_PHASE' if actual in ('SYNTAX_ERROR','SEMANTIC_ERROR','ACCEPTED') else 'FAIL')
    else: # Reject by any compiler diagnostic
        status = 'PASS' if actual in ('LEXICAL_ERROR','SYNTAX_ERROR','SEMANTIC_ERROR','PARSER_ABORT') else 'FAIL'
    results.append({
        **asdict(case), 'actual': actual, 'test_status': status,
        'lexical_diagnostics': json.dumps(lex_errors, ensure_ascii=False),
        'syntax_diagnostics': json.dumps(syn_errors, ensure_ascii=False),
        'semantic_diagnostics': json.dumps(sem_errors, ensure_ascii=False),
        'exception': exc, 'elapsed_ms': round((time.time()-t0)*1000, 2),
    })
    if index % 300 == 0:
        print(f'Executed {index}/{len(CASES)} tests...', flush=True)

# Outputs
csv_path = HERE / 'AI_Compiler_Stress_Results.csv'
json_path = HERE / 'AI_Compiler_Stress_Results.json'
with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader(); writer.writerows(results)
json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

from collections import Counter
actual_counts = Counter(r['actual'] for r in results)
status_counts = Counter(r['test_status'] for r in results)
failed = [r for r in results if r['test_status'] in ('FAIL','WRONG_PHASE')]
crashes = [r for r in results if r['actual'] == 'CRASH']
rejected = [r for r in results if r['actual'] in ('LEXICAL_ERROR','SYNTAX_ERROR','SEMANTIC_ERROR','PARSER_ABORT')]
report = []
report += ['# AI Compiler Stress-Test Report', '', f'- Project tested: `{PROJECT_ROOT}`', f'- Total cases executed: **{len(results)}**', f'- Runtime: **{time.time()-start:.1f} seconds**', '', '## Actual outcomes', '']
for k,v in actual_counts.most_common(): report.append(f'- **{k}:** {v}')
report += ['', '## Test harness outcome', '']
for k,v in status_counts.most_common(): report.append(f'- **{k}:** {v}')
report += ['', '## Unexpected outcomes', '']
if not failed:
    report.append('No expected-accept cases were rejected and no expected-reject case was accepted in the labeled cases. Exploratory operator probes are recorded as OBSERVED, not treated as pass/fail.')
else:
    for r in failed[:200]:
        report.append(f"- **{r['test_status']} {r['case_id']} — {r['title']}**; expected `{r['expected']}`, actual `{r['actual']}`; source: `{r['source']}`")
report += ['', '## Crash cases', '']
if not crashes: report.append('No Python exceptions occurred in the executed stress cases.')
else:
    for r in crashes: report.append(f"- **{r['case_id']} — {r['title']}**: `{r['exception']}`; source: `{r['source']}`")
report += ['', '## Targeted operator/comment cases', '']
for r in results:
    if r['group'] == 'Target star/comment examples':
        report.append(f"- `{r['source']}` → **{r['actual']}** ({r['test_status']})")
report += ['', '## Review candidates', '']
review = [r for r in results if r['expected'] == 'REVIEW']
if review:
    for r in review:
        report.append(f"- **{r['case_id']} {r['title']}**: observed `{r['actual']}`. {r['rationale']} Source: `{r['source']}`")
else: report.append('No review candidates were marked.')
report += ['', '## Actionable phase mismatches', '']
wrong_phase = [r for r in results if r['test_status'] == 'WRONG_PHASE']
if wrong_phase:
    for r in wrong_phase: report.append(f"- **{r['case_id']} {r['title']}**: expected lexical diagnostic but actual `{r['actual']}`. Source: `{r['source']}`")
else: report.append('No layer-specific lexical expectation mismatches among the marked cases.')
report += ['', '## How to interpret', '', '- `ACCEPTED` means no lexical, syntax, or semantic diagnostics were produced; it does not mean the source was executed at runtime.', '- `OBSERVED` cases are exploratory operator combinations. Their actual outcomes are included so you can identify surprising accepts/rejections without claiming every combination is necessarily invalid.', '- `WRONG_PHASE` indicates that input was rejected, but the diagnostic came from a later compiler phase than expected (useful for lexer bugs).', '- The test harness deliberately records crashes separately from normal compiler diagnostics.', '']
(HERE / 'AI_Compiler_Stress_Report.md').write_text('\n'.join(report), encoding='utf-8')

# Failure-oriented list: all test cases that the compiler rejected, with actual diagnostic phase.
with (HERE / 'AI_Compiler_Rejected_Cases.csv').open('w', newline='', encoding='utf-8-sig') as f:
    fields = ['case_id','group','title','source','expected','actual','test_status','lexical_diagnostics','syntax_diagnostics','semantic_diagnostics','exception']
    writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
    writer.writerows([{k:r.get(k,'') for k in fields} for r in rejected])

print(f'Finished {len(results)} cases in {time.time()-start:.1f}s')
print('Actual outcomes:', dict(actual_counts))
print('Status counts:', dict(status_counts))
print('Outputs:', csv_path, json_path, HERE/'AI_Compiler_Stress_Report.md', HERE/'AI_Compiler_Rejected_Cases.csv')
