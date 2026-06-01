"use client";

import { useEffect, useState } from "react";

const samplePayload = {
  squad: ["P1", "P2", "P3"],
  bank: 124000,
  trades_available: 2,
  boosts_available: 1,
  strategy: "balanced",
  locked_players: ["P1"],
  must_sell: ["P3"],
};

const formula = `trade_score =
  (0.45 * projected_points_next_3)
+ (0.25 * projected_points_next_6)
+ (0.15 * cash_generation_score)
+ (0.10 * bye_coverage_score)
+ (0.05 * position_flex_score)
- (0.20 * role_risk)
- (0.15 * injury_risk)
- (0.10 * job_security_risk)`;

type PlayerAnalytics = {
  id: string;
  name: string;
  price: number;
  rolling_scores: { last_3: number | null };
  projections: { next_3_rounds: number };
};

export default function TradeLabPage() {
  const [topTargets, setTopTargets] = useState<PlayerAnalytics[]>([]);

  useEffect(() => {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    const load = async () => {
      try {
        const response = await fetch(`${baseUrl}/players/analytics`);
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as PlayerAnalytics[];
        setTopTargets(
          payload
            .slice()
            .sort((a, b) => b.projections.next_3_rounds - a.projections.next_3_rounds)
            .slice(0, 3),
        );
      } catch {
        // Keep Trade Lab available even when analytics feed is unavailable.
      }
    };

    void load();
  }, []);

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Trade Lab</h1>
        <p className="mt-2 text-slate-600">
          Supports best single, double, and triple trade recommendation paths.
        </p>

        <h2 className="mt-6 text-lg font-semibold">Example request payload</h2>
        <pre className="mt-2 overflow-x-auto rounded-md bg-slate-900 p-4 text-sm text-slate-100">
          {JSON.stringify(samplePayload, null, 2)}
        </pre>

        <h2 className="mt-6 text-lg font-semibold">Scoring framework</h2>
        <pre className="mt-2 overflow-x-auto rounded-md bg-slate-900 p-4 text-sm text-slate-100">
          {formula}
        </pre>

        <h2 className="mt-6 text-lg font-semibold">Top projected targets (next 3 rounds)</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">
          {topTargets.map((player) => (
            <li key={player.id}>
              {player.name}: {player.projections.next_3_rounds.toFixed(1)} pts, $
              {player.price.toLocaleString()}, rolling 3-game avg {player.rolling_scores.last_3 ?? "-"}
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
