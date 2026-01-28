/**
 * SigmaVault NAS OS - System Hooks
 * @module hooks/useSystem
 *
 * React hooks for system status and metrics with real-time WebSocket updates.
 * Integrates with Go API (port 12080) and handles graceful degradation.
 *
 * @see docs/WEBSOCKET_PROTOCOL.md for event type specifications
 */

import { useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAppStore, selectCurrentMetrics } from "@/stores/appStore";
import { api, queryKeys } from "@/api/client";
import type { SystemMetrics } from "@/types";

// ============================================================================
// Types
// ============================================================================

interface SystemStatusData {
  hostname: string;
  uptime: number;
  cpu_usage: number;
  memory_used: number;
  memory_total: number;
  memory_pct: number;
  load_average: number[];
  timestamp: number;
  // Graceful degradation fields
  stale?: boolean;
  error_code?: string;
  last_update?: string;
}

interface UseSystemStatusOptions {
  /** Poll interval for REST fallback (default: 30000ms) */
  pollInterval?: number;
  /** Enable real-time WebSocket updates (default: true) */
  enableRealtime?: boolean;
}

interface UseSystemStatusReturn {
  /** Current system metrics */
  metrics: SystemMetrics | null;
  /** Raw status data from WebSocket */
  status: SystemStatusData | null;
  /** Whether data is currently loading */
  isLoading: boolean;
  /** Error if fetch failed */
  error: Error | null;
  /** Whether data is stale (RPC unavailable) */
  isStale: boolean;
  /** Last update timestamp */
  lastUpdate: string | null;
  /** Manually refresh data */
  refetch: () => void;
}

// ============================================================================
// Hook: useSystemStatus
// ============================================================================

/**
 * Hook for real-time system status with WebSocket integration.
 * Automatically falls back to REST polling if WebSocket is unavailable.
 *
 * @example
 * ```tsx
 * const { metrics, isStale, isLoading } = useSystemStatus();
 *
 * return (
 *   <div>
 *     <p>CPU: {metrics?.cpu?.usagePercent ?? 0}%</p>
 *     {isStale && <span className="text-yellow-500">Stale data</span>}
 *   </div>
 * );
 * ```
 */
export function useSystemStatus(
  options: UseSystemStatusOptions = {},
): UseSystemStatusReturn {
  const { pollInterval = 30000, enableRealtime = true } = options;

  // Get real-time metrics from store (updated by WebSocket)
  const realtimeMetrics = useAppStore(selectCurrentMetrics);
  const wsConnected = useAppStore((state) => state.wsConnected);
  const lastMessage = useAppStore((state) => state.lastMessage);

  // REST fallback query
  const {
    data: restMetrics,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.system.metrics(),
    queryFn: async () => {
      const response = await api.system.getMetrics();
      return response.data;
    },
    // Only poll if WebSocket is disconnected
    refetchInterval: !wsConnected && enableRealtime ? pollInterval : false,
    // Use WebSocket data if available
    enabled: !wsConnected || !enableRealtime,
  });

  // Use realtime metrics if available, otherwise fall back to REST
  const metrics =
    enableRealtime && wsConnected ? realtimeMetrics : (restMetrics ?? null);

  // Extract stale status from last WebSocket message
  const isStale =
    lastMessage?.type === "system.status"
      ? ((lastMessage.data as SystemStatusData)?.stale ?? false)
      : false;

  const lastUpdate =
    lastMessage?.type === "system.status"
      ? ((lastMessage.data as SystemStatusData)?.last_update ??
        lastMessage.timestamp)
      : null;

  // Extract status data from last message
  const status =
    lastMessage?.type === "system.status"
      ? (lastMessage.data as SystemStatusData)
      : null;

  return {
    metrics,
    status,
    isLoading,
    error: error as Error | null,
    isStale,
    lastUpdate,
    refetch,
  };
}

// ============================================================================
// Hook: useSystemHealth
// ============================================================================

interface SystemHealth {
  overall: "healthy" | "degraded" | "critical" | "unknown";
  cpu: "healthy" | "warning" | "critical";
  memory: "healthy" | "warning" | "critical";
  storage: "healthy" | "warning" | "critical";
  network: "healthy" | "warning" | "critical";
}

/**
 * Hook for system health status with automatic severity calculation.
 *
 * @example
 * ```tsx
 * const { health, isHealthy } = useSystemHealth();
 *
 * return (
 *   <Badge variant={isHealthy ? "success" : "danger"}>
 *     {health.overall}
 *   </Badge>
 * );
 * ```
 */
export function useSystemHealth() {
  const { metrics, isStale } = useSystemStatus();

  const calculateHealth = useCallback((): SystemHealth => {
    if (!metrics) {
      return {
        overall: "unknown",
        cpu: "healthy",
        memory: "healthy",
        storage: "healthy",
        network: "healthy",
      };
    }

    const cpuUsage = metrics.cpu?.usagePercent ?? metrics.cpu?.usage ?? 0;
    const memoryUsage =
      metrics.memory?.usedBytes && metrics.memory?.totalBytes
        ? (metrics.memory.usedBytes / metrics.memory.totalBytes) * 100
        : 0;

    const cpuHealth =
      cpuUsage > 90 ? "critical" : cpuUsage > 75 ? "warning" : "healthy";
    const memoryHealth =
      memoryUsage > 90 ? "critical" : memoryUsage > 80 ? "warning" : "healthy";

    // Calculate overall health
    const healthScores = [cpuHealth, memoryHealth];
    const hasCritical = healthScores.includes("critical");
    const hasWarning = healthScores.includes("warning");

    const overall = hasCritical
      ? "critical"
      : hasWarning
        ? "degraded"
        : "healthy";

    return {
      overall,
      cpu: cpuHealth,
      memory: memoryHealth,
      storage: "healthy", // TODO: Implement storage health
      network: "healthy", // TODO: Implement network health
    };
  }, [metrics]);

  const health = calculateHealth();
  const isHealthy = health.overall === "healthy";

  return {
    health,
    isHealthy,
    isStale,
  };
}

// ============================================================================
// Hook: useSystemUptime
// ============================================================================

/**
 * Hook for formatted system uptime.
 *
 * @example
 * ```tsx
 * const { uptime, formatted } = useSystemUptime();
 * // formatted = "5d 12h 30m"
 * ```
 */
export function useSystemUptime() {
  const { status } = useSystemStatus();

  const formatUptime = useCallback((seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    const parts: string[] = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);

    return parts.join(" ") || "0m";
  }, []);

  const uptime = status?.uptime ?? 0;
  const formatted = formatUptime(uptime);

  return {
    uptime,
    formatted,
    days: Math.floor(uptime / 86400),
    hours: Math.floor((uptime % 86400) / 3600),
    minutes: Math.floor((uptime % 3600) / 60),
  };
}

// ============================================================================
// Hook: useCpuMetrics
// ============================================================================

/**
 * Hook for CPU-specific metrics.
 *
 * @example
 * ```tsx
 * const { usage, loadAverage, isHigh } = useCpuMetrics();
 * ```
 */
export function useCpuMetrics() {
  const { status, metrics, isStale } = useSystemStatus();

  const usage = status?.cpu_usage ?? metrics?.cpu?.usagePercent ?? 0;
  const loadAverage = status?.load_average ?? [0, 0, 0];
  const coreCount = metrics?.cpu?.coreCount ?? 1;

  const isHigh = usage > 75;
  const isCritical = usage > 90;

  return {
    usage,
    loadAverage,
    coreCount,
    isHigh,
    isCritical,
    isStale,
  };
}

// ============================================================================
// Hook: useMemoryMetrics
// ============================================================================

/**
 * Hook for memory-specific metrics.
 *
 * @example
 * ```tsx
 * const { used, total, percentage, isHigh } = useMemoryMetrics();
 * ```
 */
export function useMemoryMetrics() {
  const { status, metrics, isStale } = useSystemStatus();

  const used = status?.memory_used ?? metrics?.memory?.usedBytes ?? 0;
  const total = status?.memory_total ?? metrics?.memory?.totalBytes ?? 1;
  const percentage =
    status?.memory_pct ?? (total > 0 ? (used / total) * 100 : 0);

  const isHigh = percentage > 80;
  const isCritical = percentage > 90;

  // Format bytes to human readable
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  return {
    used,
    total,
    percentage,
    usedFormatted: formatBytes(used),
    totalFormatted: formatBytes(total),
    isHigh,
    isCritical,
    isStale,
  };
}

export default useSystemStatus;
