import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";

const theme = createTheme({
  palette: { primary: { main: "#4b3fbf" }, secondary: { main: "#f59e0b" } },
  shape: { borderRadius: 10 },
  typography: { fontFamily: "Inter, system-ui, sans-serif" },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </StrictMode>,
);
