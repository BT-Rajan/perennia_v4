import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/global.css";
import "./styles/native.css";
import { applyPlatformAttribute } from "./platform.js";
import App from "./App.jsx";

applyPlatformAttribute();

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
