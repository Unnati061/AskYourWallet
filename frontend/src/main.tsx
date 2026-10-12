import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Self-hosted variable fonts: Inter for UI text, JetBrains Mono for figures.
// Bundled rather than loaded from a CDN so the app works offline and on a
// free-tier host with no external font requests.
import "@fontsource-variable/inter/index.css";
import "@fontsource-variable/jetbrains-mono/index.css";
import "./index.css";

import App from "@/app/App";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("index.html is missing <div id=\"root\">");

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
