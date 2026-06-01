"use client";

import { useEffect, useMemo, useState } from "react";

import { ChartCard, ComparisonBarChart, LineChart } from "@/components/charts";
import { SavedTeamsPanel } from "@/components/saved-teams-panel";
import { getApiBaseUrl, parseApiError } from "@/lib/api";
import type { SavedTeamPayload, Strategy } from "@/lib/team";

type PlayerInfo = {
  id: string;
  name: string;
  team: string;
  positions: string[];
  price: number;
};

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

function clampTrades(value: number): 1 | 2 | 3 {
  if (value <= 1) return 1;
  if (value >= 3) return 3;
  return 2;
}

export default function PlannerPage() {
  const [allPlayers, setAllPlayers] = useState<PlayerInfo[]>([]);
  const [squad, setSquad] = useState<PlayerInfo[]>([]);
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
        const response = await fetch(`${getApiBaseUrl()}/players/analytics`);
        if (!response.ok) {
          throw new Error("Failed to load players data.");
        }
        setAllPlayers((await response.json()) as PlayerInfo[]);
      } catch {
        setLoadError("Could not load players. Start backend to use planner.");
      }
    };

    void load();
  }, []);

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
          player.positions.some((position) => position.toLowerCase().includes(query))
        );
      }),
    [allPlayers, search, squadIds],
  );

  const savedTeamPayload = useMemo<SavedTeamPayload>(
    () => ({
      squad: squad.map((member) => member.id),
      bank,
      trades_available: tradesAvailable,
      boosts_available: boostsAvailable,
      strategy,
      planning_horizon: horizon,
      compare_all_scenarios: compareAll,
    }),
    [bank, boostsAvailable, compareAll, horizon, squad, strategy, tradesAvailable],
  );

  const activeScenario = useMemo(
    () => plan?.scenarios.find((scenarioPlan) => scenarioPlan.scenario === strategy) ?? plan?.scenarios[0] ?? null,
    [plan, strategy],
  );

  const byeCoverageTrend =
    plan?.bye_coverage.map((round) => ({
      label: `R${round.round}`,
      value: round.coverage_ratio * 100,
    })) ?? [];

  const scenarioComparison =
    plan?.scenarios.map((scenarioPlan) => ({
      label: scenarioPlan.scenario,
      value: scenarioPlan.total_projected_points_delta,
    })) ?? [];

  const bankTrend =
    activeScenario?.rounds.map((round) => ({
      label: `R${round.round}`,
      value: round.bank_after,
    })) ?? [];

  function applySavedTeam(payload: SavedTeamPayload) {
    setBank(payload.bank);
    setTradesAvailable(clampTrades(payload.trades_available));
    setBoostsAvailable(payload.boosts_available);
    setStrategy(payload.strategy);
    setHorizon((payload.planning_horizon as 1 | 2 | 3 | 4 | 5 | 6) ?? 3);
    setCompareAll(payload.compare_all_scenarios ?? false);
    setPlan(null);
    setError(null);

    const nextSquad = payload.squad
      .map((playerId) => playerIndex.get(playerId))
      .filter((player): player is PlayerInfo => Boolean(player));
    setSquad(nextSquad);
  }

  async function handleRunPlanner() {
    if (squad.length === 0) {
      setError("Add at least one player to your squad.");
      return;
    }

    setLoading(true);
    setError(null);
    setPlan(null);

    try {
      const response = await fetch(`${getApiBaseUrl()}/planner/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(savedTeamPayload),
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      setPlan((await response.json()) as PlannerResponse);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Planner request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 sm:py-10">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">Planner</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
          Build squad context, save scenarios, and compare multi-round planning with charts
          for bye coverage, points, and cash flow.
        </p>
      </section>

      {loadError ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {loadError}
        </p>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Squad builder</h2>
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by name, team, or position"
              className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            />
            <ul className="mt-3 max-h-80 space-y-1 overflow-y-auto">
              {filteredPlayers.map((player) => (
                <li
                  key={player.id}
                  className="flex items-center justify-between gap-3 rounded-lg px-2 py-2 hover:bg-slate-50"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900">{player.name}</p>
                    <p className="text-xs text-slate-500">
                      {player.team} · {player.positions.join("/")} · ${player.price.toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => setSquad((current) => [...current, player])}
                    className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
                  >
                    Add
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Selected squad ({squad.length})</h2>
            <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto">
              {squad.length === 0 ? (
                <li className="text-sm text-slate-400">Add players to start planning.</li>
              ) : (
                squad.map((member) => (
                  <li
                    key={member.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-slate-900">{member.name}</p>
                      <p className="text-xs text-slate-500">${member.price.toLocaleString()}</p>
                    </div>
                    <button
                      onClick={() =>
                        setSquad((current) => current.filter((item) => item.id !== member.id))
                      }
                      className="rounded-lg px-2 py-1 text-slate-400 hover:bg-rose-50 hover:text-rose-700"
                    >
                      ✕
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>

        <SavedTeamsPanel payload={savedTeamPayload} onLoad={applySavedTeam} />
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-semibold text-slate-900">Planner settings</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
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
            onChange={(event) => setTradesAvailable(clampTrades(Number(event.target.value)))}
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
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm capitalize"
          >
            {STRATEGIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <select
            value={horizon}
            onChange={(event) => setHorizon(Number(event.target.value) as 1 | 2 | 3 | 4 | 5 | 6)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {[1, 2, 3, 4, 5, 6].map((value) => (
              <option key={value} value={value}>
                {value} rounds
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={compareAll}
              onChange={(event) => setCompareAll(event.target.checked)}
            />
            Compare all scenarios
          </label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={() => void handleRunPlanner()}
            disabled={loading}
            className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {loading ? "Planning…" : "Run plan"}
          </button>
          <p className="text-sm text-slate-500">Best on mobile: save a setup, then reload and compare scenarios.</p>
        </div>
      </section>

      {error ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </p>
      ) : null}

      {plan ? (
        <>
          <section className="grid gap-4 xl:grid-cols-3">
            <ChartCard title="Bye coverage trend" description="Coverage ratio across the planning horizon.">
              <LineChart data={byeCoverageTrend} color="#0f766e" />
            </ChartCard>
            <ChartCard title="Scenario comparison" description="Projected points delta by strategy.">
              <ComparisonBarChart data={scenarioComparison} />
            </ChartCard>
            <ChartCard
              title="Bank path"
              description={`Round-by-round bank under the ${activeScenario?.scenario ?? strategy} scenario.`}
            >
              <LineChart data={bankTrend} color="#7c3aed" />
            </ChartCard>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">Cash & price outlook</h2>
              <p className="mt-3 text-sm text-slate-600">
                Net price move: {formatCash(plan.cash_generation.projected_price_change)}
              </p>
              <p className="text-sm text-slate-600">
                Cash generation: {formatCash(plan.cash_generation.projected_cash_generation)}
              </p>
              <p className="text-sm text-slate-600">
                Avg breakeven gap: {plan.cash_generation.avg_breakeven_gap.toFixed(2)}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">Structure & flexibility</h2>
              <p className="mt-3 text-sm text-slate-600">
                Dual-position players: {plan.squad_structure.dual_position_count}
              </p>
              <p className="text-sm text-slate-600">
                Flexibility score: {plan.squad_structure.position_flexibility_score.toFixed(2)}
              </p>
              <p className="text-sm text-slate-600">
                Balance score: {plan.squad_structure.squad_balance_score.toFixed(2)}
              </p>
            </div>
          </section>

          {plan.scenarios.map((scenarioPlan) => (
            <section
              key={scenarioPlan.scenario}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
            >
              <h2 className="text-xl font-semibold capitalize text-slate-900">
                {scenarioPlan.scenario} scenario
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                {scenarioPlan.total_projected_points_delta >= 0 ? "+" : ""}
                {scenarioPlan.total_projected_points_delta.toFixed(1)} projected points · {" "}
                {formatCash(scenarioPlan.total_projected_cash_delta)} cash impact · risk {" "}
                {scenarioPlan.avg_risk_score.toFixed(2)}
              </p>
              <div className="mt-4 grid gap-3">
                {scenarioPlan.rounds.map((round) => (
                  <div key={`${scenarioPlan.scenario}-${round.round}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <p className="font-semibold text-slate-900">Round {round.round}</p>
                      <p className="text-sm text-slate-600">
                        Points {round.projected_points_delta.toFixed(1)} · Cash {formatCash(round.projected_cash_delta)} · Bank ${round.bank_after.toLocaleString()}
                      </p>
                    </div>
                    {round.trades.length > 0 ? (
                      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">
                        {round.trades.map((trade, index) => (
                          <li key={index}>
                            OUT {playerIndex.get(trade.out_player_id)?.name ?? trade.out_player_id} → IN {playerIndex.get(trade.in_player_id)?.name ?? trade.in_player_id}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-3 text-sm text-slate-500">No trades required in this round.</p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          ))}
        </>
      ) : null}
    </main>
  );
}
