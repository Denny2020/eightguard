import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { AuthProvider } from "./auth";
import { loadConfig } from "./config";
import { RouterProvider } from "./router";
import "./styles.css";

const root = createRoot(document.getElementById("root")!);

loadConfig().then(
  (config) =>
    root.render(
      <StrictMode>
        <AuthProvider config={config}>
          <RouterProvider>
            <App />
          </RouterProvider>
        </AuthProvider>
      </StrictMode>,
    ),
  (err) => root.render(<p className="alert error">EightGuard couldn't start: {String(err.message)}</p>),
);
