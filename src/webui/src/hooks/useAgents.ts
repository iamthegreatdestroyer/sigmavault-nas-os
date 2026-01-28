/**
 * SigmaVault NAS OS - Agent Hooks
 * @module hooks/useAgents
 *
 * React hooks for AI agent management with real-time WebSocket updates.
 * Handles agent status, orchestration, and the 40-agent Elite Collective.
 *
 * @see docs/WEBSOCKET_PROTOCOL.md for event type specifications
 */

import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "@/stores/appStore";
import { api, queryKeys } from "@/api/client";
import type { AgentStatus } from "@/types";

// ============================================================================
// Types
// ============================================================================

interface AgentStatusData {
  agent_id: string;
  name: string;
  status: AgentStatus;
  current_task?: string;
  cpu_usage: number;
  memory_mb: number;
  tasks_completed: number;
  last_active: string;
  error?: string;
}

// Note: AgentStatus is imported from @/types

interface AgentStats {
  totalAgents: number;
  activeAgents: number;
  idleAgents: number;
  errorAgents: number;
  totalTasksCompleted: number;
  avgCpuUsage: number;
  avgMemoryMb: number;
}

interface AgentTask {
  id: string;
  name: string;
  agentId: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  startTime?: string;
  endTime?: string;
  error?: string;
}

interface UseAgentsOptions {
  /** Enable real-time WebSocket updates (default: true) */
  enableRealtime?: boolean;
  /** Poll interval for REST fallback (default: 10000ms) */
  pollInterval?: number;
  /** Filter agents by status */
  statusFilter?: AgentStatus[];
}

// ============================================================================
// Hook: useAgents
// ============================================================================

/**
 * Hook for agent swarm management with real-time status updates.
 *
 * @example
 * ```tsx
 * const { agents, stats, activeAgents, isLoading } = useAgents();
 *
 * return (
 *   <div>
 *     <p>Active: {stats.activeAgents} / {stats.totalAgents}</p>
 *     {agents.map(agent => (
 *       <AgentCard key={agent.id} agent={agent} />
 *     ))}
 *   </div>
 * );
 * ```
 */
export function useAgents(options: UseAgentsOptions = {}) {
  const { enableRealtime = true, pollInterval = 10000, statusFilter } = options;

  const wsConnected = useAppStore((state) => state.wsConnected);
  const lastMessage = useAppStore((state) => state.lastMessage);

  // Track real-time agent updates
  const [realtimeUpdates, setRealtimeUpdates] = useState<
    Map<string, AgentStatusData>
  >(new Map());

  // Fetch agents from API
  const {
    data: apiAgents = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.agents.list(),
    queryFn: async () => {
      const response = await api.agents.getAll();
      return response.data;
    },
    refetchInterval: !wsConnected && enableRealtime ? pollInterval : false,
  });

  // Handle real-time agent status updates
  useEffect(() => {
    if (!enableRealtime || !lastMessage) return;

    if (lastMessage.type === "agent.status") {
      const update = lastMessage.data as AgentStatusData;

      setRealtimeUpdates((prev) => {
        const next = new Map(prev);
        next.set(update.agent_id, update);
        return next;
      });
    }
  }, [lastMessage, enableRealtime]);

  // Merge API data with real-time updates
  const agents = useMemo(() => {
    const merged = apiAgents.map((agent) => {
      const realtimeData = realtimeUpdates.get(agent.id);
      if (realtimeData) {
        return {
          ...agent,
          status: realtimeData.status,
          currentTask: realtimeData.current_task,
          cpuUsage: realtimeData.cpu_usage,
          memoryMb: realtimeData.memory_mb,
          tasksCompleted: realtimeData.tasks_completed,
          lastActive: realtimeData.last_active,
          error: realtimeData.error,
        };
      }
      return agent;
    });

    // Apply status filter if provided
    if (statusFilter && statusFilter.length > 0) {
      return merged.filter((agent) => statusFilter.includes(agent.status));
    }

    return merged;
  }, [apiAgents, realtimeUpdates, statusFilter]);

  // Calculate statistics
  const stats = useMemo((): AgentStats => {
    const totalAgents = agents.length;
    const activeAgents = agents.filter(
      (a) => a.status === "active" || a.status === "processing",
    ).length;
    const idleAgents = agents.filter((a) => a.status === "idle").length;
    const errorAgents = agents.filter((a) => a.status === "error").length;

    const totalTasksCompleted = agents.reduce(
      (sum, a) => sum + (a.metrics?.tasksCompleted ?? 0),
      0,
    );

    const avgCpuUsage =
      totalAgents > 0
        ? agents.reduce((sum, a) => sum + (a.metrics?.cpuUsage ?? 0), 0) /
          totalAgents
        : 0;

    const avgMemoryMb =
      totalAgents > 0
        ? agents.reduce((sum, a) => sum + (a.metrics?.memoryUsage ?? 0), 0) /
          totalAgents
        : 0;

    return {
      totalAgents,
      activeAgents,
      idleAgents,
      errorAgents,
      totalTasksCompleted,
      avgCpuUsage,
      avgMemoryMb,
    };
  }, [agents]);

  // Convenience accessors
  const activeAgents = useMemo(
    () =>
      agents.filter((a) => a.status === "active" || a.status === "processing"),
    [agents],
  );

  const idleAgents = useMemo(
    () => agents.filter((a) => a.status === "idle"),
    [agents],
  );

  const errorAgents = useMemo(
    () => agents.filter((a) => a.status === "error"),
    [agents],
  );

  return {
    agents,
    stats,
    activeAgents,
    idleAgents,
    errorAgents,
    isLoading,
    error: error as Error | null,
    refetch,
    isRealtime: wsConnected && enableRealtime,
  };
}

// ============================================================================
// Hook: useAgent
// ============================================================================

/**
 * Hook for a single agent with real-time updates.
 *
 * @example
 * ```tsx
 * const { agent, isActive, pause, resume } = useAgent("agent-1");
 * ```
 */
export function useAgent(agentId: string) {
  const { agents, isLoading, error } = useAgents();
  const queryClient = useQueryClient();

  const agent = useMemo(
    () => agents.find((a) => a.id === agentId) ?? null,
    [agents, agentId],
  );

  const isActive = agent?.status === "active" || agent?.status === "processing";
  const isIdle = agent?.status === "idle";
  const hasError = agent?.status === "error";

  // Pause agent mutation
  const pauseMutation = useMutation({
    mutationFn: async () => {
      await api.agents.pause(agentId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list() });
    },
  });

  // Resume agent mutation
  const resumeMutation = useMutation({
    mutationFn: async () => {
      await api.agents.resume(agentId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list() });
    },
  });

  // Restart agent mutation
  const restartMutation = useMutation({
    mutationFn: async () => {
      await api.agents.restart(agentId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list() });
    },
  });

  return {
    agent,
    isActive,
    isIdle,
    hasError,
    isLoading,
    error,
    pause: pauseMutation.mutate,
    resume: resumeMutation.mutate,
    restart: restartMutation.mutate,
    isPausing: pauseMutation.isPending,
    isResuming: resumeMutation.isPending,
    isRestarting: restartMutation.isPending,
  };
}

// ============================================================================
// Hook: useAgentTasks
// ============================================================================

/**
 * Hook for agent task management and monitoring.
 *
 * @example
 * ```tsx
 * const { tasks, runningTasks, submitTask } = useAgentTasks();
 * ```
 */
export function useAgentTasks() {
  const queryClient = useQueryClient();
  const lastMessage = useAppStore((state) => state.lastMessage);

  const {
    data: tasks = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.agents.tasks(),
    queryFn: async () => {
      const response = await api.agents.getTasks();
      return response.data as AgentTask[];
    },
  });

  // Handle task updates from WebSocket
  useEffect(() => {
    if (!lastMessage || lastMessage.type !== "agent.status") return;

    const update = lastMessage.data as AgentStatusData;
    if (update.current_task) {
      // Refresh tasks when agent reports a current task
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.tasks() });
    }
  }, [lastMessage, queryClient]);

  // Submit task mutation
  const submitTask = useMutation({
    mutationFn: async (params: {
      agentId?: string;
      taskType: string;
      payload: Record<string, unknown>;
    }) => {
      const response = await api.agents.submitTask(params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.tasks() });
    },
  });

  // Cancel task mutation
  const cancelTask = useMutation({
    mutationFn: async (taskId: string) => {
      await api.agents.cancelTask(taskId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.tasks() });
    },
  });

  const runningTasks = useMemo(
    () => tasks.filter((t) => t.status === "running"),
    [tasks],
  );

  const pendingTasks = useMemo(
    () => tasks.filter((t) => t.status === "pending"),
    [tasks],
  );

  const completedTasks = useMemo(
    () => tasks.filter((t) => t.status === "completed"),
    [tasks],
  );

  return {
    tasks,
    runningTasks,
    pendingTasks,
    completedTasks,
    isLoading,
    error: error as Error | null,
    refetch,
    submitTask: submitTask.mutate,
    cancelTask: cancelTask.mutate,
    isSubmitting: submitTask.isPending,
    isCancelling: cancelTask.isPending,
  };
}

// ============================================================================
// Hook: useSwarmOrchestrator
// ============================================================================

interface SwarmStatus {
  totalAgents: number;
  activeAgents: number;
  taskQueue: number;
  memoryUsage: number;
  isActive?: boolean;
  mode?: "manual" | "auto" | "learning";
  throughput?: number;
  efficiency?: number;
}

/**
 * Hook for agent swarm orchestration and control.
 * Manages the 40-agent Elite Collective coordination.
 *
 * @example
 * ```tsx
 * const { status, setMode, scaleUp, scaleDown } = useSwarmOrchestrator();
 * ```
 */
export function useSwarmOrchestrator() {
  const { stats } = useAgents();
  const queryClient = useQueryClient();

  const {
    data: swarmStatus,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKeys.agents.swarm(),
    queryFn: async () => {
      const response = await api.agents.getSwarmStatus();
      return response.data as SwarmStatus;
    },
  });

  // Set orchestration mode
  const setMode = useMutation({
    mutationFn: async (mode: "manual" | "auto" | "learning") => {
      await api.agents.setSwarmMode(mode);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.swarm() });
    },
  });

  // Scale up agents
  const scaleUp = useMutation({
    mutationFn: async (count: number) => {
      await api.agents.scaleSwarm(count);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.swarm() });
    },
  });

  // Scale down agents
  const scaleDown = useMutation({
    mutationFn: async (count: number) => {
      await api.agents.scaleSwarm(-count);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.swarm() });
    },
  });

  // Pause all agents
  const pauseAll = useMutation({
    mutationFn: async () => {
      await api.agents.pauseAll();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list() });
    },
  });

  // Resume all agents
  const resumeAll = useMutation({
    mutationFn: async () => {
      await api.agents.resumeAll();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.list() });
    },
  });

  const status: SwarmStatus = swarmStatus ?? {
    totalAgents: stats.totalAgents,
    activeAgents: stats.activeAgents,
    taskQueue: 0,
    memoryUsage: stats.avgMemoryMb,
    isActive: stats.activeAgents > 0,
    mode: "auto",
    throughput: 0,
    efficiency:
      stats.totalAgents > 0
        ? (stats.activeAgents / stats.totalAgents) * 100
        : 0,
  };

  return {
    status,
    isLoading,
    error: error as Error | null,
    setMode: setMode.mutate,
    scaleUp: scaleUp.mutate,
    scaleDown: scaleDown.mutate,
    pauseAll: pauseAll.mutate,
    resumeAll: resumeAll.mutate,
    isSettingMode: setMode.isPending,
    isScaling: scaleUp.isPending || scaleDown.isPending,
  };
}

// ============================================================================
// Hook: useAgentMetrics
// ============================================================================

/**
 * Hook for aggregated agent performance metrics.
 *
 * @example
 * ```tsx
 * const { cpuUsage, memoryUsage, tasksPerMinute } = useAgentMetrics();
 * ```
 */
export function useAgentMetrics() {
  const { agents, stats } = useAgents();

  const metrics = useMemo(() => {
    // Calculate aggregate metrics
    const totalCpu = agents.reduce(
      (sum, a) => sum + (a.metrics?.cpuUsage ?? 0),
      0,
    );
    const totalMemory = agents.reduce(
      (sum, a) => sum + (a.metrics?.memoryUsage ?? 0),
      0,
    );

    // Get agents sorted by activity
    const byActivity = [...agents].sort(
      (a, b) =>
        (b.metrics?.tasksCompleted ?? 0) - (a.metrics?.tasksCompleted ?? 0),
    );

    return {
      cpuUsage: stats.avgCpuUsage,
      memoryUsage: stats.avgMemoryMb,
      totalCpuUsage: totalCpu,
      totalMemoryMb: totalMemory,
      tasksCompleted: stats.totalTasksCompleted,
      activeRatio:
        stats.totalAgents > 0 ? stats.activeAgents / stats.totalAgents : 0,
      topPerformers: byActivity.slice(0, 5),
    };
  }, [agents, stats]);

  return metrics;
}

export default useAgents;
