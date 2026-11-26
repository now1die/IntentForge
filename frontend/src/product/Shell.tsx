import { useState, type ReactNode } from "react";
import { ArrowClockwise, BookOpen, BracketsCurly, Code, Flask, Gear, Question, Target } from "@phosphor-icons/react";
import illustration from "./engraving.svg";

export const destinations = {
  compiler: { label: "Compiler", description: "Find syntax and type errors, then explore how the compiler reads your code.", icon: Code },
  intention: { label: "Intention", description: "Describe what your code should do and review changes supported by your examples.", icon: Target },
  research: { label: "Research Lab", description: "Trace program paths, inspect evidence and compare recorded engine results.", icon: Flask },
  examples: { label: "Examples & Learning", description: "Try a Mini-C program and learn how to interpret compiler and repair evidence.", icon: BookOpen },
};

export type Destination = keyof typeof destinations;

export function readDestination(): Destination {
  const hash = window.location.hash.slice(1);
  return Object.hasOwn(destinations, hash) ? hash as Destination : "compiler";
}

export function Engraving({ topic }: { topic: Destination }) {
  return <svg className="engraving" viewBox="0 0 420 175" aria-hidden="true"><use href={`${illustration}#${topic}`} /></svg>;
}

export function ProductShell({ page, connection, execution, refresh, children }: {
  page: Destination;
  connection: string;
  execution: string;
  refresh: () => void;
  children: ReactNode;
}) {
  const [dialog, setDialog] = useState<"settings" | "help" | null>(null);
  const navigate = (sidebar: boolean) => Object.entries(destinations).map(([key, item]) => {
    const Icon = item.icon;
    return <a key={key} href={`#${key}`} aria-current={page === key ? "page" : undefined}
      aria-label={sidebar ? item.label : undefined} title={sidebar ? item.label : undefined}>
      <Icon size={sidebar ? 24 : 18} />{!sidebar && <span>{item.label}</span>}
    </a>;
  });
  const active = destinations[page];
  return <div className="product">
    <a className="product-skip" href="#workspace-main" onClick={(event) => {
      event.preventDefault();
      document.getElementById("workspace-main")?.focus();
    }}>Skip to workspace</a>
    <header className="product-header">
      <a href="#compiler" className="product-wordmark"><BracketsCurly size={30} weight="bold" />
        <span><strong>IntentForge</strong><small>Code Understanding &amp; Intention-Based Repair</small></span>
      </a>
      <nav className="product-top-nav" aria-label="Primary navigation">{navigate(false)}</nav>
      <div className="product-services">
        <span className="product-connectivity" title={execution}><i className={connection === "Backend connected" ? "online" : ""} />{connection}</span>
        <button type="button" aria-label="Settings" title="Settings" onClick={() => setDialog("settings")}><Gear size={22} /></button>
        <button type="button" aria-label="Help" title="Help" onClick={() => setDialog("help")}><Question size={22} /></button>
      </div>
    </header>
    <aside className="product-sidebar">
      <nav aria-label="Workspace sidebar">{navigate(true)}</nav>
      <button type="button" title="Workspace help" aria-label="Workspace help" onClick={() => setDialog("help")}><Question size={24} /></button>
    </aside>
    <main id="workspace-main" className="product-main" tabIndex={-1}>
      <div className="product-intro" key={page}>
        <div><h1>{active.label}</h1><p>{active.description}</p></div>
        <Engraving topic={page} />
      </div>
      {children}
    </main>
    {dialog && <dialog className="product-dialog" ref={(node) => { if (node && !node.open) node.showModal(); }}
      onClose={() => setDialog(null)} aria-labelledby="shell-dialog-title">
      <h2 id="shell-dialog-title">{dialog === "settings" ? "Workspace settings" : "Working with IntentForge"}</h2>
      {dialog === "settings" ? <><p>{connection}</p><p>{execution}</p>
        <button type="button" onClick={refresh}><ArrowClockwise /> Refresh connections</button></>
        : <><p>Start in Compiler. For a behavior problem, give Intention examples of the expected result.</p>
          <p>Review every change before applying it. Runtime observations require the restricted Mini-C worker.</p>
          <a href="#examples" onClick={() => setDialog(null)}>Open the learning guide</a></>}
      <form method="dialog"><button type="submit">Close</button></form>
    </dialog>}
  </div>;
}
