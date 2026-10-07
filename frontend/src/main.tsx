import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";

// The approved faces (docs/design/DESIGN.md section 3), self-hosted: two weights, Latin subset.
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/ibm-plex-sans-condensed/latin-400.css";
import "@fontsource/ibm-plex-sans-condensed/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@/index.css";

// Mount only. Providers live in App, routes in app/routes.tsx.
const container = document.getElementById("root");
if (!container) {
  throw new Error("index.html has no #root element");
}

// Design directions are a development aid: `?variant=1-instrument-panel` and so on. Not in the production bundle.
if (import.meta.env.DEV) {
  void import("@/design/variants/switch").then((module) => module.applyVariantFromUrl());
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
