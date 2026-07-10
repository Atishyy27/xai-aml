import React, { useEffect, useState } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import NetworkView from "./components/NetworkView";
import { getModelCard } from "./api";
import { useFetch } from "./lib/useFetch";

/* The old file also declared a <NetworkViewWrapper> that pulled `networkId` from
 * useParams and passed it down -- but it was never referenced by any route, and
 * NetworkView reads useParams itself. Removed. */

const useTheme = () => {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") ?? "system");
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);
  return [theme, setTheme];
};

function ModelCard() {
  const { data } = useFetch(() => getModelCard(), []);
  if (!data?.classifier?.macro_f1) return null;
  const { macro_f1, n_test } = data.classifier;
  return (
    <span className="model-card" title={`Evaluated on ${n_test.toLocaleString()} held-out accounts`}>
      Pattern classifier · macro-F1 {macro_f1.toFixed(2)} on held-out data
    </span>
  );
}

export default function App() {
  const [theme, setTheme] = useTheme();
  const next = { system: "light", light: "dark", dark: "system" }[theme];

  return (
    <BrowserRouter>
      <div className="shell">
        <header className="topbar">
          <Link to="/" className="brand">
            <img src="/logo.png" alt="" className="brand__mark" />
            <span>
              <strong>SENTINEL</strong>
              <span className="brand__sub">Explainable AML detection</span>
            </span>
          </Link>

          <div className="topbar__right">
            <ModelCard />
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setTheme(next)}
              aria-label={`Theme: ${theme}. Switch to ${next}.`}
            >
              {{ system: "Auto", light: "Light", dark: "Dark" }[theme]}
            </button>
          </div>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/network/:networkId" element={<NetworkView />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
