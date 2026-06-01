"use client";

import { useEffect, useMemo, useState } from "react";

type Strategy = "conservative" | "balanced" | "aggressive";

type PlayerInfo = {
  id: string;
  name: string;
  team: string;
  positions: string[];
  price: number;
  projections: { next_3_rounds: number };
};

type SquadMember = PlayerInfo;

type TradePair = {
  out_player_id: string;
  in_player_id: string;
};

type RoundSimulation = {
  round: number;
  trades: TradePair[];
  projected_points_delta: number;
  projected_cash_delta: number;
  bank_after: number;
  risk_score: number;
};

type ScenarioPlan = {
  scenario: Strategy;
  rounds: RoundSimulation[];
  total_projected_points_delta: number;
  total_projected_cash_delta: number;
  avg_risk_score: number;
  bye_coverage_score: number;
  position_flexibility_score: number;
};

type PlannerResponse = {
  planning_horizon: number;
  bye_coverage: {
    round: number;
    available_count: number;
    bye_count: number;
    coverage_ratio: number;
  }[];
  cash_generation: {
    projected_price_change: number;
    projected_cash_generation: number;
    rising_players: string[];
    falling_players: string[];
    avg_breakeven_gap: number;
  };
  squad_structure: {
    dual_position_count: number;
    position_counts: Record<string, number>;
    position_flexibility_score: number;
    squad_balance_score: number;
  };
  scenarios: ScenarioPlan[];
};

const STRATEGIES: Strategy[] = ["conservative", "balanced", "aggressive"];

function formatCash(amount: number): string {
  return `${amount >= 0 ? "+" : "-"}$${Math.abs(amount).toLocaleString()}`;
}

export default function PlannerPage() {
  const baseUrl =
    typeof window !== "undefined"
      ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000")
      : "http://localhost:8000";

  const [allPlayers, setAllPlayers] = useState<PlayerInfo[]>([]);
  const [squad, setSquad] = useState<SquadMember[]>([]);
  const [search, setSearch] = useState("");
  const [bank, setBank] = useState(150000);
  const [tradesAvailable, setTradesAvailable] = useState<1 | 2 | 3>(2);
  const [boostsAvailable, setBoostsAvailable] = useState(1);
  const [strategy, setStrategy] = useState<Strategy>("balanced");
  const [compareAll, setCompareAll] = useState(true);
  const [horizon, setHorizon] = useState<1 | 2 | 3 | 4 | 5 | 6>(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlannerResponse | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`${baseUrl}/players/analytics`);
        if (!res.ok) throw new Error("Failed to load players data.");
        setAllPlayers((await res.json()) as PlayerInfo[]);
      } catch {
        setLoadError("Could not load players. Start backend to use planner.");
      }
    };
    void load();
  }, [baseUrl]);

  const playerIndex = useMemo(
    () => new Map(allPlayers.map((player) => [player.id, player])),
    [allPlayers],
  );

  const squadIds = useMemo(() => new Set(squad.map((member) => member.id)), [squad]);
  const filteredPlayers = useMemo(
    () =>
      allPlayers.filter((player) => {
        if (squadIds.has(player.id)) return false;
        const query = search.toLowerCase();
        return (
          !query ||
          player.name.toLowerCase().includes(query) ||
          player.team.toLowerCase().includes(query) ||
          player.positions.some((position) =>
            position.toLowerCase().includes(query),
          )
        );
      }),
    [allPlayers, search, squadIds],
  );

  async function handleRunPlanner() {
    if (squad.length === 0) {
      setError("Add at least one player to your squad.");
      return;
    }
    setLoading(true);
    setError(null);
    setPlan(null);
    try {
      const payload = {
        squad: squad.map((member) => member.id),
        bank,
        trades_available: tradesAvailable,
        boosts_available: boostsAvailable,
        strategy,
        planning_horizon: horizon,
        compare_all_scenarios: compareAll,
      };
      const res = await fetch(`${baseUrl}/planner/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Planner request failed (${res.status})`);
      setPlan((await res.json()) as PlannerResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Planner request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-6 py-10">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Planner</h1>
        <p className="mt-1 text-slate-600">
          Build your squad context and simulate scenario-based planning across
          upcoming rounds.
        </p>
      </div>

      {loadError && (
        <p className="rounded border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {loadError}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Squad Builder</h2>
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search players..."
            className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
          />
          <ul className="mt-3 max-h-72 space-y-1 overflow-y-auto">
            {filteredPlayers.map((player) => (
              <li
                key={player.id}
                className="flex items-center justify-between rounded px-2 py-1 hover:bg-slate-50"
              >
                <span className="text-sm">
                  {player.name} · {player.positions.join("/")} · $
                  {player.price.toLocaleString()}
                </span>
                <button
                  onClick={() => setSquad((prev) => [...prev, player])}
                  className="rounded bg-slate-800 px-2 py-1 text-xs text-white hover:bg-slate-700"
                >
                  Add
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Selected Squad ({squad.length})</h2>
          <ul className="mt-3 space-y-2">
            {squad.map((member) => (
              <li
                key={member.id}
                className="flex items-center justify-between rounded border border-slate-100 px-3 py-2 text-sm"
              >
                <span>
                  {member.name} · ${member.price.toLocaleString()}
                </span>
                <button
                  onClick={() =>
                    setSquad((prev) => prev.filter((item) => item.id !== member.id))
                  }
                  className="text-slate-400 hover:text-red-600"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Planner Settings</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
          <input
            type="number"
            min={0}
            value={bank}
            onChange={(event) => setBank(Math.max(0, Number(event.target.value)))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Bank"
          />
          <select
            value={tradesAvailable}
            onChange={(event) => setTradesAvailable(Number(event.target.value) as 1 | 2 | 3)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {[1, 2, 3].map((value) => (
              <option key={value} value={value}>
                {value} trade{value > 1 ? "s" : ""}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={0}
            max={9}
            value={boostsAvailable}
            onChange={(event) =>
              setBoostsAvailable(Math.max(0, Math.min(9, Number(event.target.value))))
            }
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Boosts"
          />
          <select
            value={strategy}
            onChange={(event) => setStrategy(event.target.value as Strategy)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {STRATEGIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select
            value={horizon}
            onChange={(event) =>
              setHorizon(Number(event.target.value) as 1 | 2 | 3 | 4 | 5 | 6)
            }
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {[1, 2, 3, 4, 5, 6].map((value) => (
              <option key={value} value={value}>
                {value} rounds
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={compareAll}
              onChange={(event) => setCompareAll(event.target.checked)}
            />
            Compare all
          </label>
        </div>
        <button
          onClick={() => void handleRunPlanner()}
          disabled={loading}
          className="mt-4 rounded-lg bg-slate-800 px-5 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? "Planning…" : "Run Plan"}
        </button>
      </div>

      {error && (
        <p className="rounded border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {plan && (
        <div className="space-y-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold">Bye Coverage</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-slate-500">
                    <th className="py-1">Round</th>
                    <th className="py-1">Available</th>
                    <th className="py-1">On bye</th>
                    <th className="py-1">Coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.bye_coverage.map((round) => (
                    <tr key={round.round} className="border-t border-slate-100">
                      <td className="py-1">{round.round}</td>
                      <td className="py-1">{round.available_count}</td>
                      <td className="py-1">{round.bye_count}</td>
                      <td className="py-1">{(round.coverage_ratio * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold">Cash & Price Outlook</h2>
              <p className="mt-2 text-sm text-slate-600">
                Net price move: {formatCash(plan.cash_generation.projected_price_change)}
              </p>
              <p className="text-sm text-slate-600">
                Cash generation:{" "}
                {formatCash(plan.cash_generation.projected_cash_generation)}
              </p>
              <p className="text-sm text-slate-600">
                Avg BE gap: {plan.cash_generation.avg_breakeven_gap.toFixed(2)}
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold">Structure & Flexibility</h2>
              <p className="mt-2 text-sm text-slate-600">
                Dual-position players: {plan.squad_structure.dual_position_count}
              </p>
              <p className="text-sm text-slate-600">
                Flexibility score:{" "}
                {plan.squad_structure.position_flexibility_score.toFixed(2)}
              </p>
              <p className="text-sm text-slate-600">
                Balance score: {plan.squad_structure.squad_balance_score.toFixed(2)}
              </p>
            </div>
          </div>

          {plan.scenarios.map((scenarioPlan) => (
            <div
              key={scenarioPlan.scenario}
              className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <h2 className="text-lg font-semibold capitalize">
                {scenarioPlan.scenario} scenario
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {scenarioPlan.total_projected_points_delta >= 0 ? "+" : ""}
                {scenarioPlan.total_projected_points_delta.toFixed(1)} projected
                points · {formatCash(scenarioPlan.total_projected_cash_delta)} cash
                impact · risk {scenarioPlan.avg_risk_score.toFixed(2)}
              </p>
              <div className="mt-3 space-y-2">
                {scenarioPlan.rounds.map((round) => (
                  <div
                    key={`${scenarioPlan.scenario}-${round.round}`}
                    className="rounded border border-slate-100 bg-slate-50 p-3 text-sm"
                  >
                    <p className="font-medium">Round {round.round}</p>
                    <p className="text-slate-600">
                      Points: {round.projected_points_delta.toFixed(1)} · Cash:{" "}
                      {formatCash(round.projected_cash_delta)} · Bank: $
                      {round.bank_after.toLocaleString()}
                    </p>
                    {round.trades.length > 0 && (
                      <ul className="mt-1 list-disc pl-4 text-slate-600">
                        {round.trades.map((trade, index) => (
                          <li key={index}>
                            OUT{" "}
                            {playerIndex.get(trade.out_player_id)?.name ??
                              trade.out_player_id}{" "}
                            → IN{" "}
                            {playerIndex.get(trade.in_player_id)?.name ??
                              trade.in_player_id}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
