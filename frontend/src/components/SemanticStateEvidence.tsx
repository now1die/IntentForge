import type { Phase12Analysis } from "../types/compiler";

const labels = {
  initialization: "Initialization",
  logical_array: "Logical array",
  inactive_read: "Inactive array read",
  sentinel: "Numeric sentinel",
  presence: "Presence flag",
  coordinate: "Coordinate",
  physical_index: "Physical index",
};
const words = (value: string) => value.toLowerCase().replaceAll("_", " ");

export function SemanticStateEvidence({ analysis }: { analysis: Phase12Analysis }) {
  return <section className="guided-evidence" aria-label="Phase 12 semantic state evidence">
    <h4>Phase 12 semantic state evidence</h4>
    <p>{words(analysis.status)} · {analysis.compatible_candidates} discovery-compatible
      {analysis.compatible_candidates > 0 && " · Independent holdout is separate"}</p>
    {analysis.facts.map((fact, index) => <details key={index} open={fact.kind !== "initialization"}>
      <summary>{labels[fact.kind]} · {fact.name ?? fact.binding}
        {fact.cell != null && `[${fact.cell}]`} · line {fact.span.start.line}</summary>
      <p><code>{fact.function}</code> · binding <code>{fact.binding}</code> · CFG site {fact.cfg_site}</p>
      {fact.initialization && <p>Initialization · {words(fact.initialization)}</p>}
      {fact.presence && <p>Optional presence · {words(fact.presence)}</p>}
      {fact.marker != null && <p>Sentinel {fact.marker} · collision {words(fact.collision ?? "unknown")}</p>}
      {fact.physical_extent != null && <p>Physical extent · {fact.physical_extent} cells</p>}
      {fact.logical_length != null && <p>Logical length · <code>{fact.logical_length}</code></p>}
      {fact.active_interval && <p>Active region · <code>{fact.active_interval}</code></p>}
      {fact.axis && <p>{fact.axis} · {fact.lower} ≤ {fact.name} &lt; {fact.upper_exclusive} · {words(fact.validity ?? "unknown")}</p>}
      {fact.kind === "physical_index" && <p>Physical validity · {words(fact.validity ?? "unknown")}</p>}
      {!!fact.coordinate_observations?.length && <p>Sampled coordinate inputs · {fact.coordinate_observations.map(
        (sample) => `${sample.value} (${words(sample.validity)})`).join(", ")}</p>}
      {!!fact.definitions?.length && <p>Reaching definitions · {fact.definitions.join(", ")}</p>}
      {fact.assumptions?.map((assumption, i) => <p key={i}>{typeof assumption === "string" ? assumption
        : `Path fact ${assumption[0]} ${assumption[1]}, CFG site ${assumption[2]} (${assumption[3]})`}</p>)}
      {!!fact.observations?.length && <ul aria-label="Sampled logical lengths">
        {fact.observations.map((sample) => <li key={sample.input}>Input {sample.input} · length {sample.logical_length}
          {" · "}inactive cells [{sample.inactive_interval.join(", ")})</li>)}
      </ul>}
    </details>)}
    {analysis.withheld.map((item, i) => <p key={i}>Withheld {words(item.category)} · {item.reason}</p>)}
  </section>;
}
