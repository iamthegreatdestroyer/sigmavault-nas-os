/**
 * SigmaVault NAS OS - Query Hooks
 * @module hooks/useQueries
 *
 * React Query hooks for data fetching with automatic caching and refetching.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, queryKeys } from "@/api/client";
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
} from "@/types";

// ============================================================================
// Agent Hooks
// ============================================================================

export function useAgents() {
  return useQuery({
    queryKey: queryKeys.agents.list(),
    queryFn: async () => {
      const response = await api.agents.list();
      return response.data;
    },
  });
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: queryKeys.agents.detail(id),
    queryFn: async () => {
      const response = await api.agents.get(id);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useAgentSwarmStatus() {
  return useQuery({
    queryKey: queryKeys.agents.swarm(),
    queryFn: async () => {
      const response = await api.agents.getSwarmStatus();
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}

export function useActivateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.agents.activate(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list() });
    },
  });
}

export function useDeactivateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.agents.deactivate(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list() });
    },
  });
}

// ============================================================================
// Storage Hooks
// ============================================================================

export function useStoragePools() {
  return useQuery({
    queryKey: queryKeys.storage.pools(),
    queryFn: async () => {
      const response = await api.storage.listPools();
      return response.data;
    },
  });
}

export function useStoragePool(id: string) {
  return useQuery({
    queryKey: queryKeys.storage.pool(id),
    queryFn: async () => {
      const response = await api.storage.getPool(id);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useStorageVolumes() {
  return useQuery({
    queryKey: queryKeys.storage.volumes(),
    queryFn: async () => {
      const response = await api.storage.listVolumes();
      return response.data;
    },
  });
}

export function useStorageVolume(id: string) {
  return useQuery({
    queryKey: queryKeys.storage.volume(id),
    queryFn: async () => {
      const response = await api.storage.getVolume(id);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useStorageDisks() {
  return useQuery({
    queryKey: queryKeys.storage.disks(),
    queryFn: async () => {
      const response = await api.storage.listDisks();
      return response.data;
    },
  });
}

export function useStorageDisk(id: string) {
  return useQuery({
    queryKey: queryKeys.storage.disk(id),
    queryFn: async () => {
      const response = await api.storage.getDisk(id);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreatePool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Parameters<typeof api.storage.createPool>[0]) =>
      api.storage.createPool(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.storage.pools() });
    },
  });
}

export function useDeletePool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.storage.deletePool(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.storage.pools() });
    },
  });
}

export function useCreateVolume() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Parameters<typeof api.storage.createVolume>[0]) =>
      api.storage.createVolume(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.storage.volumes() });
    },
  });
}

export function useDeleteVolume() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.storage.deleteVolume(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.storage.volumes() });
    },
  });
}

// ============================================================================
// Compression Hooks
// ============================================================================

export function useCompressionStats() {
  return useQuery({
    queryKey: queryKeys.compression.stats(),
    queryFn: async () => {
      const response = await api.compression.getStats();
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

export function useCompressionJobs() {
  return useQuery({
    queryKey: queryKeys.compression.jobs(),
    queryFn: async () => {
      const response = await api.compression.listJobs();
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds for active jobs
  });
}

export function useCompressionJob(id: string) {
  return useQuery({
    queryKey: queryKeys.compression.job(id),
    queryFn: async () => {
      const response = await api.compression.getJob(id);
      return response.data;
    },
    enabled: !!id,
    refetchInterval: 2000, // Refresh every 2 seconds for active job
  });
}

export function useCreateCompressionJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Parameters<typeof api.compression.createJob>[0]) =>
      api.compression.createJob(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.compression.jobs() });
    },
  });
}

export function useCancelCompressionJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.compression.cancelJob(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.compression.jobs() });
    },
  });
}

// ============================================================================
// Network Hooks
// ============================================================================

export function useNetworkInterfaces() {
  return useQuery({
    queryKey: queryKeys.network.interfaces(),
    queryFn: async () => {
      const response = await api.network.listInterfaces();
      return response.data;
    },
  });
}

export function useNetworkInterface(id: string) {
  return useQuery({
    queryKey: queryKeys.network.interface(id),
    queryFn: async () => {
      const response = await api.network.getInterface(id);
      return response.data;
    },
    enabled: !!id,
  });
}

export function usePhantomMesh() {
  return useQuery({
    queryKey: queryKeys.network.phantomMesh(),
    queryFn: async () => {
      const response = await api.network.getPhantomMesh();
      return response.data;
    },
    refetchInterval: 10000,
  });
}

export function usePhantomMeshPeers() {
  return useQuery({
    queryKey: queryKeys.network.peers(),
    queryFn: async () => {
      const response = await api.network.listPeers();
      return response.data;
    },
  });
}

export function useAddPhantomMeshPeer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Parameters<typeof api.network.addPeer>[0]) =>
      api.network.addPeer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.network.peers() });
      queryClient.invalidateQueries({
        queryKey: queryKeys.network.phantomMesh(),
      });
    },
  });
}

export function useRemovePhantomMeshPeer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.network.removePeer(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.network.peers() });
      queryClient.invalidateQueries({
        queryKey: queryKeys.network.phantomMesh(),
      });
    },
  });
}

export function useEnablePhantomMesh() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.network.enableMesh(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.network.phantomMesh(),
      });
    },
  });
}

export function useDisablePhantomMesh() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.network.disableMesh(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.network.phantomMesh(),
      });
    },
  });
}

// ============================================================================
// Security Hooks
// ============================================================================

export function useEncryptionStatus() {
  return useQuery({
    queryKey: queryKeys.security.encryption(),
    queryFn: async () => {
      const response = await api.security.getEncryptionStatus();
      return response.data;
    },
  });
}

export function useSecurityAudit(
  params?: Parameters<typeof api.security.getAuditLog>[0]
) {
  return useQuery({
    queryKey: [...queryKeys.security.audit(), params],
    queryFn: async () => {
      const response = await api.security.getAuditLog(params);
      return response;
    },
  });
}

export function useRotateEncryptionKeys() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.security.rotateKeys(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.security.encryption(),
      });
    },
  });
}

// ============================================================================
// System Hooks
// ============================================================================

export function useSystemMetrics() {
  return useQuery({
    queryKey: queryKeys.system.metrics(),
    queryFn: async () => {
      const response = await api.system.getMetrics();
      return response.data;
    },
    refetchInterval: 2000, // Refresh every 2 seconds for real-time metrics
  });
}

export function useSystemInfo() {
  return useQuery({
    queryKey: queryKeys.system.info(),
    queryFn: async () => {
      const response = await api.system.getInfo();
      return response.data;
    },
    staleTime: 60000, // System info rarely changes
  });
}

export function useSystemHealth() {
  return useQuery({
    queryKey: queryKeys.system.health(),
    queryFn: async () => {
      const response = await api.system.getHealth();
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

// ============================================================================
// Auth Hooks
// ============================================================================

export function useCurrentUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const response = await api.auth.me();
      return response.data;
    },
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: { username: string; password: string }) =>
      api.auth.login(credentials),
    onSuccess: (response) => {
      if (response.data?.token) {
        localStorage.setItem("sigmavault_token", response.data.token);
      }
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.auth.logout(),
    onSuccess: () => {
      localStorage.removeItem("sigmavault_token");
      queryClient.clear();
    },
  });
}
