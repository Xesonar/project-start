import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "@/app/App";
import { initializeTheme } from "@/lib/theme";
import "@/styles/index.css";

initializeTheme();

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js");
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
