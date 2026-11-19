# ML Model + Interactive Correction Verification

## Model
- Classifier: scikit-learn LogisticRegression pipeline with DictVectorizer features
- Classes: 21
- Training records: 2,400
- Train/test split: 1,920 / 480
- Random seed: 42
- Controlled held-out accuracy: 100%

## Classes
1. INSERT_SEMICOLON
2. INSERT_RPAREN
3. INSERT_LPAREN
4. INSERT_RBRACKET
5. INSERT_RBRACE
6. DELETE_EXTRA_TOKEN
7. REPLACE_BRACKET
8. REPLACE_OPERATOR
9. CORRECT_KEYWORD
10. KEYBOARD_GREATER_THAN
11. KEYBOARD_LESS_THAN
12. KEYBOARD_MULTIPLY
13. KEYBOARD_ASSIGNMENT
14. KEYBOARD_SEMICOLON
15. KEYBOARD_LPAREN
16. KEYBOARD_RPAREN
17. ARRAY_DECLARATION_ERROR
18. ARRAY_INDEX_ERROR
19. ARRAY_CALL_ERROR
20. REPAIR_MISMATCHED_DELIMITER
21. DECLARATION_SEPARATOR_ERROR

## Important fixes
- Added source-pattern features and augmented classifier data for parser-early-stop cases such as `if(a.b)`.
- Added `DECLARATION_SEPARATOR_ERROR` and trained it with dedicated examples.
- Added semantic-context training examples for `arr(i)` when `arr` is an array.
- Added interactive alternatives for declaration-separator errors: combined declaration and separate typed declarations.
- Added semantic array-call correction options.
- Added local-progress suggestions when an earlier unrelated grammar error prevents whole-program validation.
- Fixed the frontend preview crash by making Monaco diagnostics optional/default-empty.
- Prevented formatting-only duplicate suggestions from occupying multiple option slots.
- Preserved compiler validation before an option is labelled fully valid.

## Verification
- Full pytest suite: 440 passed.
- General compiler test suite: 220/220 passed.
- Keyboard/array regression: 65/65 exact, 0 crashes.
- Stress suite: 3,758 cases executed, 0 Python exceptions.

## Key interactive examples

### Declaration separator
Input:
`int x;y;`

Options:
- `int x,y;`
- `int x; int y;`

Both are compiler-valid.

### Keyboard comparison
Input:
`if(a.b){return 0;}`

The ML classifier predicts `KEYBOARD_GREATER_THAN` and the UI presents:
`if(a>b){return 0;}`

This is labelled a local repair because the standalone top-level `if` is still outside the Mini-C program grammar.

### Array call
Input:
`int main(){ int arr[5]; int i=2; arr(i) = 10; return 0; }`

The ML classifier predicts `ARRAY_CALL_ERROR` and the UI presents:
`int main(){ int arr[5]; int i=2; arr[i] = 10; return 0; }`
