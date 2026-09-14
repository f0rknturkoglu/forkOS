import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./core/queryClient";
const client = queryClient();
import App from "./app/App";

// Fontlar pakete gomulur; offline'da da yuklenir, CDN'e cikilmaz.
import "@fontsource-variable/manrope";
import "@fontsource-variable/newsreader";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
