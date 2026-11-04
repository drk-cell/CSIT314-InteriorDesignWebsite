interface BudgetSliderProps {
  min: number;
  max: number;
  step: number;
  low: number;
  high: number;
  onChange: (low: number, high: number) => void;
}

/**
 * One track, two handles. The handles can meet but not cross.
 */
export default function BudgetSlider({
  min,
  max,
  step,
  low,
  high,
  onChange,
}: BudgetSliderProps) {
  const span = max - min;
  const lowPercent = span === 0 ? 0 : ((low - min) / span) * 100;
  const highPercent = span === 0 ? 100 : ((high - min) / span) * 100;

  return (
    <div className="range">
      <div className="range-track" aria-hidden="true" />
      <div
        className="range-fill"
        aria-hidden="true"
        style={{ left: `${lowPercent}%`, width: `${highPercent - lowPercent}%` }}
      />
      <input
        type="range"
        aria-label="Minimum budget"
        min={min}
        max={max}
        step={step}
        value={low}
        onChange={(event) => {
          const next = Number(event.target.value);
          onChange(Math.min(next, high - step), high);
        }}
      />
      <input
        type="range"
        aria-label="Maximum budget"
        min={min}
        max={max}
        step={step}
        value={high}
        onChange={(event) => {
          const next = Number(event.target.value);
          onChange(low, Math.max(next, low + step));
        }}
      />
    </div>
  );
}