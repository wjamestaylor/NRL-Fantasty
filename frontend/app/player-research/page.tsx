"use client";

import { useEffect, useState } from "react";

type PlayerAnalytics = {
  id: string;
  name: string;
  price: number;
  season_average: number;
  rolling_scores: { last_3: number | null; last_5: number | null };
  minutes: { recent: number[]; average: number | null };
  projections: { next_3_rounds: number; next_6_rounds: number };
};

export default function PlayerResearchPage() {
  const [players, setPlayers] = useState<PlayerAnalytics[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    const load = async () => {
      try {
        const response = await fetch(`${baseUrl}/players/analytics`);
        if (!response.ok) {
          throw new Error("Failed to load player analytics");
        }
        setPlayers((await response.json()) as PlayerAnalytics[]);
      } catch {
        setError("Player analytics feed unavailable. Start backend to view enriched stats.");
      }
    };

    void load();
  }, []);

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Player Research</h1>
        <p className="mt-2 text-slate-600">
          Enriched analytics including price history, rolling scores, minutes, and projections.
        </p>

        {error ? (
          <p className="mt-4 text-sm text-amber-700">{error}</p>
        ) : (
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-left text-sm text-slate-700">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="pb-2 pr-4">Player</th>
                  <th className="pb-2 pr-4">Price</th>
                  <th className="pb-2 pr-4">Season Avg</th>
                  <th className="pb-2 pr-4">Rolling (3/5)</th>
                  <th className="pb-2 pr-4">Minutes Avg</th>
                  <th className="pb-2 pr-4">Proj (3/6)</th>
                </tr>
              </thead>
              <tbody>
                {players.map((player) => (
                  <tr key={player.id} className="border-t border-slate-100">
                    <td className="py-2 pr-4 font-medium">{player.name}</td>
                    <td className="py-2 pr-4">${player.price.toLocaleString()}</td>
                    <td className="py-2 pr-4">{player.season_average.toFixed(1)}</td>
                    <td className="py-2 pr-4">
                      {player.rolling_scores.last_3 ?? "-"} / {player.rolling_scores.last_5 ?? "-"}
                    </td>
                    <td className="py-2 pr-4">{player.minutes.average ?? "-"}</td>
                    <td className="py-2 pr-4">
                      {player.projections.next_3_rounds.toFixed(1)} /{" "}
                      {player.projections.next_6_rounds.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
