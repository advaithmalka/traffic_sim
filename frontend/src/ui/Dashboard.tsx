import { useCallback, useEffect, useState } from 'react';
import { Slider } from './Slider';
import { TelemetryChart } from './TelemetryChart';
import type {
  TelemetryData,
  TelemetrySnapshot,
  ConfigCommand,
  RoadData,
} from '../types';

interface DashboardProps {
  connected: boolean;
  telemetry: TelemetryData | null;
  telemetryHistory: TelemetrySnapshot[];
  sendConfig: (command: ConfigCommand) => void;
  road: RoadData | null;
}

const METERS_TO_FEET = 3.28084;
const DEFAULT_TRACK_RADIUS_FT = 150;
const DEFAULT_TRACK_CIRCUMFERENCE_FT = DEFAULT_TRACK_RADIUS_FT * 2 * Math.PI;

/**
 * Glassmorphic sidebar overlay with controls and telemetry.
 */
export function Dashboard({
  connected,
  telemetry,
  telemetryHistory,
  sendConfig,
  road,
}: DashboardProps) {
  const [speedLimit, setSpeedLimit] = useState(67);
  const [lanes, setLanes] = useState(2);
  const [circumferenceFt, setCircumferenceFt] = useState(DEFAULT_TRACK_CIRCUMFERENCE_FT);
  const [collapsed, setCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<'profiles' | 'environment'>('profiles');
  const [simSpeed, setSimSpeed] = useState<number>(1);

  useEffect(() => {
    if (!road) {
      return;
    }

    setSpeedLimit(Math.round(road.speed_limit_mph));
    setLanes(road.num_lanes);
    setCircumferenceFt(road.circumference * METERS_TO_FEET);
  }, [road]);

  const handleRemoveAll = useCallback(() => {
    sendConfig({ type: 'remove_all_profiles' });
  }, [sendConfig]);

  const handleAddProfile = useCallback(
    (profileId: string) => {
      sendConfig({ type: 'add_profile', profile: profileId });
    },
    [sendConfig]
  );

  const handleRemoveProfile = useCallback(
    (profileId: string) => {
      sendConfig({ type: 'remove_profile', profile: profileId });
    },
    [sendConfig]
  );

  const handleSpeedLimit = useCallback(
    (value: number) => {
      setSpeedLimit(value);
      sendConfig({ type: 'speed_limit', value });
    },
    [sendConfig]
  );

  const handleLanes = useCallback(
    (value: number) => {
      setLanes(value);
      sendConfig({ type: 'num_lanes', value });
    },
    [sendConfig]
  );

  const handleCircumference = useCallback(
    (value_ft: number) => {
      setCircumferenceFt(value_ft);
      sendConfig({ type: 'circumference', value: value_ft });
    },
    [sendConfig]
  );

  const handleResetSimulation = useCallback(() => {
    setSimSpeed(1);
    sendConfig({ type: 'reset_simulation' });
  }, [sendConfig]);

  const handlePause = useCallback(() => {
    sendConfig({ type: 'toggle_pause' });
  }, [sendConfig]);

  return (
    <div
      className="slide-in-left"
      style={{
        position: 'absolute',
        top: '16px',
        left: '16px',
        bottom: '16px',
        width: collapsed ? '48px' : '320px',
        zIndex: 10,
        transition: 'width 0.3s ease',
        pointerEvents: 'auto',
      }}
    >
      {/* Collapse toggle */}
      <button
        id="dashboard-toggle"
        onClick={() => setCollapsed(!collapsed)}
        style={{
          position: 'absolute',
          top: '12px',
          right: collapsed ? '8px' : '12px',
          width: '32px',
          height: '32px',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)',
          background: 'var(--bg-panel)',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '14px',
          zIndex: 11,
          transition: 'all 0.2s ease',
        }}
        title={collapsed ? 'Expand panel' : 'Collapse panel'}
      >
        {collapsed ? '▶' : '◀'}
      </button>

      {!collapsed && (
        <div
          className="glass-panel"
          style={{
            width: '100%',
            height: '100%',
            padding: '20px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            position: 'relative'
          }}
        >
          {/* Connection status overlay */}
          {!connected && (
            <div style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(15, 23, 42, 0.8)',
              backdropFilter: 'blur(4px)',
              zIndex: 100,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '16px',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#ef4444',
              textAlign: 'center',
              padding: '20px'
            }}>
              <div style={{ fontSize: '24px', marginBottom: '8px' }}>⚠️</div>
              <div style={{ fontSize: '14px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Backend Disconnected</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>Reconnecting...</div>
            </div>
          )}

          {/* Header */}
          <div style={{ marginBottom: '8px', zIndex: 1 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                marginBottom: '4px',
                justifyContent: 'space-between',
              }}
            >
              <h1
                style={{
                  fontSize: '16px',
                  fontWeight: 700,
                  letterSpacing: '-0.02em',
                  background: 'linear-gradient(135deg, #4f8eff, #22d3ee)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                Traffic Simulator
              </h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginRight: '30px' }}>
                <select
                  value={simSpeed}
                  onChange={(e) => {
                    const next = parseInt(e.target.value);
                    setSimSpeed(next);
                    sendConfig({ type: 'set_sim_speed', value: next });
                  }}
                  title="Fast Forward Simulation"
                  style={{
                    background: simSpeed > 1 ? 'rgba(34, 211, 238, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                    border: `1px solid ${simSpeed > 1 ? 'var(--accent-blue)' : 'var(--border-subtle)'}`,
                    color: simSpeed > 1 ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: 800,
                    borderRadius: '4px',
                    padding: '4px 6px',
                    outline: 'none',
                    textAlign: 'center'
                  }}
                >
                  <option value={1} style={{ background: '#0a0f1e', color: 'white' }}>1x Speed</option>
                  <option value={2} style={{ background: '#0a0f1e', color: 'white' }}>2x Speed</option>
                  <option value={5} style={{ background: '#0a0f1e', color: 'white' }}>5x Speed</option>
                  <option value={10} style={{ background: '#0a0f1e', color: 'white' }}>10x Speed</option>
                </select>
                <button
                  id="pause-button"
                  onClick={handlePause}
                  title={road?.paused ? 'Play' : 'Pause'}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontSize: '18px',
                    lineHeight: 1,
                    padding: 0,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.color = 'var(--text-hover)')}
                  onMouseOut={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
                >
                  {road?.paused ? '▶' : '⏸'}
                </button>
              </div>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11px',
                color: 'var(--text-muted)',
              }}
            >
              <span
                className={`status-dot ${connected ? 'connected' : 'disconnected'}`}
              />
              {connected ? 'Connected' : 'Reconnecting...'}
            </div>
          </div>

          {/* Tabs Navigation */}
          <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '12px' }}>
            <button
              onClick={() => setActiveTab('profiles')}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'profiles' ? '2px solid var(--accent-blue)' : '2px solid transparent',
                color: activeTab === 'profiles' ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '8px 0',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              DRIVER PROFILES
            </button>
            <button
              onClick={() => setActiveTab('environment')}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'environment' ? '2px solid var(--accent-blue)' : '2px solid transparent',
                color: activeTab === 'environment' ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '8px 0',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              ENVIRONMENT
            </button>
          </div>

          {activeTab === 'profiles' && (
            <div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                {[
                  { id: 'COMMUTER', label: 'Commuter', color: '#808080', tagline: 'The Baseline Driver', desc: 'The control group of the highway. Commuters drive at the speed limit, maintain standard following distances, and behave predictably. They change lanes only when an obvious speed advantage presents itself without disrupting the flow of others.' },
                  { id: 'AGGRESSIVE', label: 'Weaver', color: '#FF0000', tagline: 'High Speed, Low Patience', desc: 'Driven by a desire to maximize speed at all costs. This profile tailgates heavily, brakes violently, and forcefully weaves into any available gap. Their erratic speed changes are the primary catalyst for triggering ripple effects and phantom traffic jams.' },
                  { id: 'CAMPER', label: 'Left Camper', color: '#800080', tagline: 'The Rolling Roadblock', desc: 'Stubbornly occupies the innermost passing lane while driving exactly at—or slightly below—the speed limit. By refusing to yield to faster traffic, they create severe artificial bottlenecks and force other drivers into dangerous right-side passing maneuvers.' },
                  { id: 'CAUTIOUS', label: 'Cautious', color: '#FFFF00', tagline: 'Overly Cautious', desc: 'Prioritizes absolute safety over speed. They drive under the limit, leave massive multi-car gaps ahead of them, and are highly reluctant to change lanes. While safe individually, their slow acceleration can drag down the overall throughput of a busy highway.' },
                  { id: 'FOLLOWER', label: 'Pass & Return', color: '#0000FF', tagline: 'Perfect Lane Discipline', desc: 'The gold standard of highway etiquette. They treat the left lane strictly as a passing zone. Once they have successfully overtaken slower traffic, they will proactively merge back into the cruising lanes to maintain optimal systemic flow.' },
                  { id: 'PACER', label: 'Auto Pacer', color: '#00FF00', tagline: 'The Jam Breaker', desc: 'An algorithmic agent designed to cure gridlock. Rather than racing to the bumper of the car ahead, the pacer maintains a steady, moderate speed and a massive buffer gap. This allows it to absorb the shockwaves of aggressive braking ahead, keeping the traffic behind it moving in a continuous flow.' },
                ].map((prof) => {
                  const count = telemetry?.profile_counts?.[prof.id] || 0;
                  return (
                    <ProfileItem
                      key={prof.id}
                      prof={prof}
                      count={count}
                      onAdd={() => handleAddProfile(prof.id)}
                      onRemove={() => handleRemoveProfile(prof.id)}
                    />
                  );
                })}
              </div>
              <button
                onClick={handleRemoveAll}
                style={{
                  width: '100%',
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#ef4444',
                  padding: '8px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  marginTop: '8px',
                }}
                onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)')}
                onMouseOut={(e) => (e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)')}
              >
                REMOVE ALL CARS
              </button>
            </div>
          )}

          {activeTab === 'environment' && (
            <div>
              <Slider
                id="lanes-slider"
                label="Track Lanes"
                value={lanes}
                min={1}
                max={6}
                step={1}
                unit=" lanes"
                accentColor="var(--accent-violet)"
                onChange={handleLanes}
              />

              <Slider
                id="size-slider"
                label="Track Radius"
                value={Math.round(circumferenceFt / (2 * Math.PI))}
                min={50}
                max={500}
                step={10}
                unit=" ft"
                accentColor="var(--accent-blue)"
                onChange={(val) => handleCircumference(val * 2 * Math.PI)}
              />

              <Slider
                id="speed-slider"
                label="Speed Limit"
                value={speedLimit}
                min={15}
                max={150}
                step={1}
                unit=" mph"
                accentColor="var(--accent-amber)"
                onChange={handleSpeedLimit}
              />

              <button
                onClick={handleResetSimulation}
                style={{
                  width: '100%',
                  background: 'rgba(56, 189, 248, 0.15)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  color: 'var(--accent-blue)',
                  padding: '10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  marginTop: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
                onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(56, 189, 248, 0.25)')}
                onMouseOut={(e) => (e.currentTarget.style.background = 'rgba(56, 189, 248, 0.15)')}
              >
                <span>↺</span> RESET TO DEFAULTS
              </button>
            </div>
          )}

          {/* Divider */}
          <hr
            style={{
              border: 'none',
              borderTop: '1px solid var(--border-subtle)',
              margin: '12px 0 8px 0',
            }}
          />

          {/* Telemetry Stats */}
          <div>
            <h2
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                marginBottom: '12px',
              }}
            >
              Live Telemetry
            </h2>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '8px',
                marginBottom: '16px',
              }}
            >
              <StatCard
                label="Avg Speed"
                value={telemetry ? `${telemetry.avg_speed}` : '--'}
                unit="mph"
                color="var(--accent-blue)"
              />
              <StatCard
                label="Flow Rate"
                value={telemetry ? `${Math.round(telemetry.flow)}` : '--'}
                unit="veh/h"
                color="var(--accent-emerald)"
              />
              <StatCard
                label="Vehicles"
                value={telemetry ? `${telemetry.count}` : '--'}
                unit=""
                color="var(--accent-violet)"
              />
              <StatCard
                label="Density"
                value={telemetry ? `${telemetry.density}` : '--'}
                unit="v/mi"
                color="var(--accent-amber)"
              />
            </div>
          </div>

          {/* Divider */}
          <hr
            style={{
              border: 'none',
              borderTop: '1px solid var(--border-subtle)',
              margin: '8px 0',
            }}
          />

          {/* Telemetry Chart */}
          <div>
            <h2
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                marginBottom: '8px',
              }}
            >
              Speed & Flow History
            </h2>
            <div
              style={{
                display: 'flex',
                gap: '12px',
                marginBottom: '6px',
                fontSize: '10px',
              }}
            >
              <span style={{ color: '#4f8eff' }}>● Speed (mph)</span>
              <span style={{ color: '#34d399' }}>● Flow (×100 veh/h)</span>
            </div>
            <TelemetryChart data={telemetryHistory} />
          </div>

          {/* Footer */}
          <div
            style={{
              marginTop: 'auto',
              paddingTop: '12px',
              borderTop: '1px solid var(--border-subtle)',
              fontSize: '10px',
              color: 'var(--text-muted)',
              textAlign: 'center',
            }}
          >
            IDM + MOBIL Multi-Agent Simulation
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Inline Components ────────────────────────────────────────────── */

function ProfileItem({ prof, count, onAdd, onRemove }: any) {
  const [hovered, setHovered] = useState(false);

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'help' }}
      >
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: prof.color }} />
        <span style={{ fontSize: '12px', color: 'var(--text-primary)' }}>{prof.label}</span>
      </div>

      {hovered && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          marginTop: '6px',
          background: 'rgba(15, 20, 35, 0.98)',
          border: `1px solid ${prof.color}`,
          padding: '12px',
          borderRadius: '8px',
          width: '260px',
          zIndex: 1000,
          boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
          color: 'white',
          pointerEvents: 'none'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <span style={{ fontSize: '11px', fontWeight: 800, color: prof.color, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{prof.tagline}</span>
          </div>
          <p style={{ margin: 0, fontSize: '11px', lineHeight: '1.4', color: 'var(--text-muted)' }}>
            {prof.desc}
          </p>
        </div>
      )}

      {/* Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={onRemove}
          disabled={count <= 0}
          style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-primary)',
            borderRadius: '4px',
            width: '24px', height: '24px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: count > 0 ? 'pointer' : 'default',
            opacity: count > 0 ? 1 : 0.5
          }}
        >-</button>
        <span style={{ width: '20px', textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>{count}</span>
        <button
          onClick={onAdd}
          style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-primary)',
            borderRadius: '4px',
            width: '24px', height: '24px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer'
          }}
        >+</button>
      </div>
    </div>
  );
}

/* ── Stat Card Component ────────────────────────────────────────────── */
interface StatCardProps {
  label: string;
  value: string;
  unit: string;
  color: string;
}

function StatCard({ label, value, unit, color }: StatCardProps) {
  return (
    <div
      className="glass-panel-hover"
      style={{
        padding: '10px 12px',
        borderRadius: '10px',
        border: '1px solid var(--border-subtle)',
        background: 'rgba(15, 20, 35, 0.5)',
        transition: 'all 0.2s ease',
      }}
    >
      <div
        style={{
          fontSize: '10px',
          color: 'var(--text-muted)',
          marginBottom: '4px',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: '18px',
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
          color,
          lineHeight: 1,
        }}
      >
        {value}
        {unit && (
          <span
            style={{
              fontSize: '10px',
              fontWeight: 400,
              color: 'var(--text-muted)',
              marginLeft: '2px',
            }}
          >
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}
