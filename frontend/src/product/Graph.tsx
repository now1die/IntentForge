import { useId, useState } from "react";
import { ArrowsOut, Minus, Plus, ArrowCounterClockwise } from "@phosphor-icons/react";
import type { FlowGraph, SourceSpan } from "../types/compiler";

export function layout(graph: FlowGraph) {
  const levels = new Map<number, number>([[graph.entry, 0]]);
  const queue = [graph.entry];
  for (const id of queue) {
    for (const edge of graph.edges) {
      if (edge.source !== id || edge.target === graph.exit || edge.kind === "back" || levels.has(edge.target)) continue;
      levels.set(edge.target, levels.get(id)! + 1);
      queue.push(edge.target);
    }
  }
  const last = Math.max(...levels.values());
  levels.set(graph.exit, last + 1);
  const groups = new Map<number, FlowGraph["blocks"]>();
  for (const block of graph.blocks) {
    const level = levels.get(block.id) ?? last + 2;
    const group = groups.get(level) ?? [];
    group.push(block);
    groups.set(level, group);
  }
  const width = Math.max(350, ...[...groups.values()].map((rows) => rows.length * 177 + 60));
  const height = 70 + Math.max(...groups.keys()) * 108;
  const points = new Map<number, { x: number; y: number }>();
  for (const [level, rows] of groups) {
    rows.forEach((block, index) => points.set(block.id, {
      x: width / 2 + (index - (rows.length - 1) / 2) * 177, y: 35 + level * 108,
    }));
  }
  return { points, width, height };
}

const names: Record<string, string> = { entry: "Entry", exit: "Exit", loop_header: "Loop condition", loop_latch: "Loop update",
  branch: "Conditional", return: "Return", statement: "Statement", break: "Break", continue: "Continue" };
const baseView = { x: 0, y: 0, zoom: 1 };

export function FlowDiagram({ graph, code, onLocate, compact = false }: {
  graph: FlowGraph; code: string; onLocate: (span: SourceSpan) => void; compact?: boolean;
}) {
  const [selection, setSelection] = useState(graph.entry);
  const [view, setView] = useState(baseView);
  const [pan, setPan] = useState<{ x: number; y: number; startX: number; startY: number } | null>(null);
  const arrow = useId();
  const { points, width, height } = layout(graph);
  const block = graph.blocks.find(({id}) => id === selection) ?? graph.blocks[0];
  const adjacent = graph.edges.filter(e => e.source === block.id || e.target === block.id);
  const codeLines = code.split("\n");
  const label = (kind: string) => kind === "back" ? "Loop back" : kind.charAt(0).toUpperCase() + kind.slice(1);
  const excerpt = (node: typeof block) => {
    if (node.kind === "entry" || node.kind === "exit") return names[node.kind];
    const line = codeLines[node.span.start.line - 1]?.trim();
    return line ? line.length > 20 ? line.slice(0, 19) + "…" : line : names[node.kind];
  };
  function zoomBy(delta: number) {
    setView((old) => ({ ...old, zoom: Math.max(.5, Math.min(3, old.zoom + delta)) }));
  }
  return <div className={`flow-diagram ${compact ? "flow-compact" : ""}`}>
    <div className="flow-canvas">
      {!compact && <div className="graph-tools" role="group" aria-label="Graph controls">
        <button type="button" aria-label="Zoom in" onClick={() => zoomBy(.25)}><Plus size={16} /></button>
        <button type="button" aria-label="Zoom out" onClick={() => zoomBy(-.25)}><Minus size={16} /></button>
        <button type="button" aria-label="Fit graph" onClick={() => setView(baseView)}><ArrowsOut size={16} /></button>
        <button type="button" aria-label="Reset graph" onClick={() => { setView(baseView); setSelection(graph.entry); }}><ArrowCounterClockwise size={16} /></button>
      </div>}
      <svg role="group" aria-label="Control-flow graph" viewBox={`0 0 ${width} ${height}`} data-zoom={view.zoom}
        onPointerDown={(e) => {
          if (compact || (e.target as Element).closest("[data-block]")) return;
          e.currentTarget.setPointerCapture(e.pointerId);
          setPan({ x:e.clientX, y:e.clientY, startX:view.x, startY:view.y });
        }} onPointerMove={(e) => {
          if (!pan) return;
          const bounds = e.currentTarget.getBoundingClientRect();
          const scale = Math.max(width / bounds.width, height / bounds.height);
          setView((old) => ({...old, x:pan.startX + (e.clientX - pan.x) * scale, y:pan.startY + (e.clientY - pan.y) * scale}));
        }} onPointerUp={() => setPan(null)} onPointerCancel={() => setPan(null)}>
        <defs><marker id={arrow} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0 0L8 4 0 8Z" fill="var(--brand-primary)" />
        </marker></defs>
        <g transform={`translate(${view.x + width * (1 - view.zoom) / 2} ${view.y + height * (1 - view.zoom) / 2}) scale(${view.zoom})`}>
          {graph.edges.map((edge, index) => {
            const a = points.get(edge.source)!;
            const b = points.get(edge.target)!;
            const back = edge.kind === "back" || b.y <= a.y;
            const right = Math.min(width - 12, Math.max(a.x, b.x) + 114 + (index % 4) * 12);
            const middle = (a.y + b.y) / 2;
            const fromY = a.y + 26;
            const toY = b.y - 28;
            const d = back ? `M${a.x + 72} ${a.y}H${right}V${b.y}H${b.x + 74}`
              : `M${a.x} ${fromY}V${middle}H${b.x}V${toY}`;
            return <g key={index} data-edge={edge.kind} data-from={edge.source} data-to={edge.target}>
              <path d={d} markerEnd={`url(#${arrow})`} />
              {["true", "false", "back"].includes(edge.kind) && <text x={back ? right - 3 : b.x + 8}
                y={back ? b.y + 17 : toY - 6} textAnchor={back ? "end" : "start"}>{label(edge.kind)}</text>}
            </g>;
          })}
          {graph.blocks.map((node) => {
            const p = points.get(node.id)!;
            const conditional = ["loop_header", "branch"].includes(node.kind);
            return <g key={node.id} data-block={node.id} data-kind={node.kind} data-selected={node.id === block.id}
              data-unreachable={!node.reachable || undefined} transform={`translate(${p.x} ${p.y})`}
              role="button" tabIndex={0} aria-pressed={node.id === block.id} aria-label={`Block ${node.id}, ${names[node.kind] ?? node.kind}`}
              onClick={() => setSelection(node.id)} onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelection(node.id); }
              }}>
              {conditional ? <polygon points="0,-26 76,0 0,26 -76,0" className="graph-conditional" />
                : <rect x="-73" y="-25" width="146" height="50" rx="13" />}
              <text textAnchor="middle" y="-4" className="graph-block-id">B{node.id} · {names[node.kind]}</text>
              {node.kind !== "entry" && node.kind !== "exit" && <text textAnchor="middle" y="14">{excerpt(node)}</text>}
            </g>;
          })}
        </g>
      </svg>
    </div>
    {!compact && <aside className="block-detail" aria-label="Selected block">
      <h3>Block B{block.id}</h3>
      <dl><dt>Type</dt><dd>{names[block.kind]}</dd><dt>Reachable</dt><dd>{block.reachable ? "Yes" : "No"}</dd>
        <dt>Location</dt><dd><button type="button" onClick={() => onLocate(block.span)}>Line {block.span.start.line}</button></dd></dl>
      <h4>Connections</h4>
      <ul>{adjacent.map((edge, index) => <li key={index}>B{edge.source} → B{edge.target} · {label(edge.kind)}</li>)}</ul>
    </aside>}
  </div>;
}
