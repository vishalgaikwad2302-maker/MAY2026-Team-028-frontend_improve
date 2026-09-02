import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App.jsx";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { ComplaintsProvider } from "./context/ComplaintsContext.jsx";
import { OperationalProvider } from "./context/OperationalContext.jsx";
import { BulkPickupProvider } from "./context/BulkPickupContext.jsx";
import { ToastProvider } from "./context/ToastContext.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <ComplaintsProvider>
              <OperationalProvider>
                <BulkPickupProvider>
                  <App />
                </BulkPickupProvider>
              </OperationalProvider>
            </ComplaintsProvider>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>
);