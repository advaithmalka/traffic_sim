/* ── Simulation Data Types ────────────────────────────────────────────── */

export interface VehicleData {
  id: number;
  x: number;
  y: number;
  rotation: number;
  speed: number;
  lane: number;
  profile: string;
  color: string;
  acceleration: number;
  gap: number;
}

export interface RoadData {
  circumference: number;
  inner_radius: number;
  num_lanes: number;
  lane_width: number;
  paused: boolean;
}

export interface TelemetryData {
  avg_speed: number;
  flow: number;
  count: number;
  density: number;
  profile_counts: Record<string, number>;
}

export interface SimulationFrame {
  type: 'state';
  tick: number;
  vehicles: VehicleData[];
  telemetry: TelemetryData;
  road: RoadData;
}

export interface ConfigCommand {
  type: 'speed_limit' | 'num_lanes' | 'circumference' | 'toggle_pause' | 'add_profile' | 'remove_profile' | 'remove_all_profiles';
  value?: number;
  profile?: string;
}

export interface TelemetrySnapshot {
  timestamp: number;
  avg_speed: number;
  flow: number;
  count: number;
  density: number;
}
