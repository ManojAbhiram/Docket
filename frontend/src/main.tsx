import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";

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
