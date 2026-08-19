import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import { AppProviders } from "./app/providers";
import { router } from "./app/router";
import "./styles/tokens.css";
import "./styles/global.css";
import "./styles/actionMenu.css";
import "./styles/pilot.css";
import "./styles/volume.css";
import "./styles/volumeInspector.css";
import "./styles/volumeV12.css";
import "./styles/volumeDifference.css";
import "./styles/print.css";

const root = document.getElementById("root");
if (!root) throw new Error("Application root was not found.");

createRoot(root).render(
  <StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </StrictMode>,
);
