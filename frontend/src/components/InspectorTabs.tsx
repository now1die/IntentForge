import { useEffect, useRef } from "react";
import {
  ListBullets,
  TreeStructure,
  Table,
  Wrench,
  WarningCircle,
  MagnifyingGlass,
  Info,
} from "@phosphor-icons/react";

export const tabs = [
  "Overview",
  "Tokens",
  "AST",
  "Symbol Table",
  "Corrections",
  "Diagnostics",
  "Intention",
] as const;
export type Tab = (typeof tabs)[number];
const icons = [Info, ListBullets, TreeStructure, Table, Wrench, WarningCircle, MagnifyingGlass];

export function InspectorTabs({
  active,
  onChange,
  count,
  product = false,
}: {
  active: Tab;
  onChange: (tab: Tab) => void;
  count: number;
  product?: boolean;
}) {
  const visible = product ? [tabs[0],tabs[1],tabs[2],tabs[3],tabs[5],tabs[4]] : tabs.slice(1);
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    if (product) return;
    const index = tabs.indexOf(active);
    refs.current[index - 1]?.scrollIntoView({
      behavior: "auto",
      block: "nearest",
      inline: "nearest",
    });
  }, [active]);

  return (
    <div className="inspector-tabs-wrap">
      <div
        className="inspector-tabs"
        role="tablist"
        aria-label="Compiler inspector"
      >
        {visible.map((tab, index) => {
          const tabId = tabs.indexOf(tab);
          const Icon = icons[tabId];
          return (
            <button
              ref={(element) => {
                refs.current[index] = element;
              }}
              id={`tab-${tabId}`}
              aria-controls="inspector-content"
              role="tab"
              aria-selected={active === tab}
              tabIndex={active === tab ? 0 : -1}
              key={tab}
              onClick={() => onChange(tab)}
              onKeyDown={(event) => {
                const next =
                  event.key === "ArrowRight"
                    ? (index + 1) % visible.length
                    : event.key === "ArrowLeft"
                      ? (index + visible.length - 1) % visible.length
                      : event.key === "Home"
                        ? 0
                        : event.key === "End"
                          ? visible.length - 1
                          : -1;
                if (next >= 0) {
                  event.preventDefault();
                  onChange(visible[next]);
                  refs.current[next]?.focus();
                }
              }}
            >
              <Icon size={16} />
              {product && tab === "Symbol Table" ? "Symbols" : product && tab === "Corrections" ? "Fixes" : tab}
              {tab === "Diagnostics" && (
                <span className="count">{count}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
