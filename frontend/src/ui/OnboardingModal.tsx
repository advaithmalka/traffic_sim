import { useEffect, useState } from 'react';

const STORAGE_KEY = 'traffic_sim_onboarded_v1';

/**
 * First-load welcome modal. Dismissal persists in localStorage.
 * Re-openable from the dashboard footer via the exported helper.
 */
export function OnboardingModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      setOpen(true);
    }
    const handler = () => setOpen(true);
    window.addEventListener('traffic-sim:show-onboarding', handler);
    return () => window.removeEventListener('traffic-sim:show-onboarding', handler);
  }, []);

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1');
    setOpen(false);
  };

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(5, 8, 18, 0.72)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        pointerEvents: 'auto',
      }}
      onClick={dismiss}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: '520px',
          width: '100%',
          background: 'linear-gradient(180deg, rgba(20, 28, 50, 0.98), rgba(12, 18, 32, 0.98))',
          border: '1px solid rgba(79, 142, 255, 0.35)',
          borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.6), 0 0 80px rgba(34, 211, 238, 0.08)',
          padding: '28px 28px 22px',
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-sans)',
        }}
      >
        <div
          style={{
            fontSize: '10px',
            fontWeight: 800,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color: 'var(--accent-blue)',
            marginBottom: '6px',
          }}
        >
          Welcome
        </div>
        <h2
          style={{
            fontSize: '22px',
            fontWeight: 700,
            margin: '0 0 12px 0',
            background: 'linear-gradient(135deg, #4f8eff, #22d3ee)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.02em',
          }}
        >
          Multi-Agent Traffic Simulator
        </h2>
        <p
          style={{
            fontSize: '13px',
            lineHeight: 1.55,
            color: 'var(--text-secondary)',
            margin: '0 0 18px 0',
          }}
        >
          Every car is an independent agent driving by the{' '}
          <strong style={{ color: 'var(--text-primary)' }}>IDM + MOBIL</strong> physics
          model used in real traffic-engineering research. Six driver
          personalities share the road. Watch how their interactions create
          (or cure) the ghost traffic jams you see every day.
        </p>

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            marginBottom: '20px',
          }}
        >
          <Tip
            color="#00FF00"
            label="Run the experiment"
            text="Swap Commuters or Cautious drivers for Auto Pacers and watch the Flow Rate climb."
          />
          <Tip
            color="#22d3ee"
            label="Try a preset"
            text="Pick a scenario like Rush Hour or Robotaxi Future to see scripted traffic mixes."
          />
          <Tip
            color="#ef4444"
            label="Cause an incident"
            text="Force a random car into a hard brake and watch the shockwave ripple back."
          />
          <Tip
            color="#a78bfa"
            label="Inspect the scene"
            text="Pan, zoom, and rotate the 3D world — hover any car for live telemetry."
          />
        </div>

        <button
          onClick={dismiss}
          style={{
            width: '100%',
            background: 'linear-gradient(135deg, rgba(79, 142, 255, 0.25), rgba(34, 211, 238, 0.25))',
            border: '1px solid rgba(79, 142, 255, 0.5)',
            color: 'var(--text-primary)',
            padding: '12px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: 700,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onMouseOver={(e) =>
            (e.currentTarget.style.background =
              'linear-gradient(135deg, rgba(79, 142, 255, 0.4), rgba(34, 211, 238, 0.4))')
          }
          onMouseOut={(e) =>
            (e.currentTarget.style.background =
              'linear-gradient(135deg, rgba(79, 142, 255, 0.25), rgba(34, 211, 238, 0.25))')
          }
        >
          Start Exploring
        </button>
      </div>
    </div>
  );
}

interface TipProps {
  color: string;
  label: string;
  text: string;
}

function Tip({ color, label, text }: TipProps) {
  return (
    <div
      style={{
        display: 'flex',
        gap: '10px',
        padding: '10px 12px',
        background: 'rgba(255, 255, 255, 0.03)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '8px',
      }}
    >
      <div
        style={{
          width: '4px',
          borderRadius: '2px',
          background: color,
          flexShrink: 0,
        }}
      />
      <div>
        <div
          style={{
            fontSize: '11px',
            fontWeight: 700,
            color,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '2px',
          }}
        >
          {label}
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
          {text}
        </div>
      </div>
    </div>
  );
}
