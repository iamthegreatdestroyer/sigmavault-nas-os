/**
 * SigmaVault NAS OS - Main Application Entry Point
 * @module App
 *
 * Root component with providers, routing, and WebSocket connection.
 */

import * as React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
// Note: Install @tanstack/react-query-devtools for development debugging
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import * as RadixTooltip from "@radix-ui/react-tooltip";
import * as RadixToast from "@radix-ui/react-toast";
import { MainLayout } from "@components/layout";
import { Dashboard } from "@pages/Dashboard";
import { useWebSocket } from "@hooks/useWebSocket";
import { useAppStore } from "@stores/appStore";
import { FullPageLoader } from "@components/ui";

// ============================================================================
// Query Client Configuration
// ============================================================================

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      gcTime: 5 * 60 * 1000, // 5 minutes
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});

// ============================================================================
// WebSocket Connection Manager
// ============================================================================

function WebSocketManager({ children }: { children: React.ReactNode }) {
  const setWsConnected = useAppStore((state) => state.setWsConnected);
  const setLastMessage = useAppStore((state) => state.setLastMessage);
  const addToQueue = useAppStore((state) => state.addToQueue);

  const { isConnected } = useWebSocket({
    autoConnect: true,
    onOpen: () => {
      setWsConnected(true);
    },
    onClose: () => {
      setWsConnected(false);
    },
    onMessage: (message) => {
      setLastMessage(message);
      addToQueue(message);
    },
  });

  // Update store when connection status changes
  React.useEffect(() => {
    setWsConnected(isConnected);
  }, [isConnected, setWsConnected]);

  return <>{children}</>;
}

// ============================================================================
// Theme Manager
// ============================================================================

function ThemeManager({ children }: { children: React.ReactNode }) {
  const theme = useAppStore((state) => state.theme);

  React.useEffect(() => {
    const root = document.documentElement;

    if (theme === "auto") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = () => {
        root.classList.toggle("dark", mediaQuery.matches);
        root.classList.toggle("light", !mediaQuery.matches);
      };
      handleChange();
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }

    root.classList.remove("light", "dark");
    root.classList.add(theme);
  }, [theme]);

  return <>{children}</>;
}

// ============================================================================
// Toast Notifications
// ============================================================================

function ToastNotifications() {
  const { notifications, removeNotification } = useAppStore((state) => ({
    notifications: state.notifications,
    removeNotification: state.removeNotification,
  }));

  return (
    <RadixToast.Provider swipeDirection="right">
      {notifications.slice(0, 5).map((notification) => (
        <RadixToast.Root
          key={notification.id}
          open={!notification.read}
          onOpenChange={(open) => {
            if (!open) removeNotification(notification.id);
          }}
          className={`
            group pointer-events-auto relative flex w-full items-center justify-between space-x-4
            overflow-hidden rounded-lg border p-4 shadow-lg transition-all
            data-[swipe=cancel]:translate-x-0
            data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)]
            data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)]
            data-[swipe=move]:transition-none
            data-[state=open]:animate-in
            data-[state=closed]:animate-out
            data-[swipe=end]:animate-out
            data-[state=closed]:fade-out-80
            data-[state=closed]:slide-out-to-right-full
            data-[state=open]:slide-in-from-top-full
            bg-bg-secondary border-border-primary
            ${notification.type === "error" ? "border-status-error/50" : ""}
            ${notification.type === "success" ? "border-status-success/50" : ""}
            ${notification.type === "warning" ? "border-status-warning/50" : ""}
          `}
        >
          <div className="flex-1">
            <RadixToast.Title className="text-sm font-semibold text-text-primary">
              {notification.title}
            </RadixToast.Title>
            <RadixToast.Description className="text-sm text-text-secondary mt-1">
              {notification.message}
            </RadixToast.Description>
          </div>
        </RadixToast.Root>
      ))}

      <RadixToast.Viewport
        className="
        fixed top-0 right-0 z-[100]
        flex flex-col gap-2 p-4
        w-full max-w-[420px]
        outline-none
      "
      />
    </RadixToast.Provider>
  );
}

// ============================================================================
// Placeholder Pages
// ============================================================================

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <h1 className="text-2xl font-bold text-text-primary mb-2">{title}</h1>
      <p className="text-text-secondary">Coming soon...</p>
    </div>
  );
}

// ============================================================================
// Application Routes
// ============================================================================

function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/storage" element={<PlaceholderPage title="Storage" />} />
        <Route
          path="/compression"
          element={<PlaceholderPage title="Compression" />}
        />
        <Route
          path="/security"
          element={<PlaceholderPage title="Security" />}
        />
        <Route
          path="/encryption"
          element={<PlaceholderPage title="Encryption" />}
        />
        <Route
          path="/network"
          element={<PlaceholderPage title="PhantomMesh VPN" />}
        />
        <Route
          path="/agents"
          element={<PlaceholderPage title="Agent Swarm" />}
        />
        <Route
          path="/analytics"
          element={<PlaceholderPage title="Analytics" />}
        />
        <Route
          path="/monitoring"
          element={<PlaceholderPage title="Monitoring" />}
        />
        <Route
          path="/settings"
          element={<PlaceholderPage title="Settings" />}
        />
      </Route>
    </Routes>
  );
}

// ============================================================================
// Root Application Component
// ============================================================================

export function App() {
  const [isHydrated, setIsHydrated] = React.useState(false);

  // Wait for Zustand to hydrate from localStorage
  React.useEffect(() => {
    setIsHydrated(true);
  }, []);

  if (!isHydrated) {
    return <FullPageLoader message="Loading SigmaVault..." />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <RadixTooltip.Provider delayDuration={300}>
        <ThemeManager>
          <BrowserRouter>
            <WebSocketManager>
              <AppRoutes />
              <ToastNotifications />
            </WebSocketManager>
          </BrowserRouter>
        </ThemeManager>
      </RadixTooltip.Provider>
      {/* <ReactQueryDevtools initialIsOpen={false} /> */}
    </QueryClientProvider>
  );
}

export default App;
