"use client";

import { useEffect, useMemo, useState } from "react";

import { ChartCard, ComparisonBarChart, LineChart } from "@/components/charts";
import { getApiBaseUrl } from "@/lib/api";

type PlayerAnalytics = {
  id: string;
  name: string;
  team: string;
  positions: string[];
  price: number;
  price_history: { round: number; price: number }[];
  season_average: number;
  rolling_scores: { last_3: number | null; last_5: number | null };
  minutes: { recent: number[]; average: number | null };
  projections: { next_round: number; next_3_rounds: number; next_6_rounds: number };
};

type DataSourceHealth = {
  features?: { player_breakeven?: { enabled?: boolean } };
};

export default function PlayerResearchPage() {
  const [players, setPlayers] = useState<PlayerAnalytics[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [breakevenAvailable, setBreakevenAvailable] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [analyticsResponse, healthResponse] = await Promise.all([
          fetch(`${getApiBaseUrl()}/players/analytics`),
          fetch(`${getApiBaseUrl()}/health/data-sources`),
        ]);

        if (!analyticsResponse.ok) {
          throw new Error("Failed to load player analytics");
        }

        const analytics = (await analyticsResponse.json()) as PlayerAnalytics[];
        setPlayers(analytics);
        setSelectedId((current) => current || analytics[0]?.id || "");

        if (healthResponse.ok) {
          const healthPayload = (await healthResponse.json()) as DataSourceHealth;
          setBreakevenAvailable(healthPayload.features?.player_breakeven?.enabled === true);
        }
      } catch {
        setError("Player analytics feed unavailable. Start backend to view enriched stats.");
      }
    };

    void load();
  }, []);

  const selectedPlayer = useMemo(
    () => players.find((player) => player.id === selectedId) ?? players[0] ?? null,
    [players, selectedId],
  );

  const priceTrend = selectedPlayer?.price_history.map((point) => ({
    label: `R${point.round}`,
    value: point.price,
  })) ?? [];

  const minutesTrend =
    selectedPlayer?.minutes.recent.map((value, index) => ({
      label: `G${index + 1}`,
      value,
    })) ?? [];

  const projectionComparison = selectedPlayer
    ? [
        { label: "Next round", value: selectedPlayer.projections.next_round },
        { label: "Next 3 rounds", value: selectedPlayer.projections.next_3_rounds },
        { label: "Next 6 rounds", value: selectedPlayer.projections.next_6_rounds },
      ]
    : [];

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 sm:py-10">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">Player Research</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
              Enriched analytics for price trends, rolling scores, minutes, and short-term
              projections.
            </p>
          </div>
          <label className="block text-sm font-medium text-slate-600">
            Focus player
            <select
              value={selectedPlayer?.id ?? ""}
              onChange={(event) => setSelectedId(event.target.value)}
              className="mt-2 w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-slate-400 focus:outline-none lg:min-w-72"
            >
              {players.map((player) => (
                <option key={player.id} value={player.id}>
                  {player.name} · {player.team}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {error ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {error}
        </p>
      ) : null}

      {selectedPlayer ? (
        <>
          <section className="grid gap-4 lg:grid-cols-[1.2fr,0.8fr]">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">
                Player snapshot
              </p>
              <h2 className="mt-2 text-2xl font-bold text-slate-900">{selectedPlayer.name}</h2>
              <p className="mt-2 text-sm text-slate-600">
                {selectedPlayer.team} · {selectedPlayer.positions.join("/")} · $
                {selectedPlayer.price.toLocaleString()}
              </p>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                    Season avg
                  </p>
                  <p className="mt-2 text-2xl font-bold text-slate-900">
                    {selectedPlayer.season_average.toFixed(1)}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                    Rolling form
                  </p>
                  <p className="mt-2 text-2xl font-bold text-slate-900">
                    {selectedPlayer.rolling_scores.last_3 ?? "-"}
                    <span className="text-base font-medium text-slate-500"> / {selectedPlayer.rolling_scores.last_5 ?? "-"}</span>
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                    Minutes avg
                  </p>
                  <p className="mt-2 text-2xl font-bold text-slate-900">
                    {selectedPlayer.minutes.average?.toFixed(1) ?? "-"}
                  </p>
                </div>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">Decision support</h2>
              <ul className="mt-4 space-y-3 text-sm text-slate-600">
                <li>• Price history highlights momentum and cash-generation opportunity.</li>
                <li>• Minutes trend helps identify role stability before you buy in.</li>
                <li>• Projection charts compare immediate and medium-term value.</li>
                {!breakevenAvailable ? (
                  <li>• Breakeven data will appear once full source coverage is available.</li>
                ) : null}
              </ul>
            </div>
          </section>

          <section className="grid gap-4 xl:grid-cols-3">
            <ChartCard
              title="Price trend"
              description="Recent price history by round."
            >
              <LineChart data={priceTrend} />
            </ChartCard>
            <ChartCard
              title="Recent minutes"
              description="Last five games to flag role volatility."
            >
              <ComparisonBarChart data={minutesTrend} />
            </ChartCard>
            <ChartCard
              title="Projection outlook"
              description="Short-term and multi-round scoring expectations."
            >
              <ComparisonBarChart data={projectionComparison} />
            </ChartCard>
          </section>
        </>
      ) : null}

      {!error ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900">Player list</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-[720px] text-left text-sm text-slate-700">
              <thead className="text-xs uppercase tracking-[0.15em] text-slate-500">
                <tr>
                  <th className="pb-3 pr-4">Player</th>
                  <th className="pb-3 pr-4">Price</th>
                  <th className="pb-3 pr-4">Season Avg</th>
                  <th className="pb-3 pr-4">Rolling (3/5)</th>
                  <th className="pb-3 pr-4">Minutes Avg</th>
                  <th className="pb-3 pr-4">Proj (1/3/6)</th>
                </tr>
              </thead>
              <tbody>
                {players.map((player) => (
                  <tr
                    key={player.id}
                    className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                    onClick={() => setSelectedId(player.id)}
                  >
                    <td className="py-3 pr-4 font-medium text-slate-900">{player.name}</td>
                    <td className="py-3 pr-4">${player.price.toLocaleString()}</td>
                    <td className="py-3 pr-4">{player.season_average.toFixed(1)}</td>
                    <td className="py-3 pr-4">
                      {player.rolling_scores.last_3 ?? "-"} / {player.rolling_scores.last_5 ?? "-"}
                    </td>
                    <td className="py-3 pr-4">
                      {typeof player.minutes.average === "number"
                        ? player.minutes.average.toFixed(1)
                        : "-"}
                    </td>
                    <td className="py-3 pr-4">
                      {player.projections.next_round.toFixed(1)} / {" "}
                      {player.projections.next_3_rounds.toFixed(1)} / {" "}
                      {player.projections.next_6_rounds.toFixed(1)}
                    </td>
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
