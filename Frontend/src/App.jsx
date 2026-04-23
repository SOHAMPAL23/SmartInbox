import React, { useEffect } from "react";
import { BrowserRouter } from "react-router-dom";
import { AppRoutes } from "./routes/AppRoutes";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useStore } from "./store/useStore";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      cacheTime: 1000 * 60 * 30, // 30 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const initAuth = useStore((state) => state.initAuth);

  React.useEffect(() => {
    initAuth();
  }, [initAuth]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 3500,
            style: {
              background: "#FFFFFF",
              color: "#1e293b",
              border: "1px solid #e2e8f0",
              borderRadius: "12px",
              fontSize: "14px",
              fontFamily: "Inter, sans-serif",
              padding: "12px 16px",
              boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
            },
            success: {
              iconTheme: { primary: "#16a34a", secondary: "#fff" },
            },
            error: {
              iconTheme: { primary: "#dc2626", secondary: "#fff" },
            },
          }}
        />
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
