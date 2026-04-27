/* ── Simulation Data Types ────────────────────────────────────────────── */

export type TrackType = 'ring' | 'merge';

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
  raw_gap: number;
}

export interface RoadData {
  track_type: TrackType;
  circumference: number;
  inner_radius: number;
  straight_length: number;
  aux_lane_start: number;
  merge_start: number;
  merge_end: number;
  num_lanes: number;
  lane_width: number;
  speed_limit_mph: number;
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
  type:
    | 'speed_limit'
    | 'num_lanes'
    | 'circumference'
    | 'toggle_pause'
    | 'add_profile'
    | 'remove_profile'
    | 'remove_all_profiles'
    | 'set_sim_speed'
    | 'reset_simulation'
    | 'apply_preset'
    | 'cause_incident';
  value?: number;
  profile?: string;
  preset?: string;
}

export interface TelemetrySnapshot {
  elapsedMs: number;
  avg_speed: number;
  flow: number;
  count: number;
  density: number;
}
