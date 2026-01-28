/**
 * SigmaVault NAS OS - Storage Hooks
 * @module hooks/useStorage
 *
 * React hooks for storage management with real-time WebSocket updates.
 * Handles pools, volumes, SMART data, and storage events.
 *
 * @see docs/WEBSOCKET_PROTOCOL.md for event type specifications
 */

import { useEffect, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "@/stores/appStore";
import { api, queryKeys } from "@/api/client";

// ============================================================================
// Types
// ============================================================================

interface StorageUpdateData {
  event_type:
    | "pool_status"
    | "volume_change"
    | "disk_health"
    | "capacity_warning";
  pool_id?: string;
  volume_id?: string;
  device_id?: string;
  status?: string;
  health?: string;
  usage_percent?: number;
  message?: string;
  timestamp: string;
}

interface StorageStats {
  totalCapacity: number;
  usedCapacity: number;
  freeCapacity: number;
  usagePercent: number;
  poolCount: number;
  volumeCount: number;
  healthyPools: number;
  degradedPools: number;
}

interface UseStoragePoolsOptions {
  /** Enable real-time WebSocket updates (default: true) */
  enableRealtime?: boolean;
  /** Poll interval for REST fallback (default: 60000ms) */
  pollInterval?: number;
}

// ============================================================================
// Hook: useStoragePools
// ============================================================================

/**
 * Hook for storage pool management with real-time updates.
 *
 * @example
 * ```tsx
 * const { pools, isLoading, stats } = useStoragePools();
 *
 * return (
 *   <div>
 *     <p>Total: {stats.totalCapacity} bytes</p>
 *     {pools.map(pool => (
 *       <PoolCard key={pool.id} pool={pool} />
 *     ))}
 *   </div>
 * );
 * ```
 */
export function useStoragePools(options: UseStoragePoolsOptions = {}) {
  const { enableRealtime = true, pollInterval = 60000 } = options;

  const queryClient = useQueryClient();
  const wsConnected = useAppStore((state) => state.wsConnected);
  const lastMessage = useAppStore((state) => state.lastMessage);

  // Fetch pools from API
  const {
    data: pools = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.storage.pools(),
    queryFn: async () => {
      const response = await api.storage.getPools();
      return response.data;
    },
    refetchInterval: !wsConnected && enableRealtime ? pollInterval : false,
  });

  // Handle real-time storage updates
  useEffect(() => {
    if (!enableRealtime || !lastMessage) return;

    if (lastMessage.type === "storage.update") {
      const update = lastMessage.data as StorageUpdateData;

      // Refresh pools if this is a pool-related update
      if (
        update.event_type === "pool_status" ||
        update.event_type === "capacity_warning"
      ) {
        queryClient.invalidateQueries({ queryKey: queryKeys.storage.pools() });
      }
    }
  }, [lastMessage, enableRealtime, queryClient]);

  // Calculate storage statistics
  const stats = useMemo((): StorageStats => {
    const totalCapacity = pools.reduce(
      (sum, p) => sum + (p.capacityBytes ?? 0),
      0,
    );
    const usedCapacity = pools.reduce((sum, p) => sum + (p.usedBytes ?? 0), 0);
    const freeCapacity = totalCapacity - usedCapacity;
    const usagePercent =
      totalCapacity > 0 ? (usedCapacity / totalCapacity) * 100 : 0;

    const healthyPools = pools.filter(
      (p) => p.health === "healthy" || p.status === "healthy",
    ).length;
    const degradedPools = pools.filter(
      (p) => p.health === "degraded" || p.status === "degraded",
    ).length;

    return {
      totalCapacity,
      usedCapacity,
      freeCapacity,
      usagePercent,
      poolCount: pools.length,
      volumeCount: pools.reduce((sum, p) => sum + (p.disks?.length ?? 0), 0),
      healthyPools,
      degradedPools,
    };
  }, [pools]);

  return {
    pools,
    stats,
    isLoading,
    error: error as Error | null,
    refetch,
    isRealtime: wsConnected && enableRealtime,
  };
}

// ============================================================================
// Hook: useStoragePool
// ============================================================================

/**
 * Hook for a single storage pool with real-time updates.
 *
 * @example
 * ```tsx
 * const { pool, volumes, isHealthy } = useStoragePool("pool-1");
 * ```
 */
export function useStoragePool(poolId: string) {
  const { pools, isLoading, error } = useStoragePools();

  const pool = useMemo(
    () => pools.find((p) => p.id === poolId) ?? null,
    [pools, poolId],
  );

  const disks = pool?.disks ?? [];
  const isHealthy = pool?.health === "healthy" || pool?.status === "healthy";
  const isDegraded = pool?.health === "degraded" || pool?.status === "degraded";

  return {
    pool,
    disks,
    isHealthy,
    isDegraded,
    isLoading,
    error,
  };
}

// ============================================================================
// Hook: useVolumes
// ============================================================================

/**
 * Hook for volume management across all pools.
 *
 * @example
 * ```tsx
 * const { volumes, createVolume, deleteVolume } = useVolumes();
 * ```
 */
export function useVolumes() {
  const queryClient = useQueryClient();

  // Fetch volumes from API
  const { data: volumes = [], isLoading } = useQuery({
    queryKey: queryKeys.storage.volumes(),
    queryFn: async () => {
      const response = await api.storage.listVolumes();
      return response.data;
    },
  });

  // Create volume mutation
  const createVolume = useMutation({
    mutationFn: async (params: {
      poolId: string;
      name: string;
      size: number;
    }) => {
      const response = await api.storage.createVolume(params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.storage.pools() });
    },
  });

  // Delete volume mutation
  const deleteVolume = useMutation({
    mutationFn: async (params: { poolId: string; volumeId: string }) => {
      await api.storage.deleteVolume(params.poolId, params.volumeId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.storage.pools() });
    },
  });

  return {
    volumes,
    isLoading,
    createVolume: createVolume.mutate,
    deleteVolume: deleteVolume.mutate,
    isCreating: createVolume.isPending,
    isDeleting: deleteVolume.isPending,
  };
}

// ============================================================================
// Hook: useStorageDevices
// ============================================================================

/**
 * Hook for storage device (disk) management with SMART data.
 *
 * @example
 * ```tsx
 * const { devices, healthyCount, warningCount } = useStorageDevices();
 * ```
 */
export function useStorageDevices() {
  const queryClient = useQueryClient();
  const wsConnected = useAppStore((state) => state.wsConnected);
  const lastMessage = useAppStore((state) => state.lastMessage);

  const {
    data: devices = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.storage.devices(),
    queryFn: async () => {
      const response = await api.storage.getDevices();
      return response.data;
    },
    refetchInterval: !wsConnected ? 120000 : false, // 2 min fallback
  });

  // Handle disk health updates
  useEffect(() => {
    if (!lastMessage || lastMessage.type !== "storage.update") return;

    const update = lastMessage.data as StorageUpdateData;
    if (update.event_type === "disk_health") {
      queryClient.invalidateQueries({ queryKey: queryKeys.storage.devices() });
    }
  }, [lastMessage, queryClient]);

  // Count devices by health status
  const healthyCount = devices.filter(
    (d) => d.health === "healthy" && d.smartStatus?.passed === true,
  ).length;

  const warningCount = devices.filter(
    (d) => d.health === "degraded" || (d.smartStatus && !d.smartStatus.passed),
  ).length;

  const failingCount = devices.filter((d) => d.health === "critical").length;

  return {
    devices,
    healthyCount,
    warningCount,
    failingCount,
    totalCount: devices.length,
    isLoading,
    error: error as Error | null,
    refetch,
  };
}

// ============================================================================
// Hook: useStorageAlerts
// ============================================================================

interface StorageAlert {
  id: string;
  type: "capacity" | "health" | "performance";
  severity: "info" | "warning" | "critical";
  poolId?: string;
  deviceId?: string;
  message: string;
  timestamp: string;
}

/**
 * Hook for storage-related alerts and warnings.
 * Monitors capacity thresholds and device health.
 *
 * @example
 * ```tsx
 * const { alerts, criticalCount, hasAlerts } = useStorageAlerts();
 * ```
 */
export function useStorageAlerts() {
  const { pools, stats } = useStoragePools();
  const { failingCount } = useStorageDevices();

  const alerts = useMemo((): StorageAlert[] => {
    const result: StorageAlert[] = [];
    const now = new Date().toISOString();

    // Capacity alerts
    if (stats.usagePercent > 90) {
      result.push({
        id: "capacity-critical",
        type: "capacity",
        severity: "critical",
        message: `Storage capacity critical: ${stats.usagePercent.toFixed(1)}% used`,
        timestamp: now,
      });
    } else if (stats.usagePercent > 80) {
      result.push({
        id: "capacity-warning",
        type: "capacity",
        severity: "warning",
        message: `Storage capacity warning: ${stats.usagePercent.toFixed(1)}% used`,
        timestamp: now,
      });
    }

    // Pool health alerts
    pools.forEach((pool) => {
      if (pool.health === "degraded" || pool.status === "degraded") {
        result.push({
          id: `pool-degraded-${pool.id}`,
          type: "health",
          severity: "warning",
          poolId: pool.id,
          message: `Pool "${pool.name}" is degraded`,
          timestamp: now,
        });
      }
    });

    // Device health alerts
    if (failingCount > 0) {
      result.push({
        id: "devices-failing",
        type: "health",
        severity: "critical",
        message: `${failingCount} storage device(s) failing`,
        timestamp: now,
      });
    }

    return result;
  }, [pools, stats, failingCount]);

  const criticalCount = alerts.filter((a) => a.severity === "critical").length;
  const warningCount = alerts.filter((a) => a.severity === "warning").length;
  const hasAlerts = alerts.length > 0;

  return {
    alerts,
    criticalCount,
    warningCount,
    hasAlerts,
    hasCritical: criticalCount > 0,
  };
}

// ============================================================================
// Hook: useStorageCapacity
// ============================================================================

/**
 * Hook for storage capacity with formatted values.
 *
 * @example
 * ```tsx
 * const { total, used, free, percentage } = useStorageCapacity();
 * // total = "10.5 TB", used = "5.2 TB", free = "5.3 TB", percentage = 49.5
 * ```
 */
export function useStorageCapacity() {
  const { stats } = useStoragePools();

  const formatBytes = useCallback((bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB", "PB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  }, []);

  return {
    total: formatBytes(stats.totalCapacity),
    used: formatBytes(stats.usedCapacity),
    free: formatBytes(stats.freeCapacity),
    percentage: stats.usagePercent,
    totalBytes: stats.totalCapacity,
    usedBytes: stats.usedCapacity,
    freeBytes: stats.freeCapacity,
    isHigh: stats.usagePercent > 80,
    isCritical: stats.usagePercent > 90,
  };
}

export default useStoragePools;
