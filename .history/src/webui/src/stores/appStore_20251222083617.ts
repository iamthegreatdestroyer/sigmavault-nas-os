/**
 * SigmaVault NAS OS - Global State Store
 * @module stores/appStore
 *
 * Zustand store for centralized application state management.
 * Follows CQRS pattern with separate read/write concerns.
 */

import { create } from "zustand";
import { devtools, persist, subscribeWithSelector } from "zustand/middleware";
import type {
  Agent,
  AgentSwarmStatus,
  StoragePool,
  StorageVolume,
  PhantomMeshNetwork,
  SystemMetrics,
  DashboardStats,
  Notification,
  WebSocketMessage,
} from "@/types";

// ============================================================================
// State Interfaces
// ============================================================================

interface ThemeState {
  theme: "dark" | "light" | "auto";
  setTheme: (theme: "dark" | "light" | "auto") => void;
}

interface ConnectionState {
  wsConnected: boolean;
  wsReconnecting: boolean;
  apiConnected: boolean;
  lastPing: string | null;
  setWsConnected: (connected: boolean) => void;
  setWsReconnecting: (reconnecting: boolean) => void;
  setApiConnected: (connected: boolean) => void;
  setLastPing: (timestamp: string) => void;
}

interface AgentState {
  agents: Agent[];
  swarmStatus: AgentSwarmStatus | null;
  selectedAgentId: string | null;
  setAgents: (agents: Agent[]) => void;
  updateAgent: (agent: Agent) => void;
  setSwarmStatus: (status: AgentSwarmStatus) => void;
  selectAgent: (id: string | null) => void;
}

interface StorageState {
  pools: StoragePool[];
  volumes: StorageVolume[];
  selectedPoolId: string | null;
  selectedVolumeId: string | null;
  setPools: (pools: StoragePool[]) => void;
  updatePool: (pool: StoragePool) => void;
  setVolumes: (volumes: StorageVolume[]) => void;
  updateVolume: (volume: StorageVolume) => void;
  selectPool: (id: string | null) => void;
  selectVolume: (id: string | null) => void;
}

interface NetworkState {
  meshNetworks: PhantomMeshNetwork[];
  selectedNetworkId: string | null;
  setMeshNetworks: (networks: PhantomMeshNetwork[]) => void;
  updateMeshNetwork: (network: PhantomMeshNetwork) => void;
  selectNetwork: (id: string | null) => void;
}

interface MetricsState {
  currentMetrics: SystemMetrics | null;
  metricsHistory: SystemMetrics[];
  maxHistoryLength: number;
  setCurrentMetrics: (metrics: SystemMetrics) => void;
  addMetricsToHistory: (metrics: SystemMetrics) => void;
  clearMetricsHistory: () => void;
}

interface DashboardState {
  stats: DashboardStats | null;
  isLoading: boolean;
  error: string | null;
  setStats: (stats: DashboardStats) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Notification) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

interface WebSocketState {
  lastMessage: WebSocketMessage | null;
  messageQueue: WebSocketMessage[];
  setLastMessage: (message: WebSocketMessage) => void;
  addToQueue: (message: WebSocketMessage) => void;
  clearQueue: () => void;
}

// Combined store type
type AppStore = ThemeState &
  ConnectionState &
  AgentState &
  StorageState &
  NetworkState &
  MetricsState &
  DashboardState &
  NotificationState &
  WebSocketState;

// ============================================================================
// Store Implementation
// ============================================================================

export const useAppStore = create<AppStore>()(
  devtools(
    subscribeWithSelector(
      persist(
        (set, get) => ({
          // ----------------------------------------------------------------
          // Theme State
          // ----------------------------------------------------------------
          theme: "dark",
          setTheme: (theme) => {
            set({ theme });
            // Apply theme to document
            document.documentElement.classList.remove(
              "dark",
              "light",
              "auto-theme"
            );
            if (theme === "auto") {
              document.documentElement.classList.add("auto-theme");
            } else {
              document.documentElement.classList.add(theme);
            }
          },

          // ----------------------------------------------------------------
          // Connection State
          // ----------------------------------------------------------------
          wsConnected: false,
          wsReconnecting: false,
          apiConnected: false,
          lastPing: null,
          setWsConnected: (connected) => set({ wsConnected: connected }),
          setWsReconnecting: (reconnecting) => set({ wsReconnecting: reconnecting }),
          setApiConnected: (connected) => set({ apiConnected: connected }),
          setLastPing: (timestamp) => set({ lastPing: timestamp }),

          // ----------------------------------------------------------------
          // Agent State
          // ----------------------------------------------------------------
          agents: [],
          swarmStatus: null,
          selectedAgentId: null,
          setAgents: (agents) => set({ agents }),
          updateAgent: (agent) =>
            set((state) => ({
              agents: state.agents.map((a) => (a.id === agent.id ? agent : a)),
            })),
          setSwarmStatus: (status) => set({ swarmStatus: status }),
          selectAgent: (id) => set({ selectedAgentId: id }),

          // ----------------------------------------------------------------
          // Storage State
          // ----------------------------------------------------------------
          pools: [],
          volumes: [],
          selectedPoolId: null,
          selectedVolumeId: null,
          setPools: (pools) => set({ pools }),
          updatePool: (pool) =>
            set((state) => ({
              pools: state.pools.map((p) => (p.id === pool.id ? pool : p)),
            })),
          setVolumes: (volumes) => set({ volumes }),
          updateVolume: (volume) =>
            set((state) => ({
              volumes: state.volumes.map((v) =>
                v.id === volume.id ? volume : v
              ),
            })),
          selectPool: (id) => set({ selectedPoolId: id }),
          selectVolume: (id) => set({ selectedVolumeId: id }),

          // ----------------------------------------------------------------
          // Network State
          // ----------------------------------------------------------------
          meshNetworks: [],
          selectedNetworkId: null,
          setMeshNetworks: (networks) => set({ meshNetworks: networks }),
          updateMeshNetwork: (network) =>
            set((state) => ({
              meshNetworks: state.meshNetworks.map((n) =>
                n.id === network.id ? network : n
              ),
            })),
          selectNetwork: (id) => set({ selectedNetworkId: id }),

          // ----------------------------------------------------------------
          // Metrics State
          // ----------------------------------------------------------------
          currentMetrics: null,
          metricsHistory: [],
          maxHistoryLength: 100,
          setCurrentMetrics: (metrics) => set({ currentMetrics: metrics }),
          addMetricsToHistory: (metrics) =>
            set((state) => ({
              metricsHistory: [
                ...state.metricsHistory.slice(-(state.maxHistoryLength - 1)),
                metrics,
              ],
            })),
          clearMetricsHistory: () => set({ metricsHistory: [] }),

          // ----------------------------------------------------------------
          // Dashboard State
          // ----------------------------------------------------------------
          stats: null,
          isLoading: false,
          error: null,
          setStats: (stats) => set({ stats }),
          setLoading: (loading) => set({ isLoading: loading }),
          setError: (error) => set({ error }),

          // ----------------------------------------------------------------
          // Notification State
          // ----------------------------------------------------------------
          notifications: [],
          unreadCount: 0,
          addNotification: (notification) =>
            set((state) => ({
              notifications: [notification, ...state.notifications].slice(
                0,
                100
              ),
              unreadCount: state.unreadCount + 1,
            })),
          markAsRead: (id) =>
            set((state) => {
              const updated = state.notifications.map((n) =>
                n.id === id ? { ...n, read: true } : n
              );
              return {
                notifications: updated,
                unreadCount: updated.filter((n) => !n.read).length,
              };
            }),
          markAllAsRead: () =>
            set((state) => ({
              notifications: state.notifications.map((n) => ({
                ...n,
                read: true,
              })),
              unreadCount: 0,
            })),
          removeNotification: (id) =>
            set((state) => {
              const updated = state.notifications.filter((n) => n.id !== id);
              return {
                notifications: updated,
                unreadCount: updated.filter((n) => !n.read).length,
              };
            }),
          clearAll: () => set({ notifications: [], unreadCount: 0 }),

          // ----------------------------------------------------------------
          // WebSocket State
          // ----------------------------------------------------------------
          lastMessage: null,
          messageQueue: [],
          setLastMessage: (message) => set({ lastMessage: message }),
          addToQueue: (message) =>
            set((state) => ({
              messageQueue: [...state.messageQueue, message].slice(-50),
            })),
          clearQueue: () => set({ messageQueue: [] }),
        }),
        {
          name: "sigmavault-storage",
          partialize: (state) => ({
            theme: state.theme,
            // Only persist theme and UI preferences
          }),
        }
      )
    ),
    { name: "SigmaVault" }
  )
);

// ============================================================================
// Selectors (for optimized re-renders)
// ============================================================================

export const selectTheme = (state: AppStore) => state.theme;
export const selectWsConnected = (state: AppStore) => state.wsConnected;
export const selectApiConnected = (state: AppStore) => state.apiConnected;
export const selectAgents = (state: AppStore) => state.agents;
export const selectActiveAgents = (state: AppStore) =>
  state.agents.filter(
    (a) => a.status === "active" || a.status === "processing"
  );
export const selectSwarmStatus = (state: AppStore) => state.swarmStatus;
export const selectPools = (state: AppStore) => state.pools;
export const selectHealthyPools = (state: AppStore) =>
  state.pools.filter((p) => p.health === "healthy");
export const selectVolumes = (state: AppStore) => state.volumes;
export const selectMeshNetworks = (state: AppStore) => state.meshNetworks;
export const selectCurrentMetrics = (state: AppStore) => state.currentMetrics;
export const selectDashboardStats = (state: AppStore) => state.stats;
export const selectNotifications = (state: AppStore) => state.notifications;
export const selectUnreadCount = (state: AppStore) => state.unreadCount;

// ============================================================================
// Actions (for external use)
// ============================================================================

export const appActions = {
  setTheme: (theme: "dark" | "light" | "auto") =>
    useAppStore.getState().setTheme(theme),

  addNotification: (
    notification: Omit<Notification, "id" | "timestamp" | "read">
  ) =>
    useAppStore.getState().addNotification({
      ...notification,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      read: false,
    }),

  handleWebSocketMessage: (message: WebSocketMessage) => {
    const store = useAppStore.getState();
    store.setLastMessage(message);
    store.addToQueue(message);

    // Route message to appropriate handler
    switch (message.type) {
      case "metrics_update":
        store.setCurrentMetrics(message.payload as SystemMetrics);
        store.addMetricsToHistory(message.payload as SystemMetrics);
        break;
      case "agent_status":
        store.updateAgent(message.payload as Agent);
        break;
      case "notification":
        store.addNotification(message.payload as Notification);
        break;
      // Add more handlers as needed
    }
  },
};
