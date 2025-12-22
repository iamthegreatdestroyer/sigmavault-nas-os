/**
 * SigmaVault NAS OS - WebSocket Hook
 * @module hooks/useWebSocket
 *
 * Real-time WebSocket connection for live updates.
 * Implements automatic reconnection with exponential backoff.
 */

import { useEffect, useRef, useCallback } from "react";
import { useAppStore, appActions } from "@/stores/appStore";
import type {
  WebSocketMessage,
  JsonRpcRequest,
  JsonRpcResponse,
} from "@/types";

// ============================================================================
// Configuration
// ============================================================================

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8080/ws";
const INITIAL_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;
const RECONNECT_MULTIPLIER = 1.5;
const PING_INTERVAL = 30000;
const PONG_TIMEOUT = 5000;

// ============================================================================
// Types
// ============================================================================

interface UseWebSocketOptions {
  autoConnect?: boolean;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  send: (message: WebSocketMessage) => void;
  sendRpc: <T>(method: string, params?: unknown[]) => Promise<T>;
  connect: () => void;
  disconnect: () => void;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useWebSocket(
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const { autoConnect = true, onOpen, onClose, onError, onMessage } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pongTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingRpcRef = useRef<
    Map<
      string | number,
      {
        resolve: (value: unknown) => void;
        reject: (error: Error) => void;
      }
    >
  >(new Map());
  const mountedRef = useRef(true);

  const setWsConnected = useAppStore((state) => state.setWsConnected);
  const setLastPing = useAppStore((state) => state.setLastPing);
  const isConnected = useAppStore((state) => state.wsConnected);

  // --------------------------------------------------------------------------
  // Cleanup
  // --------------------------------------------------------------------------
  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current);
      pongTimeoutRef.current = null;
    }
  }, []);

  // --------------------------------------------------------------------------
  // Start Ping/Pong
  // --------------------------------------------------------------------------
  const startPingPong = useCallback(() => {
    cleanup();

    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({ type: "ping", timestamp: new Date().toISOString() })
        );

        pongTimeoutRef.current = setTimeout(() => {
          console.warn("[WebSocket] Pong timeout, reconnecting...");
          wsRef.current?.close();
        }, PONG_TIMEOUT);
      }
    }, PING_INTERVAL);
  }, [cleanup]);

  // --------------------------------------------------------------------------
  // Connect
  // --------------------------------------------------------------------------
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    cleanup();

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;

        console.log("[WebSocket] Connected to", WS_URL);
        setWsConnected(true);
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
        startPingPong();
        onOpen?.();
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;

        console.log("[WebSocket] Disconnected:", event.code, event.reason);
        setWsConnected(false);
        cleanup();
        onClose?.();

        // Auto-reconnect with exponential backoff
        if (mountedRef.current) {
          const delay = reconnectDelayRef.current;
          console.log(`[WebSocket] Reconnecting in ${delay}ms...`);

          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              reconnectDelayRef.current = Math.min(
                delay * RECONNECT_MULTIPLIER,
                MAX_RECONNECT_DELAY
              );
              connect();
            }
          }, delay);
        }
      };

      ws.onerror = (error) => {
        if (!mountedRef.current) return;
        console.error("[WebSocket] Error:", error);
        onError?.(error);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;

        try {
          const data = JSON.parse(event.data);

          // Handle pong
          if (data.type === "pong") {
            if (pongTimeoutRef.current) {
              clearTimeout(pongTimeoutRef.current);
              pongTimeoutRef.current = null;
            }
            setLastPing(new Date().toISOString());
            return;
          }

          // Handle JSON-RPC response
          if ("jsonrpc" in data && data.id !== undefined) {
            const pending = pendingRpcRef.current.get(data.id);
            if (pending) {
              pendingRpcRef.current.delete(data.id);
              if (data.error) {
                pending.reject(new Error(data.error.message));
              } else {
                pending.resolve(data.result);
              }
            }
            return;
          }

          // Handle regular message
          const message = data as WebSocketMessage;
          appActions.handleWebSocketMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error("[WebSocket] Failed to parse message:", error);
        }
      };
    } catch (error) {
      console.error("[WebSocket] Failed to create connection:", error);
    }
  }, [
    cleanup,
    setWsConnected,
    setLastPing,
    startPingPong,
    onOpen,
    onClose,
    onError,
    onMessage,
  ]);

  // --------------------------------------------------------------------------
  // Disconnect
  // --------------------------------------------------------------------------
  const disconnect = useCallback(() => {
    cleanup();
    if (wsRef.current) {
      wsRef.current.close(1000, "Client disconnect");
      wsRef.current = null;
    }
    setWsConnected(false);
  }, [cleanup, setWsConnected]);

  // --------------------------------------------------------------------------
  // Send Message
  // --------------------------------------------------------------------------
  const send = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn("[WebSocket] Cannot send, not connected");
    }
  }, []);

  // --------------------------------------------------------------------------
  // Send RPC
  // --------------------------------------------------------------------------
  const sendRpc = useCallback(
    <T>(method: string, params?: unknown[]): Promise<T> => {
      return new Promise((resolve, reject) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
          reject(new Error("WebSocket not connected"));
          return;
        }

        const id = crypto.randomUUID();
        const request: JsonRpcRequest = {
          jsonrpc: "2.0",
          method,
          params,
          id,
        };

        pendingRpcRef.current.set(id, {
          resolve: resolve as (value: unknown) => void,
          reject,
        });

        wsRef.current.send(JSON.stringify(request));

        // Timeout after 30 seconds
        setTimeout(() => {
          if (pendingRpcRef.current.has(id)) {
            pendingRpcRef.current.delete(id);
            reject(new Error(`RPC timeout: ${method}`));
          }
        }, 30000);
      });
    },
    []
  );

  // --------------------------------------------------------------------------
  // Effect: Auto-connect
  // --------------------------------------------------------------------------
  useEffect(() => {
    mountedRef.current = true;

    if (autoConnect) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    isConnected,
    send,
    sendRpc,
    connect,
    disconnect,
  };
}

export default useWebSocket;
