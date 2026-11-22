import { lazy, StrictMode, Suspense } from "react";
import ReactDOM from "react-dom/client";
import "@fontsource/geist/400.css";
import "@fontsource/geist/500.css";
import "@fontsource/geist/600.css";
import "@fontsource/geist-mono/400.css";
import { StartupBoundary, StartupMessage } from "./components/StartupBoundary";
import "./styles.css";
const App = lazy(() => import("./App"));

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <StartupBoundary>
      <Suspense fallback={<StartupMessage />}>
        <App />
      </Suspense>
    </StartupBoundary>
  </StrictMode>,
);
