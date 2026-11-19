import { useState } from "react";
import type { ClangAnalysis, ClangDiagnostic, ClangNode, ClangSpan } from "../types/clang";

type Focus = (span: ClangSpan) => void;

function Location({ span, focus }: { span: ClangSpan; focus: Focus }) {
  const label = `${span.file}:${span.start.line}:${span.start.column}`;
  return span.file === "main.c" ? <button onClick={() => focus(span)}>{label}</button> : <span>{label}</span>;
}

function DiagnosticRow({ diagnostic, focus }: { diagnostic: ClangDiagnostic; focus: Focus }) {
  return <li>
    <b>{diagnostic.severity}</b> {diagnostic.message}
    {diagnostic.code && <code> {diagnostic.code}</code>}
    {diagnostic.span && <Location span={diagnostic.span} focus={focus} />}
    {diagnostic.related.map((span, index) => <Location key={index} span={span} focus={focus} />)}
    {!!diagnostic.notes.length && <ul>{diagnostic.notes.map((note, index) =>
      <DiagnosticRow key={index} diagnostic={note} focus={focus} />,
    )}</ul>}
  </li>;
}

function Branch({ node, children, focus }: { node: ClangNode; children: Map<number | null, ClangNode[]>; focus: Focus }) {
  const [open, setOpen] = useState(false);
  const nested = children.get(node.id) ?? [];
  return <li>
    {nested.length > 0 && <button aria-expanded={open} aria-label={`Toggle ${node.kind}`} onClick={() => setOpen(!open)}>
      {open ? "−" : "+"}
    </button>}
    <code>{node.kind}</code> {node.name} {node.type && <span>· {node.type}</span>}
    {node.span && <Location span={node.span} focus={focus} />}
    {node.spelling_span && <> Spelling <Location span={node.spelling_span} focus={focus} /></>}
    {node.reference !== null && <span> · Declaration #{node.reference}</span>}
    {open && <ul>{nested.map((child) => <Branch key={child.id} node={child} children={children} focus={focus} />)}</ul>}
  </li>;
}

export function ClangEvidence({ analysis, focus }: { analysis: ClangAnalysis | null; focus: Focus }) {
  const [tab, setTab] = useState("Clang diagnostics");
  const unit = analysis?.units[0];
  const children = new Map<number | null, ClangNode[]>();
  for (const node of unit?.nodes ?? []) {
    const group = children.get(node.parent) ?? [];
    group.push(node);
    children.set(node.parent, group);
  }
  return <section className="inspector clang-inspector" aria-label="Clang evidence">
    <div className="clang-tabs" aria-label="Clang views">
      {["Clang diagnostics", "C AST", "C declarations"].map((name) =>
        <button key={name} aria-pressed={tab === name} onClick={() => setTab(name)}>{name}</button>)}
    </div>
    <div className="inspector-body">
      {!unit ? <p>{analysis?.detail ?? "Analyze the editor source to see Clang evidence."}</p> :
        tab === "Clang diagnostics" ? <ul>{unit.diagnostics.length ? unit.diagnostics.map((diagnostic, index) =>
          <DiagnosticRow key={index} diagnostic={diagnostic} focus={focus} />,
        ) : <li>No Clang diagnostics.</li>}</ul> :
        tab === "C AST" ? <><p>AST {unit.ast}</p><ul>{(children.get(null) ?? []).map((node) =>
          <Branch key={node.id} node={node} children={children} focus={focus} />,
        )}</ul></> :
        <ul>{unit.nodes.filter((node) => node.declaration).map((node) => <li key={node.id}>
          <code>#{node.id} {node.name ?? node.kind}</code> {node.type}
          {node.canonical_type && node.canonical_type !== node.type && <> · Canonical {node.canonical_type}</>}
          {node.scope !== null && <> · Scope #{node.scope}</>}
          {node.span && <Location span={node.span} focus={focus} />}
        </li>)}</ul>}
    </div>
  </section>;
}
