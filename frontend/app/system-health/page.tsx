"use client";

import { useEffect, useState } from "react";

import { getApiBaseUrl } from "@/lib/api";

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

type ProbeStatus = {
  status: string;
  loaded_at?: string;
  player_count?: number;
  fixture_count?: number;
  news_count?: number;
};

const STATUS_BADGE: Record<string, string> = {
  live: "bg-emerald-100 text-emerald-800",
  ready: "bg-emerald-100 text-emerald-800",
  snapshot: "bg-blue-100 text-blue-800",
  snapshot_fallback: "bg-amber-100 text-amber-800",
  not_configured: "bg-slate-100 text-slate-500",
};

function StatusBadge({ status }: { status: string }) {
  const className = STATUS_BADGE[status] ?? "bg-slate-100 text-slate-500";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${className}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export default function SystemHealthPage() {
  const [health, setHealth] = useState<DataSourceHealth | null>(null);
  const [log, setLog] = useState<IngestionLogEntry[]>([]);
  const [liveProbe, setLiveProbe] = useState<ProbeStatus | null>(null);
  const [readyProbe, setReadyProbe] = useState<ProbeStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [healthResponse, logResponse, liveResponse, readyResponse] = await Promise.all([
          fetch(`${getApiBaseUrl()}/health/data-sources`),
          fetch(`${getApiBaseUrl()}/health/ingestion-log?limit=50`),
          fetch(`${getApiBaseUrl()}/health/live`),
          fetch(`${getApiBaseUrl()}/health/ready`),
        ]);

        if (!healthResponse.ok) {
          throw new Error("Health endpoint unavailable");
        }

        setHealth((await healthResponse.json()) as DataSourceHealth);

        if (logResponse.ok) {
          const entries = (await logResponse.json()) as IngestionLogEntry[];
          setLog(entries.slice().reverse());
        }

        if (liveResponse.ok) {
          setLiveProbe((await liveResponse.json()) as ProbeStatus);
        }

        if (readyResponse.ok) {
          setReadyProbe((await readyResponse.json()) as ProbeStatus);
        }
      } catch {
        setError("Data pipeline monitoring unavailable. Start backend to view system health.");
      }
    };

    void load();
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 sm:py-10">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">System Health</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
          Data ingestion status, production probes, and audit visibility for deployment and
          monitoring workflows.
        </p>
      </section>

      {error ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {error}
        </p>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Overall pipeline</h2>
          {health ? (
            <div className="mt-4 space-y-2 text-sm text-slate-600">
              <div className="flex items-center gap-3">
                <StatusBadge status={health.status === "ok" ? "live" : health.status} />
                <span>{health.status === "ok" ? "Operational" : health.status}</span>
              </div>
              <p>Last loaded {new Date(health.loaded_at).toLocaleString()}</p>
              <p>{health.alerts.length} active alert{health.alerts.length === 1 ? "" : "s"}</p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-400">Loading health snapshot…</p>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Live probe</h2>
          {liveProbe ? (
            <div className="mt-4 space-y-2 text-sm text-slate-600">
              <StatusBadge status={liveProbe.status} />
              <p>Use /health/live for load balancers and basic uptime checks.</p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-400">Loading live probe…</p>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Ready probe</h2>
          {readyProbe ? (
            <div className="mt-4 space-y-2 text-sm text-slate-600">
              <StatusBadge status={readyProbe.status} />
              <p>{readyProbe.player_count ?? 0} players · {readyProbe.fixture_count ?? 0} fixtures · {readyProbe.news_count ?? 0} news records</p>
              <p>Use /health/ready before routing production traffic.</p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-400">Loading ready probe…</p>
          )}
        </div>
      </section>

      {health?.alerts.length ? (
        <section className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-rose-900">Active alerts</h2>
          <div className="mt-4 space-y-2 text-sm text-rose-800">
            {health.alerts.map((alert, index) => (
              <div key={index} className="rounded-lg border border-rose-200 bg-white px-4 py-3">
                <span className="font-semibold">[{alert.type}]</span> {alert.message}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {health ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900">Data sources</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-[760px] text-left text-sm text-slate-700">
              <thead className="text-xs uppercase tracking-[0.15em] text-slate-500">
                <tr>
                  <th className="pb-3 pr-4">Source</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Records</th>
                  <th className="pb-3 pr-4">Last ingested</th>
                  <th className="pb-3 pr-4">Last error</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(health.sources).map(([name, info]) => (
                  <tr key={name} className="border-t border-slate-100">
                    <td className="py-3 pr-4 font-medium text-slate-900">{name}</td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={info.status} />
                    </td>
                    <td className="py-3 pr-4">{info.record_count ?? "—"}</td>
                    <td className="py-3 pr-4 text-slate-500">
                      {info.ingested_at ? new Date(info.ingested_at).toLocaleString() : "—"}
                    </td>
                    <td className="max-w-xs py-3 pr-4 text-xs text-rose-700">{info.last_error ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {log.length > 0 ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900">Ingestion audit log</h2>
          <p className="mt-1 text-sm text-slate-500">Most recent 50 events, newest first.</p>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-[760px] text-left text-sm text-slate-700">
              <thead className="text-xs uppercase tracking-[0.15em] text-slate-500">
                <tr>
                  <th className="pb-3 pr-4">Timestamp</th>
                  <th className="pb-3 pr-4">Source</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Records</th>
                  <th className="pb-3 pr-4">Error</th>
                </tr>
              </thead>
              <tbody>
                {log.map((entry, index) => (
                  <tr key={index} className="border-t border-slate-100">
                    <td className="py-3 pr-4 text-slate-500">{new Date(entry.timestamp).toLocaleString()}</td>
                    <td className="py-3 pr-4 font-medium text-slate-900">{entry.source}</td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={entry.status} />
                    </td>
                    <td className="py-3 pr-4">{entry.record_count}</td>
                    <td className="max-w-xs py-3 pr-4 text-xs text-rose-700">{entry.error ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </main>
  );
}
