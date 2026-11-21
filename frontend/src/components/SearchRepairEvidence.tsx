import type { Phase10Analysis } from "../types/compiler";

const statuses: Record<string,string> = {
  INCOMPLETE_SPECIFICATION: "Supply typed expected outputs for distinct inputs.",
  CONSTRAINTS_ALREADY_AGREE: "Projected results match the supplied expectations.",
  COMPATIBLE_EDIT: "One bounded edit set matches the supplied expectations.",
  MULTIPLE_COMPATIBLE_EDITS: "Several edit sets match the supplied expectations.",
  NO_COMPATIBLE_EDIT: "No supported edit matches every supplied expectation.",
  UNSUPPORTED_PROJECTION: "The program exceeds the supported search model.",
  INSUFFICIENT_SUCCESSFUL_SAMPLES: "More successful original examples are needed.",
  ANALYSIS_LIMITED: "The search projection reached its work limit.",
};

const progressLabels: Record<string,string> = {
  interval: "Shrinking search interval",
  growth: "Increasing window bound",
  remainder: "Decreasing remainder magnitude",
};

export function SearchRepairEvidence({ analysis }: { analysis: Phase10Analysis }) {
  return <section className="guided-evidence" aria-label="Phase 10 search evidence">
    <h4>Phase 10 search evidence</h4>
    <p>{statuses[analysis.status] ?? analysis.status.toLowerCase().replaceAll("_"," ")}</p>
    {!!analysis.arrays?.length && <ul aria-label="Fixed array extents">
      {analysis.arrays.map((array, i) => <li key={i}>
        <code>{array.name}</code> · {array.length} {array.element_type} cells · valid indices 0–{array.length-1} · line {array.span.start.line}
      </li>)}
    </ul>}
    {!!analysis.search_intervals?.length && <ul aria-label="Search intervals">
      {analysis.search_intervals.map((span, i) => <li key={i}>
        {span.recursive ? "Recursive" : "Iterative"} interval <code>[{span.lower}, {span.upper}{span.inclusive ? "]" : ")"}</code>
        {" · "}midpoint <code>{span.midpoint}</code> · extent {span.extent}
        {!!span.sampled_frames?.some((frames) => frames.length) && <details>
          <summary>Supplied call intervals</summary>
          <ul>{span.sampled_frames.map((frames, index) => <li key={index}>
            Input {index+1} · <code>{JSON.stringify(frames)}</code>
          </li>)}</ul>
        </details>}
      </li>)}
    </ul>}
    {!!analysis.progress?.length && <ul aria-label="Sampled progress">
      {analysis.progress.map((loop, i) => <li key={i}>
        {progressLabels[loop.kind] ?? loop.kind} · <code>{loop.function}</code> · line {loop.span.start.line}
      </li>)}
    </ul>}
    {!!analysis.accesses?.length && <details open={analysis.accesses.some((site) => !site.valid)}>
      <summary>Index observations on supplied inputs</summary>
      <ul>{analysis.accesses.map((site, i) => <li key={i}>
        Input {site.sample} · line {site.span.start.line} · {site.access} index {site.minimum}–{site.maximum}
        {" · "}{!site.valid ? "Outside declared extent" : site.access === "write" ? "Checked write" : site.initialized ? "Initialized cells" : "Missing initialization fact"}
      </li>)}</ul>
    </details>}
  </section>;
}
