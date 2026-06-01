"use client";

import { useEffect, useState } from "react";

type SourceHealth = {
  status: string;
  dataset: string;
  source: string;
  record_count?: number;
  ingested_at?: string;
  last_error?: string;
  breakeven_status?: string;
  breakeven_reason?: string;
  breakeven_coverage?: string;
};

type Alert = {
  source: string;
  type: string;
  message: string;
};

type DataSourceHealth = {
  status: string;
  loaded_at: string;
  alerts: Alert[];
  sources: Record<string, SourceHealth>;
  features?: {
    player_breakeven?: {
      enabled?: boolean;
      reason?: string;
      coverage?: string;
    };
  };
};

type IngestionLogEntry = {
  timestamp: string;
  source: string;
  status: string;
  record_count: number;
  error?: string;
};

const STATUS_BADGE: Record<string, string> = {
  live: "bg-green-100 text-green-800",
  snapshot: "bg-blue-100 text-blue-800",
  snapshot_fallback: "bg-yellow-100 text-yellow-800",
  not_configured: "bg-slate-100 text-slate-500",
};

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_BADGE[status] ?? "bg-slate-100 text-slate-500";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export default function SystemHealthPage() {
  const [health, setHealth] = useState<DataSourceHealth | null>(null);
  const [log, setLog] = useState<IngestionLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    const load = async () => {
      try {
        const [healthRes, logRes] = await Promise.all([
          fetch(`${baseUrl}/health/data-sources`),
          fetch(`${baseUrl}/health/ingestion-log?limit=50`),
        ]);

        if (!healthRes.ok) {
          throw new Error("Health endpoint unavailable");
        }

        setHealth((await healthRes.json()) as DataSourceHealth);

        if (logRes.ok) {
          const entries = (await logRes.json()) as IngestionLogEntry[];
          setLog([...entries].reverse());
        }
      } catch {
        setError("Data pipeline monitoring unavailable. Start backend to view system health.");
      }
    };

    void load();
  }, []);

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10 space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">System Health</h1>
        <p className="mt-1 text-slate-600">
          Data ingestion pipeline status and audit log for system integrators.
        </p>

        {error ? (
          <p className="mt-4 text-sm text-amber-700">{error}</p>
        ) : health ? (
          <>
            {/* Overall status */}
            <div className="mt-4 flex items-center gap-3">
              <span className="text-sm font-medium text-slate-700">Overall status:</span>
              <span
                className={`rounded px-2 py-0.5 text-sm font-semibold ${
                  health.status === "ok"
                    ? "bg-green-100 text-green-800"
                    : "bg-red-100 text-red-800"
                }`}
              >
                {health.status.toUpperCase()}
              </span>
              <span className="text-xs text-slate-400">
                Last loaded: {new Date(health.loaded_at).toLocaleString()}
              </span>
            </div>

            {/* Alerts */}
            {health.alerts.length > 0 && (
              <div className="mt-4 space-y-2">
                <h2 className="text-sm font-semibold text-red-700">Active Alerts</h2>
                {health.alerts.map((alert, i) => (
                  <div
                    key={i}
                    className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
                  >
                    <span className="font-semibold">[{alert.type}]</span> {alert.message}
                  </div>
                ))}
              </div>
            )}

            {/* Breakeven feature flag */}
            {health.features?.player_breakeven && (
              <div className="mt-4">
                <h2 className="text-sm font-semibold text-slate-700">Feature Flags</h2>
                <div className="mt-2 text-sm text-slate-600">
                  <span className="font-medium">Player Breakeven:</span>{" "}
                  {health.features.player_breakeven.enabled ? (
                    <span className="text-green-700">Enabled</span>
                  ) : (
                    <span className="text-slate-500">
                      Disabled — {health.features.player_breakeven.reason ?? "unknown reason"}{" "}
                      {health.features.player_breakeven.coverage
                        ? `(${health.features.player_breakeven.coverage} coverage)`
                        : null}
                    </span>
                  )}
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="mt-4 text-sm text-slate-400">Loading…</p>
        )}
      </div>

      {/* Source health table */}
      {health && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Data Sources</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm text-slate-700">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="pb-2 pr-4">Source</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Records</th>
                  <th className="pb-2 pr-4">Last Ingested</th>
                  <th className="pb-2 pr-4">Last Error</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(health.sources).map(([name, info]) => (
                  <tr key={name} className="border-t border-slate-100">
                    <td className="py-2 pr-4 font-medium">{name}</td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={info.status} />
                    </td>
                    <td className="py-2 pr-4">
                      {info.record_count !== undefined ? info.record_count : "—"}
                    </td>
                    <td className="py-2 pr-4 text-slate-500">
                      {info.ingested_at
                        ? new Date(info.ingested_at).toLocaleString()
                        : "—"}
                    </td>
                    <td className="py-2 pr-4 text-xs text-red-600 max-w-xs truncate">
                      {info.last_error ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Ingestion audit log */}
      {log.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Ingestion Audit Log</h2>
          <p className="mt-1 text-xs text-slate-500">Most recent 50 events, newest first.</p>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm text-slate-700">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="pb-2 pr-4">Timestamp</th>
                  <th className="pb-2 pr-4">Source</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Records</th>
                  <th className="pb-2 pr-4">Error</th>
                </tr>
              </thead>
              <tbody>
                {log.map((entry, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="py-2 pr-4 text-slate-500 whitespace-nowrap">
                      {new Date(entry.timestamp).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4 font-medium">{entry.source}</td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={entry.status} />
                    </td>
                    <td className="py-2 pr-4">{entry.record_count}</td>
                    <td className="py-2 pr-4 text-xs text-red-600 max-w-xs truncate">
                      {entry.error ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
}
