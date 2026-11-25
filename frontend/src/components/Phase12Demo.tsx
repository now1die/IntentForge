import { useState } from "react";

const examples = [
  {
    label: "Correct program",
    source: "int main() { int value = 6; return value + 2; }",
    instructions: "Run Analyze and inspect the diagnostics and symbol table.",
  },
  {
    label: "Compiler diagnostic",
    source: "int main() { int value = 6 return value + 2; }",
    instructions: "Run Analyze and open the syntax diagnostic to locate the missing semicolon.",
  },
  {
    label: "Sentinel collision and manual repair",
    source: `int demo(bool write, int input) {
  int value = -1;
  bool present = false;
  if (write) { value = input; present = true; }
  if (value == -1) { return 12; }
  return value;
}`,
    instructions: "Select Phase 12 and Supplied input/output examples in the Intention tab. Use demo as the function. Review the diff before approving. With the private worker available, compare the original and the candidate in Interactive behavioral verification.",
    examples: [{ args: [true, -1], expected_return: -1 }, { args: [false, 5], expected_return: 12 },
      { args: [true, 0], expected_return: 0 }],
  },
  {
    label: "Abstention without a contract",
    source: "int demo(int index) { int data[3]; data[0] = 8; return data[index]; }",
    instructions: "Select Phase 12 and Code only. A physical extent is available, while the intended index and return convention need a specification.",
  },
];

export function Phase12Demo({ onLoad }: { onLoad: (source: string) => void }) {
  const [selected, setSelected] = useState(0);
  const example = examples[selected];
  return <details className="inspector behavior-panel">
    <summary>Phase 12 demo examples</summary>
    <div className="inspector-body">
      <p>Authored Mini-C examples</p>
      <div className="behavior-controls">
        <label>Demo example <select value={selected} onChange={(event) => setSelected(Number(event.target.value))}>
          {examples.map((item, index) => <option key={item.label} value={index}>{item.label}</option>)}
        </select></label>
        <button type="button" onClick={() => onLoad(example.source)}>Load demo source</button>
      </div>
      <p>{example.instructions}</p>
      {example.examples && <details>
        <summary>Demo expectations</summary>
        <p>Intention examples</p>
        <pre>{JSON.stringify(example.examples)}</pre>
        <p>Interactive test vectors</p>
        <pre>{JSON.stringify(example.examples.map((row) => ({ arguments: row.args, expected: row.expected_return })))}</pre>
      </details>}
    </div>
  </details>;
}
