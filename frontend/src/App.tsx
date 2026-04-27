import React from 'react';
import { useSimulation } from './hooks/useSimulation';
import { Scene } from './components/Scene';
import { Dashboard } from './ui/Dashboard';
import { OnboardingModal } from './ui/OnboardingModal';

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, color: 'white', background: 'red', height: '100vh', fontFamily: 'monospace' }}>
          <h2>Frontend Render Crash:</h2>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{this.state.error?.toString()}</pre>
          <pre style={{ whiteSpace: 'pre-wrap', marginTop: 20 }}>{this.state.error?.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * Root application component.
 * Wires the simulation WebSocket hook to the 3D scene and UI dashboard.
 */
export default function App() {
  const {
    vehiclesRef,
    road,
    telemetry,
    telemetryHistory,
    connected,
    sendConfig,
  } = useSimulation();

  return (
    <ErrorBoundary>
      <div
        style={{
          width: '100vw',
          height: '100vh',
          position: 'relative',
          overflow: 'hidden',
          background: 'var(--bg-primary)',
        }}
      >
      {/* 3D Scene — full viewport */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
        }}
      >
        <Scene vehiclesRef={vehiclesRef} road={road} />
      </div>

      {/* UI Overlay — floating above the canvas */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
        }}
      >
        <Dashboard
          connected={connected}
          telemetry={telemetry}
          telemetryHistory={telemetryHistory}
          sendConfig={sendConfig}
          road={road}
        />
      </div>

      {/* Watermark */}
      <div
        style={{
          position: 'absolute',
          bottom: '12px',
          right: '16px',
          fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
          opacity: 0.5,
          pointerEvents: 'none',
        }}
      >
        IDM + MOBIL Traffic Sim
      </div>

      <OnboardingModal />
      </div>
    </ErrorBoundary>
  );
}
