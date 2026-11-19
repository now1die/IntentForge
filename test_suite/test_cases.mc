/* AI Compiler test corpus: each case is separately evaluated by the Python runner. */

/* V001 | Valid programs | Empty void function | expected=ACCEPTED | actual=ACCEPTED | PASS */
void f() { }

/* V002 | Valid programs | Minimal integer main | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main() { return 0; }

/* V003 | Valid programs | Global integer declaration | expected=ACCEPTED | actual=ACCEPTED | PASS */
int count; int main(){ return 0; }

/* V004 | Valid programs | Global initialized integer | expected=ACCEPTED | actual=ACCEPTED | PASS */
int count = 7; int main(){ return count; }

/* V005 | Valid programs | Global float array | expected=ACCEPTED | actual=ACCEPTED | PASS */
float values[4]; int main(){ return 0; }

/* V006 | Valid programs | All scalar local types | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int i=1; float f=2.5; char c='A'; bool b=true; return i; }

/* V007 | Valid programs | Identifier underscores and digits | expected=ACCEPTED | actual=ACCEPTED | PASS */
int _total2=3; int main(){ int value_9=4; return _total2+value_9; }

/* V008 | Valid programs | Integer literal zero | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=0; return x; }

/* V009 | Valid programs | Large integer literal | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=123456; return x; }

/* V010 | Valid programs | Decimal float | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ float x=3.14159; return 0; }

/* V011 | Valid programs | Float with trailing decimal | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ float x=2.; return 0; }

/* V012 | Valid programs | Float with leading decimal | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ float x=.5; return 0; }

/* V013 | Valid programs | Float with positive exponent | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ float x=1e3; return 0; }

/* V014 | Valid programs | Float with negative exponent | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ float x=2.5e-2; return 0; }

/* V015 | Valid programs | Escaped newline character | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ char c='\n'; return 0; }

/* V016 | Valid programs | Escaped quote character | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ char c='\''; return 0; }

/* V017 | Valid programs | String literal expression | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ "hello world"; return 0; }

/* V018 | Valid programs | Boolean literals | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ bool a=true; bool b=false; return 0; }

/* V019 | Valid programs | Line comment | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=1; // comment
 return x; }

/* V020 | Valid programs | Block comment | expected=ACCEPTED | actual=ACCEPTED | PASS */
/* header */ int main(){ /* inside */ return 0; }

/* V021 | Valid programs | Multiline comment locations | expected=ACCEPTED | actual=ACCEPTED | PASS */
int x; /* one
 two
 three */
int main(){return x;}

/* V022 | Valid programs | Whitespace and blank lines | expected=ACCEPTED | actual=ACCEPTED | PASS */


 int main ( ) { 
 return 0 ; 
 } 


/* O001 | Operators and expressions | Addition | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = 2 + 3; return x; }

/* O002 | Operators and expressions | Subtraction | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = 5 - 3; return x; }

/* O003 | Operators and expressions | Multiplication | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = 2 * 3; return x; }

/* O004 | Operators and expressions | Division | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = 6 / 2; return x; }

/* O005 | Operators and expressions | Modulo | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = 7 % 2; return x; }

/* O006 | Operators and expressions | Mixed arithmetic precedence | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = 1 + 2 * 3 - 4 / 2; return x; }

/* O007 | Operators and expressions | Parentheses override precedence | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = (1 + 2) * 3; return x; }

/* O008 | Operators and expressions | Nested parentheses | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = ((1 + 2) * (3 + 4)); return x; }

/* O009 | Operators and expressions | Assignment chain | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = y = 4; return x; }

/* O010 | Operators and expressions | Plus assignment | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x += 2; return x; }

/* O011 | Operators and expressions | Minus assignment | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x -= 2; return x; }

/* O012 | Operators and expressions | Times assignment | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x *= 2; return x; }

/* O013 | Operators and expressions | Divide assignment | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x /= 2; return x; }

/* O014 | Operators and expressions | Modulo assignment | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x %= 2; return x; }

/* O015 | Operators and expressions | Prefix increment | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; ++x; return x; }

/* O016 | Operators and expressions | Prefix decrement | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; --x; return x; }

/* O017 | Operators and expressions | Postfix increment | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x++; return x; }

/* O018 | Operators and expressions | Postfix decrement | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x--; return x; }

/* O019 | Operators and expressions | Unary plus | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = +2; return x; }

/* O020 | Operators and expressions | Unary minus | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; x = -2; return x; }

/* O021 | Operators and expressions | Less than | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; b = x < y; return x; }

/* O022 | Operators and expressions | Less than or equal | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; b = x <= y; return x; }

/* O023 | Operators and expressions | Greater than | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; b = x > y; return x; }

/* O024 | Operators and expressions | Greater than or equal | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; b = x >= y; return x; }

/* O025 | Operators and expressions | Equality | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; b = x == y; return x; }

/* O026 | Operators and expressions | Inequality | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; b = x != y; return x; }

/* O027 | Operators and expressions | Logical AND | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; b = p && q; return x; }

/* O028 | Operators and expressions | Logical OR | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; b = p || q; return x; }

/* O029 | Operators and expressions | Logical NOT | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=8; int y=3; bool b=false; bool p=true; bool q=false; b = !p; return x; }

/* S001 | Arrays functions and control flow | Array declaration and access | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int a[5]; a[0]=10; return a[0]; }

/* S002 | Arrays functions and control flow | Array index expression | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int a[5]; int i=2; a[i+1]=9; return a[3]; }

/* S003 | Arrays functions and control flow | Array used in arithmetic | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int a[2]; a[0]=3; a[1]=4; return a[0]+a[1]; }

/* S004 | Arrays functions and control flow | Function with two parameters | expected=ACCEPTED | actual=ACCEPTED | PASS */
int add(int a, int b){ return a+b; } int main(){ return add(2,3); }

/* S005 | Arrays functions and control flow | Function with no parameters | expected=ACCEPTED | actual=ACCEPTED | PASS */
int get(){ return 5; } int main(){ return get(); }

/* S006 | Arrays functions and control flow | Float function and widening | expected=ACCEPTED | actual=ACCEPTED | PASS */
float scale(int a){ return a; } int main(){ float x=scale(3); return 0; }

/* S007 | Arrays functions and control flow | Void function with empty return | expected=ACCEPTED | actual=ACCEPTED | PASS */
void log(){ return; } int main(){ log(); return 0; }

/* S008 | Arrays functions and control flow | Recursive function syntax | expected=ACCEPTED | actual=ACCEPTED | PASS */
int fact(int n){ if(n<=1) return 1; else return n*fact(n-1); } int main(){return fact(4);}

/* S009 | Arrays functions and control flow | Function call used in expression | expected=ACCEPTED | actual=ACCEPTED | PASS */
int twice(int x){return x*2;} int main(){return twice(4)+1;}

/* S010 | Arrays functions and control flow | Function call with no arguments | expected=ACCEPTED | actual=ACCEPTED | PASS */
int answer(){return 42;} int main(){return answer();}

/* S011 | Arrays functions and control flow | Nested blocks | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=1; { int y=2; x=x+y; } return x; }

/* S012 | Arrays functions and control flow | Scope shadowing | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=1; { float x=2.0; x=x+1.0; } return x; }

/* S013 | Arrays functions and control flow | If without else | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ bool ok=true; if(ok){ return 1; } return 0; }

/* S014 | Arrays functions and control flow | If and else | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=1; if(x>0) x++; else x--; return x; }

/* S015 | Arrays functions and control flow | Nested if else | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=1; if(x>0){ if(x==1) x++; else x--; } return x; }

/* S016 | Arrays functions and control flow | While loop | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=0; while(x<3){x++;} return x; }

/* S017 | Arrays functions and control flow | For loop with declaration | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int s=0; for(int i=0; i<5; i++){s+=i;} return s; }

/* S018 | Arrays functions and control flow | For loop with empty initializer | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int i=0; for(;i<3;i++){ } return i; }

/* S019 | Arrays functions and control flow | For loop with empty condition and update | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int i=0; for(;;){i++; break;} return i; }

/* S020 | Arrays functions and control flow | For loop expression initializer | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int i=0; for(i=0;i<2;i++){continue;} return i; }

/* S021 | Arrays functions and control flow | Break inside while | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ while(true){break;} return 0; }

/* S022 | Arrays functions and control flow | Continue inside for | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ for(int i=0;i<2;i++){continue;} return 0; }

/* S023 | Arrays functions and control flow | Empty statement | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ ; return 0; }

/* S024 | Arrays functions and control flow | Empty block | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ { } return 0; }

/* S025 | Arrays functions and control flow | Multiple global declarations | expected=ACCEPTED | actual=ACCEPTED | PASS */
int a=1; float b=2.0; bool flag=true; int main(){return a;}

/* S026 | Arrays functions and control flow | Declaration after statement | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=0; x++; int y=2; return x+y; }

/* S027 | Arrays functions and control flow | Else associates with nearest if | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){bool a=true; bool b=false; if(a) if(b) a=false; else a=true; return 0;}

/* S028 | Arrays functions and control flow | Return expression with precedence | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){return 1+2*3;}

/* L001 | Lexical errors | Illegal at sign | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ int x=1 @ 2; return x; }

/* L002 | Lexical errors | Illegal dollar sign | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ int $x=1; return 0; }

/* L003 | Lexical errors | Hash outside supported preprocessor syntax | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
#include <stdio.h>
int main(){return 0;}

/* L004 | Lexical errors | Malformed number letters | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ int x=12abc; return 0; }

/* L005 | Lexical errors | Malformed numeric suffix | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ int x=2value; return 0; }

/* L006 | Lexical errors | Multiple decimal points | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ float x=1.2.3; return 0; }

/* L007 | Lexical errors | Malformed exponent letters | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ float x=1ehello; return 0; }

/* L008 | Lexical errors | Incomplete exponent sign | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ float x=1e+; return 0; }

/* L009 | Lexical errors | Hex literal not supported | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ int x=0x10; return 0; }

/* L010 | Lexical errors | Multi-character char | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ char c='ab'; return 0; }

/* L011 | Lexical errors | Empty character literal | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ char c=''; return 0; }

/* L012 | Lexical errors | Unterminated char literal | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ char c='a; return 0; }

/* L013 | Lexical errors | Unterminated string literal | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ "hello; return 0; }

/* L014 | Lexical errors | Unterminated block comment | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ return 0; } /* never closed

/* L015 | Lexical errors | Unicode start not supported for identifiers | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ int évalue=1; return 0; }

/* L016 | Lexical errors | Single ampersand unsupported | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ int x=1 & 2; return 0; }

/* L017 | Lexical errors | Single pipe unsupported | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ int x=1 | 2; return 0; }

/* X001 | Syntax errors and unsupported constructs | Missing semicolon after declaration | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int x=1 return x; }

/* X002 | Syntax errors and unsupported constructs | Missing semicolon after assignment | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int x=1; x=2 return x; }

/* X003 | Syntax errors and unsupported constructs | Missing closing brace | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ return 0;

/* X004 | Syntax errors and unsupported constructs | Missing opening brace | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main() return 0; }

/* X005 | Syntax errors and unsupported constructs | Missing closing parenthesis | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ if(true { return 1; } return 0; }

/* X006 | Syntax errors and unsupported constructs | Missing opening parenthesis | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ if true) return 1; return 0; }

/* X007 | Syntax errors and unsupported constructs | Dangling else | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ else return 0; }

/* X008 | Syntax errors and unsupported constructs | If missing condition | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ if() return 1; return 0; }

/* X009 | Syntax errors and unsupported constructs | While missing condition | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ while() break; return 0; }

/* X010 | Syntax errors and unsupported constructs | For missing separator | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ for(int i=0 i<3; i++){ } return 0; }

/* X011 | Syntax errors and unsupported constructs | Array missing closing bracket | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int a[5; return 0; }

/* X012 | Syntax errors and unsupported constructs | Array access missing index | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int a[5]; return a[]; }

/* X013 | Syntax errors and unsupported constructs | Array access missing closing bracket | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int a[5]; return a[1; }

/* X014 | Syntax errors and unsupported constructs | Function call missing closing parenthesis | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int f(){return 1;} int main(){return f(;}

/* X015 | Syntax errors and unsupported constructs | Missing right operand | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int x=1+; return x; }

/* X016 | Syntax errors and unsupported constructs | Missing left operand | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int x=*2; return x; }

/* X017 | Syntax errors and unsupported constructs | Adjacent identifiers in expression | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int a=1; int b=2; a b; return 0; }

/* X018 | Syntax errors and unsupported constructs | Function prototype unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int add(int a, int b); int main(){return 0;}

/* X019 | Syntax errors and unsupported constructs | Member access a dot b in program | expected=REJECTED | actual=SYNTAX_ERROR | PASS */
int main(){ int a=1; a.b; return 0; }

/* X020 | Syntax errors and unsupported constructs | Exact snippet a dot b semicolon | expected=REJECTED | actual=SYNTAX_ERROR | PASS */
a.b;

/* X021 | Syntax errors and unsupported constructs | Pointer declaration unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int *p; return 0; }

/* X022 | Syntax errors and unsupported constructs | Pointer dereference unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int x=1; return *x; }

/* X023 | Syntax errors and unsupported constructs | Address-of operator unsupported | expected=REJECTED | actual=LEXICAL_ERROR | PASS */
int main(){ int x=1; int p=&x; return 0; }

/* X024 | Syntax errors and unsupported constructs | Struct unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
struct Point { int x; }; int main(){return 0;}

/* X025 | Syntax errors and unsupported constructs | Typedef unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
typedef int Number; int main(){return 0;}

/* X026 | Syntax errors and unsupported constructs | Goto unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ goto label; return 0; }

/* X027 | Syntax errors and unsupported constructs | Ternary operator unsupported | expected=REJECTED | actual=LEXICAL_ERROR | PASS */
int main(){ int x=1; int y=x ? 2 : 3; return y; }

/* X028 | Syntax errors and unsupported constructs | Cast syntax unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ float x=2.0; return (int)x; }

/* X029 | Syntax errors and unsupported constructs | sizeof unsupported | expected=REJECTED | actual=SEMANTIC_ERROR | PASS */
int main(){ int x=1; return sizeof(x); }

/* X030 | Syntax errors and unsupported constructs | Bitwise shift unsupported | expected=REJECTED | actual=SYNTAX_ERROR | PASS */
int main(){ int x=1<<2; return x; }

/* X031 | Syntax errors and unsupported constructs | Comma expression unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int x=1; int y=2; x, y; return 0; }

/* X032 | Syntax errors and unsupported constructs | Multidimensional array unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int matrix[2][3]; return 0; }

/* X033 | Syntax errors and unsupported constructs | Array initializer unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int a[3]={1,2,3}; return 0; }

/* X034 | Syntax errors and unsupported constructs | Preprocessor include unsupported | expected=REJECTED | actual=LEXICAL_ERROR | PASS */
#include <stdio.h>
int main(){ return 0; }

/* X035 | Syntax errors and unsupported constructs | Wrong closing delimiter | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int x=1; return x; ]

/* X036 | Syntax errors and unsupported constructs | Extra closing parenthesis | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main()){ return 0; }

/* X037 | Syntax errors and unsupported constructs | Comma-separated variable declaration supported | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int a=1, b=2; return a+b; }

/* X038 | Syntax errors and unsupported constructs | Void-only parameter list unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(void){ return 0; }

/* X039 | Syntax errors and unsupported constructs | Switch statement unsupported | expected=REJECTED | actual=LEXICAL_ERROR | PASS */
int main(){ switch(1){ case 1: return 1; } return 0; }

/* X040 | Syntax errors and unsupported constructs | Do-while statement unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ do { } while(false); return 0; }

/* X041 | Syntax errors and unsupported constructs | Arrow member access unsupported | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ int x=1; x->value; return 0; }

/* X042 | Syntax errors and unsupported constructs | Empty source | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */


/* M001 | Semantic errors | Undeclared identifier assignment | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ x=1; return 0; }

/* M002 | Semantic errors | Use before declaration | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ x=1; int x; return 0; }

/* M003 | Semantic errors | Inner scope identifier escaped | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ {int inner=1;} return inner; }

/* M004 | Semantic errors | Duplicate local declaration | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int x=1; float x=2.0; return 0; }

/* M005 | Semantic errors | Duplicate function parameter | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int f(int x, float x){return 0;}

/* M006 | Semantic errors | Duplicate global declaration | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int x; int x; int main(){return 0;}

/* M007 | Semantic errors | Void variable | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ void x; return 0; }

/* M008 | Semantic errors | Void array | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ void a[3]; return 0; }

/* M009 | Semantic errors | Int assigned float | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int x; x=2.5; return 0; }

/* M010 | Semantic errors | Char assigned int | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ char c; c=65; return 0; }

/* M011 | Semantic errors | Bool assigned int | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ bool b; b=1; return 0; }

/* M012 | Semantic errors | Arithmetic with bool | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ bool b=true; int x=b+1; return 0; }

/* M013 | Semantic errors | Logical AND with integer | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ bool b; b=1 && true; return 0; }

/* M014 | Semantic errors | Logical NOT with integer | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ bool b; b=!1; return 0; }

/* M015 | Semantic errors | If condition is integer | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ if(1) return 1; return 0; }

/* M016 | Semantic errors | While condition is integer | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ while(1) break; return 0; }

/* M017 | Semantic errors | Array used as scalar | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int a[3]; int x; x=a; return 0; }

/* M018 | Semantic errors | Index scalar variable | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int x=1; return x[0]; }

/* M019 | Semantic errors | Float array index | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int a[3]; float i=1.2; return a[i]; }

/* M020 | Semantic errors | Array size float | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int a[2.5]; return 0; }

/* M021 | Semantic errors | Function called with too few args | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int add(int a,int b){return a+b;} int main(){return add(1);}

/* M022 | Semantic errors | Function called with too many args | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int add(int a){return a;} int main(){return add(1,2);}

/* M023 | Semantic errors | Function argument wrong type | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int add(int a){return a;} int main(){return add(true);}

/* M024 | Semantic errors | Call scalar as function | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int x=1; return x(); }

/* M025 | Semantic errors | Assign to function name | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int f(){return 1;} int main(){ f=3; return 0; }

/* M026 | Semantic errors | Break outside loop | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ break; return 0; }

/* M027 | Semantic errors | Continue outside loop | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ continue; return 0; }

/* M028 | Semantic errors | Return no value from int function | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int f(){return;} int main(){return 0;}

/* M029 | Semantic errors | Return value from void function | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
void f(){return 1;} int main(){return 0;}

/* M030 | Semantic errors | Return float from int function | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int f(){return 2.5;} int main(){return 0;}

/* M031 | Semantic errors | Void expression used as value | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
void f(){return;} int main(){int x=f(); return 0;}

/* M032 | Semantic errors | Duplicate function definition | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int f(){return 1;} int f(){return 2;}

/* M033 | Semantic errors | Global variable/function collision | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int item; int item(){return 0;}

/* M034 | Semantic errors | String assigned to int | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int x="hi"; return 0; }

/* B001 | Boundary and language edge cases | Keyword case sensitivity | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int If=1; return If; }

/* B002 | Boundary and language edge cases | Keyword misspelling is identifier | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int innt=1; return innt; }

/* B003 | Boundary and language edge cases | Return without expression in void main | expected=ACCEPTED | actual=ACCEPTED | PASS */
void main(){ return; }

/* B004 | Boundary and language edge cases | Integer to float widening initializer | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ float f=2; return 0; }

/* B005 | Boundary and language edge cases | Float narrowing assignment | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ float f=2.0; int i=f; return 0; }

/* B006 | Boundary and language edge cases | Same name in inner block allowed | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int x=1; {int x=2;} return x; }

/* B007 | Boundary and language edge cases | Same name in separate functions allowed | expected=ACCEPTED | actual=ACCEPTED | PASS */
int f(){int x=1;return x;} int g(){int x=2;return x;} int main(){return f()+g();}

/* B008 | Boundary and language edge cases | No implicit declaration of undeclared function | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ return missing(1); }

/* B009 | Boundary and language edge cases | Function used without call | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int f(){return 1;} int main(){int x=f; return 0;}

/* B010 | Boundary and language edge cases | Empty function argument list | expected=ACCEPTED | actual=ACCEPTED | PASS */
int f(){return 1;} int main(){return f();}

/* B011 | Boundary and language edge cases | Trailing comma in function call | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int f(int x){return x;} int main(){return f(1,);}

/* B012 | Boundary and language edge cases | Trailing comma in parameters | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int f(int x,){return x;}

/* B013 | Boundary and language edge cases | Trailing comma in declarations | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){int x=1,; return 0;}

/* B014 | Boundary and language edge cases | Negative array size is unary expression | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){int a[-1]; return 0;}

/* B015 | Boundary and language edge cases | Zero array size | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){int a[0]; return 0;}

/* B016 | Boundary and language edge cases | Increment literal is semantically invalid | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ ++1; return 0; }

/* B017 | Boundary and language edge cases | Assignment to arithmetic expression | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int x=1; (x+1)=3; return 0; }

/* B018 | Boundary and language edge cases | Chained calls parsed but callee semantics checked | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int f(){return 1;} int main(){return f()();}

/* B019 | Boundary and language edge cases | String literal compared with string literal | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ bool b; b="a"=="b"; return 0; }

/* B020 | Boundary and language edge cases | Char equality | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ bool b; char a='a'; char c='c'; b=a==c; return 0; }

/* B021 | Boundary and language edge cases | Boolean equality | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ bool b; bool x=true; bool y=false; b=x==y; return 0; }

/* B022 | Boundary and language edge cases | Float relational comparison | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ bool b; b=1.0<2.0; return 0; }

/* B023 | Boundary and language edge cases | Assignment target is prefix update | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int main(){ int x=1; ++x=2; return 0; }

/* B024 | Boundary and language edge cases | Increment array element | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int a[2]; a[1]++; return 0; }

/* B025 | Boundary and language edge cases | Void parameter rejected semantically | expected=SEMANTIC_ERROR | actual=SEMANTIC_ERROR | PASS */
int f(void x){return 0;} int main(){return 0;}

/* B026 | Boundary and language edge cases | Array bounds are not evaluated | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int a[2]; return a[2]; }

/* B027 | Boundary and language edge cases | Logical precedence combination | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ bool b=false; b=(1<2)||(3<4&&true); return 0; }

/* B028 | Boundary and language edge cases | Division by zero not statically evaluated | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ return 1/0; }

/* R001 | Lexer and parser regression fixes | Incomplete exponent 1e+ is lexical | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ float x=1e+; return 0; }

/* R002 | Lexer and parser regression fixes | Incomplete exponent 1.0e+ is lexical | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ float x=1.0e+; return 0; }

/* R003 | Lexer and parser regression fixes | Incomplete exponent .5e- is lexical | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ float x=.5e-; return 0; }

/* R004 | Lexer and parser regression fixes | Double sign in exponent is lexical | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ float x=1e+-2; return 0; }

/* R005 | Lexer and parser regression fixes | Valid exponent with plus remains accepted | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ float x=1.0e+8; return 0; }

/* R006 | Lexer and parser regression fixes | Valid small exponent remains accepted | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ float x=.5e-2; return 0; }

/* R007 | Lexer and parser regression fixes | Huge finite-type overflow rejected | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ float x=1e999999999999999999999999; return 0; }

/* R008 | Lexer and parser regression fixes | Unknown character escape rejected | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ char c='\q'; return 0; }

/* R009 | Lexer and parser regression fixes | Unknown string escape rejected | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ "\q"; return 0; }

/* R010 | Lexer and parser regression fixes | Incomplete hexadecimal escape rejected | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ char c='\x4'; return 0; }

/* R011 | Lexer and parser regression fixes | Escaped backslash character accepted | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ char c='\\'; return 0; }

/* R012 | Lexer and parser regression fixes | Escaped backslash in string accepted | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ "\\"; return 0; }

/* R013 | Lexer and parser regression fixes | Hexadecimal character escape accepted | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ char c='\x41'; return 0; }

/* R014 | Lexer and parser regression fixes | Unicode escape in character literal rejected | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ char c='\u1234'; return 0; }

/* R015 | Lexer and parser regression fixes | Unicode string escape accepted | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ "\u1234"; return 0; }

/* R016 | Lexer and parser regression fixes | Consecutive multiplication then plus rejected | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ return 1**+8; }

/* R017 | Lexer and parser regression fixes | Plus then consecutive multiplications rejected | expected=SYNTAX_ERROR | actual=SYNTAX_ERROR | PASS */
int main(){ return 1+**8; }

/* R018 | Lexer and parser regression fixes | Comment separating operators accepted | expected=ACCEPTED | actual=ACCEPTED | PASS */
int main(){ int a=1; a=1+/* ok */8; return a; }

/* R019 | Lexer and parser regression fixes | Unterminated comment remains lexical error | expected=LEXICAL_ERROR | actual=LEXICAL_ERROR | PASS */
int main(){ return 0; } /* unfinished

/* R020 | Lexer and parser regression fixes | Member access remains unsupported | expected=REJECTED | actual=SYNTAX_ERROR | PASS */
a.b;
