import { useEffect, useRef, useState, useCallback } from 'react';
import type {
  VehicleData,
  RoadData,
  TelemetryData,
  SimulationFrame,
  ConfigCommand,
  TelemetrySnapshot,
} from '../types';

const WS_URL = `ws://${window.location.hostname}:8000/ws`;
const TELEMETRY_HISTORY_SIZE = 180; // 60 seconds at ~3 Hz
const TELEMETRY_INTERVAL_MS = 333; // throttle telemetry updates to ~3 Hz

export interface SimulationState {
  /** Live vehicle data (updated every frame, no re-renders) */
  vehiclesRef: React.MutableRefObject<VehicleData[]>;
  /** Road geometry (rarely changes) */
  road: RoadData | null;
  /** Latest telemetry for UI display */
  telemetry: TelemetryData | null;
  /** Rolling telemetry history for charts */
  telemetryHistory: TelemetrySnapshot[];
  /** WebSocket connection status */
  connected: boolean;
  /** Send a configuration command to the server */
  sendConfig: (command: ConfigCommand) => void;
  /** Current tick number */
  tickRef: React.MutableRefObject<number>;
}

export function useSimulation(): SimulationState {
  const vehiclesRef = useRef<VehicleData[]>([]);
  const tickRef = useRef<number>(0);
  const wsRef = useRef<WebSocket | null>(null);

  const [road, setRoad] = useState<RoadData | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetrySnapshot[]>([]);
  const [connected, setConnected] = useState(false);

  // Telemetry throttle
  const lastTelemetryUpdate = useRef(0);

  const sendConfig = useCallback((command: ConfigCommand) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(command));
    }
  }, []);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let ws: WebSocket;

    const connect = () => {
      ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected to simulation server');
        setConnected(true);
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected. Reconnecting in 2s...');
        setConnected(false);
        reconnectTimer = setTimeout(connect, 2000);
      };

      ws.onerror = (err) => {
        console.error('[WS] Error:', err);
        ws.close();
      };

      ws.onmessage = (event) => {
        try {
          const frame: SimulationFrame = JSON.parse(event.data);

          if (frame.type === 'state') {
            // Update refs (no re-renders)
            vehiclesRef.current = frame.vehicles;
            tickRef.current = frame.tick;

            // Set road data (only on first message or if changed)
            if (frame.road) {
              setRoad((prev) => {
                if (!prev || prev.circumference !== frame.road.circumference || prev.num_lanes !== frame.road.num_lanes || prev.paused !== frame.road.paused) {
                  return frame.road;
                }
                if (prev.lane_width !== frame.road.lane_width || prev.speed_limit_mph !== frame.road.speed_limit_mph) {
                  return frame.road;
                }
                return prev;
              });
            }

            // Throttled telemetry updates for the UI
            const now = performance.now();
            if (now - lastTelemetryUpdate.current > TELEMETRY_INTERVAL_MS) {
              lastTelemetryUpdate.current = now;
              setTelemetry(frame.telemetry);

              setTelemetryHistory((prev) => {
                const snapshot: TelemetrySnapshot = {
                  timestamp: Date.now(),
                  ...frame.telemetry,
                };
                const next = [...prev, snapshot];
                if (next.length > TELEMETRY_HISTORY_SIZE) {
                  return next.slice(next.length - TELEMETRY_HISTORY_SIZE);
                }
                return next;
              });
            }
          }
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  return {
    vehiclesRef,
    road,
    telemetry,
    telemetryHistory,
    connected,
    sendConfig,
    tickRef,
  };
}
