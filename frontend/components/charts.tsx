import type { CSSProperties } from "react";

type ChartPoint = {
  label: string;
  value: number;
};

export function ChartCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-sm text-slate-500">{description}</p>
      <div className="mt-4">{children}</div>
    </div>
  );
}

export function LineChart({
  data,
  color = "#2563eb",
}: {
  data: ChartPoint[];
  color?: string;
}) {
  if (data.length === 0) {
    return <p className="text-sm text-slate-400">No data available yet.</p>;
  }

  if (data.length === 1) {
    return (
      <div className="rounded-lg bg-slate-50 px-3 py-4 text-sm text-slate-600">
        {data[0].label}: {data[0].value.toFixed(1)}
      </div>
    );
  }

  const width = 320;
  const height = 120;
  const padding = 16;
  const values = data.map((point) => point.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const valueRange = maxValue - minValue || 1;

  const points = data
    .map((point, index) => {
      const x = padding + (index * (width - padding * 2)) / (data.length - 1);
      const y =
        height -
        padding -
        ((point.value - minValue) / valueRange) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-32 w-full overflow-visible">
        <polyline
          fill="none"
          points={points}
          stroke={color}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="3"
        />
        {data.map((point, index) => {
          const x = padding + (index * (width - padding * 2)) / (data.length - 1);
          const y =
            height -
            padding -
            ((point.value - minValue) / valueRange) * (height - padding * 2);
          return <circle key={point.label} cx={x} cy={y} r="3.5" fill={color} />;
        })}
      </svg>
      <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 sm:grid-cols-4">
        {data.map((point) => (
          <div key={point.label} className="rounded-lg bg-slate-50 px-2 py-1.5">
            <span className="font-medium text-slate-700">{point.label}</span>
            <div>{point.value.toFixed(1)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ComparisonBarChart({
  data,
}: {
  data: ChartPoint[];
}) {
  if (data.length === 0) {
    return <p className="text-sm text-slate-400">No comparison data available yet.</p>;
  }

  const maxMagnitude = Math.max(...data.map((point) => Math.abs(point.value)), 1);

  return (
    <div className="space-y-3">
      {data.map((point) => {
        const width = `${Math.max((Math.abs(point.value) / maxMagnitude) * 100, 6)}%`;
        const barStyle = { width } as CSSProperties;

        return (
          <div key={point.label}>
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="font-medium text-slate-700">{point.label}</span>
              <span className={point.value >= 0 ? "text-emerald-700" : "text-rose-700"}>
                {point.value >= 0 ? "+" : ""}
                {point.value.toFixed(1)}
              </span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full ${
                  point.value >= 0 ? "bg-emerald-500" : "bg-rose-500"
                }`}
                style={barStyle}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
