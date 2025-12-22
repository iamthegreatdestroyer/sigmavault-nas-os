/**
 * SigmaVault NAS OS - Core Type Definitions
 * @module types
 */

// ============================================================================
// Agent System Types
// ============================================================================

export type AgentStatus = 'active' | 'processing' | 'idle' | 'error' | 'offline';
export type AgentTier = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export interface Agent {
  id: string;
  codename: string;
  displayName: string;
  tier: AgentTier;
  status: AgentStatus;
  philosophy: string;
  capabilities: string[];
  currentTask?: string;
  metrics: AgentMetrics;
  lastSeen: string;
}

export interface AgentMetrics {
  tasksCompleted: number;
  successRate: number;
  avgResponseTime: number;
  memoryUsage: number;
  cpuUsage: number;
}

export interface AgentSwarmStatus {
  totalAgents: number;
  activeAgents: number;
  processingAgents: number;
  idleAgents: number;
  errorAgents: number;
  overallHealth: 'healthy' | 'degraded' | 'critical';
}

// ============================================================================
// Storage System Types
// ============================================================================

export type StorageHealth = 'healthy' | 'degraded' | 'critical' | 'unknown';
export type StoragePoolType = 'raid0' | 'raid1' | 'raid5' | 'raid6' | 'raidz' | 'raidz2' | 'raidz3' | 'mirror' | 'stripe';
export type DiskType = 'ssd' | 'nvme' | 'hdd' | 'sas';

export interface StorageDisk {
  id: string;
  model: string;
  serial: string;
  type: DiskType;
  capacityBytes: number;
  usedBytes: number;
  health: StorageHealth;
  temperature: number;
  smartStatus: SmartStatus;
  path: string;
}

export interface SmartStatus {
  passed: boolean;
  powerOnHours: number;
  reallocatedSectors: number;
  currentPendingSectors: number;
  uncorrectableErrors: number;
  rawReadErrorRate: number;
}

export interface StoragePool {
  id: string;
  name: string;
  type: StoragePoolType;
  disks: StorageDisk[];
  health: StorageHealth;
  capacityBytes: number;
  usedBytes: number;
  availableBytes: number;
  compressionRatio: number;
  deduplicationRatio: number;
  aiCompressionEnabled: boolean;
  quantumEncryptionEnabled: boolean;
}

export interface StorageVolume {
  id: string;
  name: string;
  poolId: string;
  mountPoint: string;
  capacityBytes: number;
  usedBytes: number;
  quotaBytes?: number;
  compressionEnabled: boolean;
  encryptionEnabled: boolean;
  snapshotCount: number;
}

export interface StorageSnapshot {
  id: string;
  volumeId: string;
  name: string;
  createdAt: string;
  sizeBytes: number;
  isAutomatic: boolean;
}

// ============================================================================
// Compression System Types (EliteSigma-NAS)
// ============================================================================

export interface CompressionStats {
  totalBytesIn: number;
  totalBytesOut: number;
  overallRatio: number;
  aiModelVersion: string;
  filesProcessed: number;
  averageCompressionTime: number;
  targetRatio: number; // 90%+ target
}

export interface CompressionJob {
  id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  filePath: string;
  originalSize: number;
  compressedSize: number;
  compressionRatio: number;
  algorithm: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

// ============================================================================
// Network System Types (PhantomMesh-VPN)
// ============================================================================

export type VPNStatus = 'connected' | 'connecting' | 'disconnected' | 'error';
export type NetworkInterfaceType = 'ethernet' | 'bond' | 'vlan' | 'bridge' | 'wireguard' | 'phantommesh';

export interface NetworkInterface {
  id: string;
  name: string;
  type: NetworkInterfaceType;
  macAddress: string;
  ipAddresses: string[];
  isUp: boolean;
  speed: number; // Mbps
  mtu: number;
  rxBytes: number;
  txBytes: number;
}

export interface PhantomMeshPeer {
  id: string;
  publicKey: string;
  endpoint?: string;
  allowedIps: string[];
  lastHandshake?: string;
  rxBytes: number;
  txBytes: number;
  latency?: number;
  status: VPNStatus;
}

export interface PhantomMeshNetwork {
  id: string;
  name: string;
  enabled: boolean;
  listenPort: number;
  publicKey: string;
  peers: PhantomMeshPeer[];
  federationEnabled: boolean;
  quantumResistant: boolean;
}

// ============================================================================
// Security Types (Quantum-Resistant)
// ============================================================================

export type EncryptionAlgorithm = 'aes-256-gcm' | 'chacha20-poly1305' | 'kyber-1024' | 'dilithium-5';

export interface EncryptionStatus {
  atRestEnabled: boolean;
  inTransitEnabled: boolean;
  algorithm: EncryptionAlgorithm;
  keyRotationInterval: number; // hours
  lastKeyRotation: string;
  quantumResistant: boolean;
}

export interface SecurityAuditEvent {
  id: string;
  timestamp: string;
  eventType: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  source: string;
  message: string;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// System Metrics Types
// ============================================================================

export interface SystemMetrics {
  timestamp: string;
  cpu: CpuMetrics;
  memory: MemoryMetrics;
  network: NetworkMetrics;
  storage: StorageMetrics;
}

export interface CpuMetrics {
  usagePercent: number;
  coreCount: number;
  frequency: number;
  temperature: number;
  loadAverage: [number, number, number];
}

export interface MemoryMetrics {
  totalBytes: number;
  usedBytes: number;
  availableBytes: number;
  cachedBytes: number;
  swapTotalBytes: number;
  swapUsedBytes: number;
}

export interface NetworkMetrics {
  rxBytesPerSec: number;
  txBytesPerSec: number;
  connections: number;
  errors: number;
}

export interface StorageMetrics {
  readBytesPerSec: number;
  writeBytesPerSec: number;
  iops: number;
  latencyMs: number;
}

// ============================================================================
// WebSocket Message Types
// ============================================================================

export type WebSocketMessageType = 
  | 'metrics_update'
  | 'agent_status'
  | 'storage_event'
  | 'compression_progress'
  | 'network_event'
  | 'security_alert'
  | 'notification';

export interface WebSocketMessage<T = unknown> {
  type: WebSocketMessageType;
  timestamp: string;
  payload: T;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actionUrl?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  meta?: {
    page?: number;
    pageSize?: number;
    total?: number;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// RPC Types (JSON-RPC 2.0)
// ============================================================================

export interface JsonRpcRequest {
  jsonrpc: '2.0';
  method: string;
  params?: unknown[];
  id: string | number;
}

export interface JsonRpcResponse<T = unknown> {
  jsonrpc: '2.0';
  result?: T;
  error?: JsonRpcError;
  id: string | number;
}

export interface JsonRpcError {
  code: number;
  message: string;
  data?: unknown;
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface DashboardStats {
  systemHealth: 'healthy' | 'degraded' | 'critical';
  uptime: number; // seconds
  agentSwarm: AgentSwarmStatus;
  storage: {
    totalCapacity: number;
    usedCapacity: number;
    compressionSavings: number;
    poolCount: number;
    volumeCount: number;
  };
  network: {
    activeConnections: number;
    vpnPeers: number;
    bandwidth: {
      rx: number;
      tx: number;
    };
  };
  recentNotifications: Notification[];
}
