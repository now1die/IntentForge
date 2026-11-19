# Keyboard and array correction cases

The regression runner `run_keyboard_and_array_regression.py` covers realistic US-QWERTY Shift omissions and array mistakes.

Examples:

```c
if(x.5)                  // intended: if(x > 5)
if(x,5)                  // intended: if(x < 5)
int arr(5];              // intended: int arr[5];
int arr[5);              // intended: int arr[5];
arr(i] = 10;             // intended: arr[i] = 10;
int x + 5;               // intended: int x = 5;
if 9x > 5) { ... }       // intended: if (x > 5) { ... }
x 8 8;                   // intended: x * 8;
int x:                   // intended: int x;
```

Run:

```bash
python test_suite/run_keyboard_and_array_regression.py
```
