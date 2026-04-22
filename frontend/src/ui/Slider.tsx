import { useCallback, useRef } from 'react';

interface SliderProps {
  id: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  accentColor?: string;
  onChange: (value: number) => void;
}

/**
 * Custom styled range slider with debounced WebSocket-safe onChange.
 */
export function Slider({
  id,
  label,
  value,
  min,
  max,
  step,
  unit = '',
  accentColor = 'var(--accent-blue)',
  onChange,
}: SliderProps) {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = parseFloat(e.target.value);

      // Immediate update for visual feedback
      onChange(newValue);

      // Debounce the WebSocket send
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        onChange(newValue);
      }, 100);
    },
    [onChange]
  );

  // Calculate fill percentage for gradient track
  const fillPercent = max === min ? 100 : ((value - min) / (max - min)) * 100;

  return (
    <div className="slider-container" style={{ marginBottom: '16px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px',
        }}
      >
        <label
          htmlFor={id}
          style={{
            fontSize: '12px',
            fontWeight: 500,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {label}
        </label>
        <span
          style={{
            fontSize: '13px',
            fontFamily: 'var(--font-mono)',
            fontWeight: 500,
            color: accentColor,
            background: 'rgba(79, 142, 255, 0.1)',
            padding: '2px 8px',
            borderRadius: '4px',
          }}
        >
          {typeof value === 'number' && step < 1 ? value.toFixed(2) : value}
          {unit}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={handleChange}
        style={{
          background: `linear-gradient(to right, ${accentColor} 0%, ${accentColor} ${fillPercent}%, rgba(100, 120, 180, 0.2) ${fillPercent}%, rgba(100, 120, 180, 0.2) 100%)`,
        }}
      />
    </div>
  );
}
