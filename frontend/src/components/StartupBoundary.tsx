import { Component, type ErrorInfo, type ReactNode } from "react";

export function StartupMessage({ failed = false }: { failed?: boolean }) {
  return (
    <main className="startup-message" role={failed ? "alert" : "status"}>
      <h1>{failed ? "Workbench could not load" : "Loading Compiler Workbench…"}</h1>
      {failed ? (
        <>
          <p>Reload the page. If the problem continues, check the browser Console and Network panels.</p>
          <button className="primary" onClick={() => window.location.reload()}>Reload workbench</button>
        </>
      ) : null}
    </main>
  );
}

export class StartupBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) console.error("Workbench startup failed", error, info.componentStack);
  }

  render() {
    return this.state.failed ? <StartupMessage failed /> : this.props.children;
  }
}
