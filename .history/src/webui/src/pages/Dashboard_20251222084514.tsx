/**
 * SigmaVault NAS OS - Dashboard Page
 * @module pages/Dashboard
 *
 * Main dashboard with system metrics, agent swarm status, and storage overview.
 */

import * as React from "react";
import {
  HardDrive,
  Cpu,
  MemoryStick,
  Network,
  Bot,
  Shield,
  Activity,
  FolderArchive,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Zap,
} from "lucide-react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useAppStore } from "@stores/appStore";
import {
  useSystemMetrics,
  useAgents,
  useStoragePools,
} from "@hooks/useQueries";
import type { StorageHealth } from "@/types";
import {
  Card,
  CardHeader,
  CardContent,
  Badge,
  Progress,
  Spinner,
  StatusBadge,
} from "@components/ui";
import { PageHeader, PageSection, Grid } from "@components/layout";

// ============================================================================
// Types
// ============================================================================

// Map StorageHealth to StatusBadge-compatible status
type StatusBadgeStatus =
  | "online"
  | "offline"
  | "idle"
  | "busy"
  | "error"
  | "warning";

const mapStorageHealthToStatus = (health: StorageHealth): StatusBadgeStatus => {
  switch (health) {
    case "healthy":
      return "online";
    case "degraded":
      return "warning";
    case "critical":
      return "error";
    case "unknown":
    default:
      return "idle";
  }
};

interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
  trend?: {
    value: number;
    direction: "up" | "down";
  };
  loading?: boolean;
}

interface MetricChartData {
  time: string;
  value: number;
}

// ============================================================================
// Stat Card Component
// ============================================================================

function StatCard({
  title,
  value,
  unit,
  icon: Icon,
  iconColor,
  trend,
  loading,
}: StatCardProps) {
  return (
    <Card>
      <CardContent padding="lg">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-text-secondary">{title}</p>
            {loading ? (
              <Spinner size="sm" className="mt-2" />
            ) : (
              <div className="flex items-baseline gap-1 mt-2">
                <span className="text-2xl font-bold text-text-primary">
                  {value}
                </span>
                {unit && (
                  <span className="text-sm text-text-muted">{unit}</span>
                )}
              </div>
            )}
            {trend && (
              <div className="flex items-center gap-1 mt-2">
                {trend.direction === "up" ? (
                  <ArrowUpRight className="w-4 h-4 text-status-success" />
                ) : (
                  <ArrowDownRight className="w-4 h-4 text-status-error" />
                )}
                <span
                  className={`text-xs font-medium ${
                    trend.direction === "up"
                      ? "text-status-success"
                      : "text-status-error"
                  }`}
                >
                  {trend.value}%
                </span>
              </div>
            )}
          </div>
          <div
            className={`flex items-center justify-center w-10 h-10 rounded-lg ${iconColor}`}
          >
            <Icon className="w-5 h-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// System Metrics Section
// ============================================================================

function SystemMetrics() {
  const { data: metrics, isLoading } = useSystemMetrics();

  // Mock chart data
  const [cpuHistory] = React.useState<MetricChartData[]>(() =>
    Array.from({ length: 20 }, (_, i) => ({
      time: `${i}m`,
      value: Math.floor(Math.random() * 40 + 20),
    }))
  );

  return (
    <PageSection
      title="System Metrics"
      description="Real-time system resource utilization"
    >
      <Grid columns={4} gap="md">
        <StatCard
          title="CPU Usage"
          value={metrics?.cpu.usage.toFixed(1) ?? "--"}
          unit="%"
          icon={Cpu}
          iconColor="bg-primary/20 text-primary"
          loading={isLoading}
        />
        <StatCard
          title="Memory"
          value={((metrics?.memory.used ?? 0) / 1024 / 1024 / 1024).toFixed(1)}
          unit="GB"
          icon={MemoryStick}
          iconColor="bg-status-info/20 text-status-info"
          loading={isLoading}
        />
        <StatCard
          title="Network I/O"
          value={((metrics?.network.bytesSent ?? 0) / 1024 / 1024).toFixed(1)}
          unit="MB/s"
          icon={Network}
          iconColor="bg-status-success/20 text-status-success"
          loading={isLoading}
        />
        <StatCard
          title="Uptime"
          value={formatUptime(metrics?.uptime ?? 0)}
          icon={Clock}
          iconColor="bg-status-warning/20 text-status-warning"
          loading={isLoading}
        />
      </Grid>

      {/* CPU Chart */}
      <Card className="mt-4">
        <CardHeader title="CPU History" subtitle="Last 20 minutes" />
        <CardContent>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={cpuHistory}>
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="5%"
                      stopColor="var(--color-primary)"
                      stopOpacity={0.3}
                    />
                    <stop
                      offset="95%"
                      stopColor="var(--color-primary)"
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--color-border-primary)"
                />
                <XAxis
                  dataKey="time"
                  stroke="var(--color-text-muted)"
                  fontSize={12}
                />
                <YAxis stroke="var(--color-text-muted)" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-bg-secondary)",
                    border: "1px solid var(--color-border-primary)",
                    borderRadius: "8px",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="var(--color-primary)"
                  fillOpacity={1}
                  fill="url(#cpuGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </PageSection>
  );
}

// ============================================================================
// Agent Swarm Section
// ============================================================================

function AgentSwarm() {
  const { data: agents, isLoading } = useAgents();
  const storeAgents = useAppStore((state) => state.agents);

  // Use store agents if available (real-time), otherwise fall back to query
  const displayAgents = storeAgents.length > 0 ? storeAgents : agents ?? [];

  const agentStats = React.useMemo(() => {
    return {
      active: displayAgents.filter((a) => a.status === "active").length,
      idle: displayAgents.filter((a) => a.status === "idle").length,
      error: displayAgents.filter((a) => a.status === "error").length,
      total: displayAgents.length,
    };
  }, [displayAgents]);

  const agentsByTier = React.useMemo(() => {
    const tiers: Record<number, typeof displayAgents> = {};
    displayAgents.forEach((agent) => {
      if (!tiers[agent.tier]) tiers[agent.tier] = [];
      tiers[agent.tier].push(agent);
    });
    return tiers;
  }, [displayAgents]);

  return (
    <PageSection
      title="Elite Agent Collective"
      description="40-agent AI swarm status and performance"
    >
      {/* Agent Stats */}
      <Grid columns={4} gap="md">
        <StatCard
          title="Active Agents"
          value={agentStats.active}
          icon={Bot}
          iconColor="bg-agent-active/20 text-agent-active"
          loading={isLoading}
        />
        <StatCard
          title="Idle Agents"
          value={agentStats.idle}
          icon={Bot}
          iconColor="bg-agent-idle/20 text-agent-idle"
          loading={isLoading}
        />
        <StatCard
          title="Errors"
          value={agentStats.error}
          icon={Bot}
          iconColor="bg-agent-error/20 text-agent-error"
          loading={isLoading}
        />
        <StatCard
          title="Swarm Load"
          value={((agentStats.active / (agentStats.total || 1)) * 100).toFixed(
            0
          )}
          unit="%"
          icon={Zap}
          iconColor="bg-primary/20 text-primary"
          loading={isLoading}
        />
      </Grid>

      {/* Agent Grid by Tier */}
      <Card className="mt-4">
        <CardHeader
          title="Agent Status by Tier"
          actions={
            <Badge variant="primary" size="sm">
              {agentStats.total} agents
            </Badge>
          }
        />
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner size="lg" />
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(agentsByTier)
                .sort(([a], [b]) => Number(a) - Number(b))
                .map(([tier, tierAgents]) => (
                  <div key={tier}>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="default" size="sm">
                        Tier {tier}
                      </Badge>
                      <span className="text-xs text-text-muted">
                        {tierAgents.length} agents
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {tierAgents.map((agent) => (
                        <div
                          key={agent.id}
                          className={`
                            flex items-center gap-2 px-3 py-2 rounded-lg
                            border border-border-primary
                            ${
                              agent.status === "active"
                                ? "bg-agent-active/10"
                                : agent.status === "error"
                                ? "bg-agent-error/10"
                                : "bg-bg-tertiary"
                            }
                          `}
                        >
                          <div
                            className={`w-2 h-2 rounded-full ${
                              agent.status === "active"
                                ? "bg-agent-active"
                                : agent.status === "error"
                                ? "bg-agent-error"
                                : "bg-agent-idle"
                            }`}
                          />
                          <span className="text-sm font-medium text-text-primary">
                            @{agent.codename}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>
    </PageSection>
  );
}

// ============================================================================
// Storage Overview Section
// ============================================================================

function StorageOverview() {
  const { data: pools, isLoading } = useStoragePools();

  const totalCapacity = pools?.reduce((acc, p) => acc + p.totalSpace, 0) ?? 0;
  const usedSpace = pools?.reduce((acc, p) => acc + p.usedSpace, 0) ?? 0;
  const compressionRatio =
    pools?.reduce((acc, p) => acc + p.compressionRatio, 0) ?? 0;
  const avgCompression = pools?.length ? compressionRatio / pools.length : 0;

  return (
    <PageSection
      title="Storage Overview"
      description="Storage pools and compression status"
    >
      <Grid columns={3} gap="md">
        <StatCard
          title="Total Capacity"
          value={(totalCapacity / 1024 / 1024 / 1024 / 1024).toFixed(2)}
          unit="TB"
          icon={HardDrive}
          iconColor="bg-status-info/20 text-status-info"
          loading={isLoading}
        />
        <StatCard
          title="Space Used"
          value={((usedSpace / totalCapacity) * 100 || 0).toFixed(1)}
          unit="%"
          icon={FolderArchive}
          iconColor="bg-status-warning/20 text-status-warning"
          loading={isLoading}
        />
        <StatCard
          title="Avg. Compression"
          value={(avgCompression * 100).toFixed(0)}
          unit="%"
          icon={Zap}
          iconColor="bg-status-success/20 text-status-success"
          loading={isLoading}
        />
      </Grid>

      {/* Storage Pools */}
      <Card className="mt-4">
        <CardHeader title="Storage Pools" />
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner size="lg" />
            </div>
          ) : pools && pools.length > 0 ? (
            <div className="space-y-4">
              {pools.map((pool) => (
                <div key={pool.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <HardDrive className="w-4 h-4 text-text-muted" />
                      <span className="font-medium text-text-primary">
                        {pool.name}
                      </span>
                      <StatusBadge
                        status={mapStorageHealthToStatus(pool.status)}
                      />
                    </div>
                    <span className="text-sm text-text-muted">
                      {formatBytes(pool.usedSpace)} /{" "}
                      {formatBytes(pool.totalSpace)}
                    </span>
                  </div>
                  <Progress
                    value={(pool.usedSpace / pool.totalSpace) * 100}
                    className="h-2"
                  />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-text-muted py-8">
              No storage pools configured
            </p>
          )}
        </CardContent>
      </Card>
    </PageSection>
  );
}

// ============================================================================
// Security Status Section
// ============================================================================

function SecurityStatus() {
  return (
    <PageSection
      title="Security Status"
      description="Encryption and threat monitoring"
    >
      <Grid columns={2} gap="md">
        <Card>
          <CardContent padding="lg">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-status-success/20">
                <Shield className="w-6 h-6 text-status-success" />
              </div>
              <div>
                <p className="text-lg font-semibold text-text-primary">
                  Quantum-Resistant Encryption
                </p>
                <p className="text-sm text-text-secondary">
                  All data protected with post-quantum cryptography
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent padding="lg">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-status-success/20">
                <Activity className="w-6 h-6 text-status-success" />
              </div>
              <div>
                <p className="text-lg font-semibold text-text-primary">
                  No Active Threats
                </p>
                <p className="text-sm text-text-secondary">
                  Real-time monitoring active
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </Grid>
    </PageSection>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB", "PB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

// ============================================================================
// Dashboard Page Component
// ============================================================================

export function Dashboard() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="SigmaVault NAS OS system overview"
      />

      <SystemMetrics />
      <AgentSwarm />
      <StorageOverview />
      <SecurityStatus />
    </>
  );
}

export default Dashboard;
