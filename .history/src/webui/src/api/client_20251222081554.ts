/**
 * SigmaVault NAS OS - API Client
 * @module api/client
 *
 * HTTP API client with React Query integration.
 * Provides typed API methods for all SigmaVault endpoints.
 */

import { QueryClient } from "@tanstack/react-query";
import type {
  Agent,
  StoragePool,
  StorageVolume,
  StorageDisk,
  PhantomMeshNetwork,
  PhantomMeshPeer,
  NetworkInterface,
  SystemMetrics,
  CompressionStats,
  CompressionJob,
  EncryptionStatus,
  SecurityAuditEvent,
  ApiResponse,
  PaginatedApiResponse,
} from "@/types";

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

// ============================================================================
// Query Client
// ============================================================================

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30 seconds
      gcTime: 5 * 60_000, // 5 minutes (formerly cacheTime)
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
    },
  },
});

// ============================================================================
// Query Keys Factory
// ============================================================================

export const queryKeys = {
  // Agents
  agents: {
    all: ["agents"] as const,
    list: () => [...queryKeys.agents.all, "list"] as const,
    detail: (id: string) => [...queryKeys.agents.all, "detail", id] as const,
    swarm: () => [...queryKeys.agents.all, "swarm"] as const,
  },

  // Storage
  storage: {
    all: ["storage"] as const,
    pools: () => [...queryKeys.storage.all, "pools"] as const,
    pool: (id: string) => [...queryKeys.storage.all, "pool", id] as const,
    volumes: () => [...queryKeys.storage.all, "volumes"] as const,
    volume: (id: string) => [...queryKeys.storage.all, "volume", id] as const,
    disks: () => [...queryKeys.storage.all, "disks"] as const,
    disk: (id: string) => [...queryKeys.storage.all, "disk", id] as const,
  },

  // Compression
  compression: {
    all: ["compression"] as const,
    stats: () => [...queryKeys.compression.all, "stats"] as const,
    jobs: () => [...queryKeys.compression.all, "jobs"] as const,
    job: (id: string) => [...queryKeys.compression.all, "job", id] as const,
  },

  // Network
  network: {
    all: ["network"] as const,
    interfaces: () => [...queryKeys.network.all, "interfaces"] as const,
    interface: (id: string) =>
      [...queryKeys.network.all, "interface", id] as const,
    phantomMesh: () => [...queryKeys.network.all, "phantomMesh"] as const,
    peers: () => [...queryKeys.network.all, "peers"] as const,
  },

  // Security
  security: {
    all: ["security"] as const,
    encryption: () => [...queryKeys.security.all, "encryption"] as const,
    audit: () => [...queryKeys.security.all, "audit"] as const,
  },

  // System
  system: {
    all: ["system"] as const,
    metrics: () => [...queryKeys.system.all, "metrics"] as const,
    info: () => [...queryKeys.system.all, "info"] as const,
    health: () => [...queryKeys.system.all, "health"] as const,
  },
} as const;

// ============================================================================
// HTTP Client
// ============================================================================

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  // Add auth token if available
  const token = localStorage.getItem("sigmavault_token");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = { message: response.statusText };
    }

    throw new ApiError(
      errorData.message || "Request failed",
      response.status,
      errorData.code,
      errorData.details
    );
  }

  // Handle empty responses
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ============================================================================
// API Methods
// ============================================================================

export const api = {
  // --------------------------------------------------------------------------
  // Agents
  // --------------------------------------------------------------------------
  agents: {
    list: () => request<ApiResponse<Agent[]>>("/agents"),

    get: (id: string) => request<ApiResponse<Agent>>(`/agents/${id}`),

    activate: (id: string) =>
      request<ApiResponse<Agent>>(`/agents/${id}/activate`, { method: "POST" }),

    deactivate: (id: string) =>
      request<ApiResponse<Agent>>(`/agents/${id}/deactivate`, {
        method: "POST",
      }),

    assignTask: (
      id: string,
      task: { type: string; priority: number; payload: unknown }
    ) =>
      request<ApiResponse<{ taskId: string }>>(`/agents/${id}/tasks`, {
        method: "POST",
        body: JSON.stringify(task),
      }),

    getSwarmStatus: () =>
      request<
        ApiResponse<{
          totalAgents: number;
          activeAgents: number;
          taskQueue: number;
          memoryUsage: number;
        }>
      >("/agents/swarm/status"),
  },

  // --------------------------------------------------------------------------
  // Storage
  // --------------------------------------------------------------------------
  storage: {
    // Pools
    listPools: () => request<ApiResponse<StoragePool[]>>("/storage/pools"),

    getPool: (id: string) =>
      request<ApiResponse<StoragePool>>(`/storage/pools/${id}`),

    createPool: (data: {
      name: string;
      type: StoragePool["type"];
      disks: string[];
      encrypted?: boolean;
    }) =>
      request<ApiResponse<StoragePool>>("/storage/pools", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    deletePool: (id: string) =>
      request<ApiResponse<void>>(`/storage/pools/${id}`, { method: "DELETE" }),

    // Volumes
    listVolumes: () =>
      request<ApiResponse<StorageVolume[]>>("/storage/volumes"),

    getVolume: (id: string) =>
      request<ApiResponse<StorageVolume>>(`/storage/volumes/${id}`),

    createVolume: (data: {
      name: string;
      poolId: string;
      size: number;
      filesystem: StorageVolume["filesystem"];
      compression?: boolean;
      encryption?: boolean;
    }) =>
      request<ApiResponse<StorageVolume>>("/storage/volumes", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    deleteVolume: (id: string) =>
      request<ApiResponse<void>>(`/storage/volumes/${id}`, {
        method: "DELETE",
      }),

    // Disks
    listDisks: () => request<ApiResponse<StorageDisk[]>>("/storage/disks"),

    getDisk: (id: string) =>
      request<ApiResponse<StorageDisk>>(`/storage/disks/${id}`),

    getSmart: (id: string) =>
      request<ApiResponse<StorageDisk["smart"]>>(`/storage/disks/${id}/smart`),
  },

  // --------------------------------------------------------------------------
  // Compression (EliteSigma-NAS)
  // --------------------------------------------------------------------------
  compression: {
    getStats: () =>
      request<ApiResponse<CompressionStats>>("/compression/stats"),

    listJobs: () => request<ApiResponse<CompressionJob[]>>("/compression/jobs"),

    getJob: (id: string) =>
      request<ApiResponse<CompressionJob>>(`/compression/jobs/${id}`),

    createJob: (data: { volumeId: string; priority?: number }) =>
      request<ApiResponse<CompressionJob>>("/compression/jobs", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    cancelJob: (id: string) =>
      request<ApiResponse<void>>(`/compression/jobs/${id}`, {
        method: "DELETE",
      }),
  },

  // --------------------------------------------------------------------------
  // Network
  // --------------------------------------------------------------------------
  network: {
    listInterfaces: () =>
      request<ApiResponse<NetworkInterface[]>>("/network/interfaces"),

    getInterface: (id: string) =>
      request<ApiResponse<NetworkInterface>>(`/network/interfaces/${id}`),

    updateInterface: (id: string, data: Partial<NetworkInterface>) =>
      request<ApiResponse<NetworkInterface>>(`/network/interfaces/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    // PhantomMesh VPN
    getPhantomMesh: () =>
      request<ApiResponse<PhantomMeshNetwork>>("/network/phantommesh"),

    listPeers: () =>
      request<ApiResponse<PhantomMeshPeer[]>>("/network/phantommesh/peers"),

    addPeer: (data: { name: string; endpoint?: string; publicKey: string }) =>
      request<ApiResponse<PhantomMeshPeer>>("/network/phantommesh/peers", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    removePeer: (id: string) =>
      request<ApiResponse<void>>(`/network/phantommesh/peers/${id}`, {
        method: "DELETE",
      }),

    enableMesh: () =>
      request<ApiResponse<PhantomMeshNetwork>>("/network/phantommesh/enable", {
        method: "POST",
      }),

    disableMesh: () =>
      request<ApiResponse<void>>("/network/phantommesh/disable", {
        method: "POST",
      }),
  },

  // --------------------------------------------------------------------------
  // Security
  // --------------------------------------------------------------------------
  security: {
    getEncryptionStatus: () =>
      request<ApiResponse<EncryptionStatus>>("/security/encryption"),

    rotateKeys: () =>
      request<ApiResponse<{ rotatedAt: string }>>(
        "/security/encryption/rotate",
        { method: "POST" }
      ),

    getAuditLog: (params?: {
      limit?: number;
      offset?: number;
      level?: string;
    }) => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.set("limit", String(params.limit));
      if (params?.offset) searchParams.set("offset", String(params.offset));
      if (params?.level) searchParams.set("level", params.level);

      return request<PaginatedApiResponse<SecurityAuditEvent>>(
        `/security/audit?${searchParams.toString()}`
      );
    },
  },

  // --------------------------------------------------------------------------
  // System
  // --------------------------------------------------------------------------
  system: {
    getMetrics: () => request<ApiResponse<SystemMetrics>>("/system/metrics"),

    getInfo: () =>
      request<
        ApiResponse<{
          hostname: string;
          version: string;
          uptime: number;
          kernel: string;
          arch: string;
        }>
      >("/system/info"),

    getHealth: () =>
      request<
        ApiResponse<{
          status: "healthy" | "degraded" | "unhealthy";
          checks: Array<{
            name: string;
            status: "pass" | "warn" | "fail";
            message?: string;
          }>;
        }>
      >("/system/health"),

    reboot: () =>
      request<ApiResponse<void>>("/system/reboot", { method: "POST" }),

    shutdown: () =>
      request<ApiResponse<void>>("/system/shutdown", { method: "POST" }),
  },

  // --------------------------------------------------------------------------
  // Auth
  // --------------------------------------------------------------------------
  auth: {
    login: (credentials: { username: string; password: string }) =>
      request<ApiResponse<{ token: string; expiresAt: string }>>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify(credentials),
        }
      ),

    logout: () =>
      request<ApiResponse<void>>("/auth/logout", { method: "POST" }),

    refresh: () =>
      request<ApiResponse<{ token: string; expiresAt: string }>>(
        "/auth/refresh",
        {
          method: "POST",
        }
      ),

    me: () =>
      request<
        ApiResponse<{
          id: string;
          username: string;
          role: string;
          permissions: string[];
        }>
      >("/auth/me"),
  },
} as const;

export { ApiError };
export default api;
