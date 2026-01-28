/**
 * SigmaVault NAS OS - Hooks Index
 * @module hooks
 *
 * Central export for all React hooks.
 * Provides real-time data integration with WebSocket and REST fallback.
 */

// ============================================================================
// Core Hooks - Real-time WebSocket Integration
// ============================================================================

export { default as useWebSocket } from "./useWebSocket";

// ============================================================================
// System Hooks (Real-time with WebSocket)
// ============================================================================

export {
  useSystemStatus,
  useSystemHealth,
  useSystemUptime,
  useCpuMetrics,
  useMemoryMetrics,
} from "./useSystem";

// Default export alias
export { default as useSystemStatusDefault } from "./useSystem";

// ============================================================================
// Storage Hooks (Real-time with WebSocket)
// ============================================================================

export {
  useStoragePools,
  useStoragePool,
  useVolumes,
  useStorageDevices,
  useStorageAlerts,
  useStorageCapacity,
} from "./useStorage";

// Default export alias
export { default as useStoragePoolsDefault } from "./useStorage";

// ============================================================================
// Agent Hooks (Real-time with WebSocket)
// ============================================================================

export {
  useAgents,
  useAgent,
  useAgentTasks,
  useSwarmOrchestrator,
  useAgentMetrics,
} from "./useAgents";

// Default export alias
export { default as useAgentsDefault } from "./useAgents";

// ============================================================================
// Query Hooks - REST API with React Query
// ============================================================================

export {
  // Agents
  useAgents as useAgentsQuery,
  useAgent as useAgentQuery,
  useAgentSwarmStatus,
  useActivateAgent,
  useDeactivateAgent,

  // Storage
  useStoragePools as useStoragePoolsQuery,
  useStoragePool as useStoragePoolQuery,
  useStorageVolumes,
  useStorageVolume,
  useStorageDisks,
  useStorageDisk,
  useCreatePool,
  useDeletePool,
  useCreateVolume,
  useDeleteVolume,

  // Compression
  useCompressionStats,
  useCompressionJobs,
  useCompressionJob,
  useCreateCompressionJob,
  useCancelCompressionJob,

  // Network
  useNetworkInterfaces,
  useNetworkInterface,
  usePhantomMesh,
  usePhantomMeshPeers,
  useAddPhantomMeshPeer,
  useRemovePhantomMeshPeer,
  useEnablePhantomMesh,
  useDisablePhantomMesh,

  // Security
  useEncryptionStatus,
  useSecurityAudit,

  // System
  useSystemMetrics,
  useSystemInfo,
  useSystemHealth as useSystemHealthQuery,
} from "./useQueries";

// ============================================================================
// Re-export types
// ============================================================================

export type {
  SystemMetrics,
  Agent,
  AgentMetrics,
  AgentSwarmStatus,
  StoragePool,
  StorageVolume,
  StorageDisk,
} from "@/types";
