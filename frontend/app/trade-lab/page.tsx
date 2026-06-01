"use client";

import { useEffect, useMemo, useState } from "react";

import { ComparisonBarChart, ChartCard } from "@/components/charts";
import { SavedTeamsPanel } from "@/components/saved-teams-panel";
import { getApiBaseUrl, parseApiError } from "@/lib/api";
import type { SavedTeamPayload, Strategy } from "@/lib/team";

type PlayerInfo = {
  id: string;
  name: string;
  team: string;
  positions: string[];
  price: number;
  season_average: number;
  projections: { next_3_rounds: number };
};

type SquadMember = PlayerInfo & {
  locked: boolean;
  mustSell: boolean;
};

type TradePair = {
  out_player_id: string;
  in_player_id: string;
};

type TradeRecommendation = {
  trade_count: number;
  trades: TradePair[];
  projected_gain_next_3: number;
  projected_gain_next_6: number;
  cash_impact: number;
  bye_coverage_delta: number;
  risk_score: number;
  total_trade_score: number;
  explanation: string;
};

type RecommendationsResponse = {
  recommendations: TradeRecommendation[];
};

const STRATEGY_OPTIONS: { value: Strategy; label: string }[] = [
  { value: "conservative", label: "Conservative" },
  { value: "balanced", label: "Balanced" },
  { value: "aggressive", label: "Aggressive" },
];

const TRADE_COUNT_LABELS: Record<number, string> = {
  1: "Best 1-trade options",
  2: "Best 2-trade options",
  3: "Best 3-trade options",
};

function formatCash(amount: number): string {
  return `${amount >= 0 ? "+" : "-"}$${Math.abs(amount).toLocaleString()}`;
}

function groupByTradeCount(recommendations: TradeRecommendation[]) {
  const grouped = new Map<number, TradeRecommendation[]>();
  for (const recommendation of recommendations) {
    const current = grouped.get(recommendation.trade_count) ?? [];
    current.push(recommendation);
    grouped.set(recommendation.trade_count, current);
  }
  return grouped;
}

function clampTrades(value: number): 1 | 2 | 3 {
  if (value <= 1) return 1;
  if (value >= 3) return 3;
  return 2;
}

function ToggleButton({
  active,
  label,
  color,
  onClick,
}: {
  active: boolean;
  label: string;
  color: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-2.5 py-1 text-xs font-semibold transition ${
        active ? color : "bg-slate-100 text-slate-500 hover:bg-slate-200"
      }`}
    >
      {label}
    </button>
  );
}

function RecommendationCard({
  recommendation,
  playerIndex,
}: {
  recommendation: TradeRecommendation;
  playerIndex: Map<string, PlayerInfo>;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap gap-3 text-sm text-slate-600">
        <span className="font-semibold text-slate-900">
          Score {recommendation.total_trade_score.toFixed(2)}
        </span>
        <span>+3R {recommendation.projected_gain_next_3.toFixed(1)}</span>
        <span>+6R {recommendation.projected_gain_next_6.toFixed(1)}</span>
        <span>Cash {formatCash(recommendation.cash_impact)}</span>
        <span>Risk {recommendation.risk_score.toFixed(2)}</span>
      </div>

      <div className="mt-3 space-y-2 text-sm">
        {recommendation.trades.map((trade, index) => {
          const outPlayer = playerIndex.get(trade.out_player_id);
          const inPlayer = playerIndex.get(trade.in_player_id);
          return (
            <div key={index} className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-rose-100 px-3 py-1 font-medium text-rose-800">
                OUT {outPlayer?.name ?? trade.out_player_id}
              </span>
              <span className="text-slate-400">→</span>
              <span className="rounded-full bg-emerald-100 px-3 py-1 font-medium text-emerald-800">
                IN {inPlayer?.name ?? trade.in_player_id}
              </span>
            </div>
          );
        })}
      </div>

      <p className="mt-3 text-sm leading-6 text-slate-600">{recommendation.explanation}</p>
    </div>
  );
}

export default function TradeLabPage() {
  const [allPlayers, setAllPlayers] = useState<PlayerInfo[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [squad, setSquad] = useState<SquadMember[]>([]);
  const [pickerSearch, setPickerSearch] = useState("");
  const [bank, setBank] = useState(150000);
  const [tradesAvailable, setTradesAvailable] = useState<1 | 2 | 3>(2);
  const [boostsAvailable, setBoostsAvailable] = useState(1);
  const [strategy, setStrategy] = useState<Strategy>("balanced");
  const [recommendations, setRecommendations] = useState<TradeRecommendation[] | null>(null);
  const [recError, setRecError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/players/analytics`);
        if (!response.ok) {
          throw new Error("Failed to load players");
        }
        setAllPlayers((await response.json()) as PlayerInfo[]);
      } catch {
        setLoadError("Could not load player list. Start the backend to enable the squad builder.");
      }
    };

    void load();
  }, []);

  const playerIndex = useMemo(() => {
    const index = new Map(allPlayers.map((player) => [player.id, player]));
    squad.forEach((member) => index.set(member.id, member));
    return index;
  }, [allPlayers, squad]);

  const squadIds = useMemo(() => new Set(squad.map((member) => member.id)), [squad]);

  const filteredPlayers = useMemo(
    () =>
      allPlayers.filter((player) => {
        if (squadIds.has(player.id)) return false;
        const query = pickerSearch.toLowerCase();
        return (
          !query ||
          player.name.toLowerCase().includes(query) ||
          player.team.toLowerCase().includes(query) ||
          player.positions.some((position) => position.toLowerCase().includes(query))
        );
      }),
    [allPlayers, pickerSearch, squadIds],
  );

  const savedTeamPayload = useMemo<SavedTeamPayload>(
    () => ({
      squad: squad.map((member) => member.id),
      bank,
      trades_available: tradesAvailable,
      boosts_available: boostsAvailable,
      strategy,
      locked_players: squad.filter((member) => member.locked).map((member) => member.id),
      must_sell: squad.filter((member) => member.mustSell).map((member) => member.id),
    }),
    [bank, boostsAvailable, squad, strategy, tradesAvailable],
  );

  const groupedRecommendations = recommendations ? groupByTradeCount(recommendations) : null;

  const tradeComparison = recommendations
    ? Array.from(groupByTradeCount(recommendations).entries()).map(([tradeCount, group]) => ({
        label: `${tradeCount} trade${tradeCount > 1 ? "s" : ""}`,
        value: group[0]?.projected_gain_next_3 ?? 0,
      }))
    : [];

  function addToSquad(player: PlayerInfo) {
    setSquad((current) => [...current, { ...player, locked: false, mustSell: false }]);
  }

  function removeFromSquad(playerId: string) {
    setSquad((current) => current.filter((member) => member.id !== playerId));
  }

  function toggleLock(playerId: string) {
    setSquad((current) =>
      current.map((member) =>
        member.id === playerId
          ? { ...member, locked: !member.locked, mustSell: member.locked ? member.mustSell : false }
          : member,
      ),
    );
  }

  function toggleMustSell(playerId: string) {
    setSquad((current) =>
      current.map((member) =>
        member.id === playerId
          ? {
              ...member,
              mustSell: !member.mustSell,
              locked: member.mustSell ? member.locked : false,
            }
          : member,
      ),
    );
  }

  function applySavedTeam(payload: SavedTeamPayload) {
    setBank(payload.bank);
    setTradesAvailable(clampTrades(payload.trades_available));
    setBoostsAvailable(payload.boosts_available);
    setStrategy(payload.strategy);
    setRecommendations(null);
    setRecError(null);

    const locked = new Set(payload.locked_players ?? []);
    const mustSell = new Set(payload.must_sell ?? []);
    const nextSquad = payload.squad
      .map((playerId) => playerIndex.get(playerId))
      .filter((player): player is PlayerInfo => Boolean(player))
      .map((player) => ({
        ...player,
        locked: locked.has(player.id),
        mustSell: mustSell.has(player.id),
      }));
    setSquad(nextSquad);
  }

  async function handleGetRecommendations() {
    if (squad.length === 0) {
      setRecError("Add at least one player to your squad before running recommendations.");
      return;
    }

    setLoading(true);
    setRecError(null);
    setRecommendations(null);

    try {
      const response = await fetch(`${getApiBaseUrl()}/trade/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(savedTeamPayload),
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as RecommendationsResponse;
      setRecommendations(payload.recommendations);
    } catch (error) {
      setRecError(error instanceof Error ? error.message : "Failed to fetch recommendations.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 sm:py-10">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">Trade Lab</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
          Build your squad, save setups to your account, and compare the best one-, two-,
          and three-trade options with mobile-friendly controls.
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
            <p className="mt-1 text-xs text-slate-500">Search and add players to your current squad.</p>
            <input
              type="text"
              placeholder="Search by name, team, or position"
              value={pickerSearch}
              onChange={(event) => setPickerSearch(event.target.value)}
              className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            />
            <ul className="mt-3 max-h-80 space-y-1 overflow-y-auto">
              {filteredPlayers.length === 0 ? (
                <li className="text-sm text-slate-400">No players match your search.</li>
              ) : (
                filteredPlayers.map((player) => (
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
                      onClick={() => addToSquad(player)}
                      className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
                    >
                      Add
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Your squad ({squad.length})</h2>
            <p className="mt-1 text-xs text-slate-500">Lock players you must keep or flag must-sell exits.</p>
            <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto">
              {squad.length === 0 ? (
                <li className="text-sm text-slate-400">No players added yet.</li>
              ) : (
                squad.map((member) => (
                  <li
                    key={member.id}
                    className="rounded-xl border border-slate-200 px-3 py-3"
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-900">{member.name}</p>
                        <p className="text-xs text-slate-500">
                          {member.positions.join("/")} · ${member.price.toLocaleString()}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <ToggleButton
                          active={member.locked}
                          label="Lock"
                          color="bg-blue-100 text-blue-800"
                          onClick={() => toggleLock(member.id)}
                        />
                        <ToggleButton
                          active={member.mustSell}
                          label="Must sell"
                          color="bg-orange-100 text-orange-800"
                          onClick={() => toggleMustSell(member.id)}
                        />
                        <button
                          onClick={() => removeFromSquad(member.id)}
                          className="rounded-full px-2.5 py-1 text-xs font-medium text-slate-500 hover:bg-rose-50 hover:text-rose-700"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>

        <SavedTeamsPanel payload={savedTeamPayload} onLoad={applySavedTeam} />
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-semibold text-slate-900">Team settings</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
              Bank
            </label>
            <input
              type="number"
              min={0}
              step={1000}
              value={bank}
              onChange={(event) => setBank(Math.max(0, Number(event.target.value)))}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
              Trades
            </label>
            <div className="flex gap-2">
              {[1, 2, 3].map((value) => (
                <button
                  key={value}
                  onClick={() => setTradesAvailable(value as 1 | 2 | 3)}
                  className={`flex-1 rounded-lg border px-3 py-2 text-sm font-semibold ${
                    tradesAvailable === value
                      ? "border-slate-900 bg-slate-900 text-white"
                      : "border-slate-300 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
              Boosts
            </label>
            <input
              type="number"
              min={0}
              max={9}
              value={boostsAvailable}
              onChange={(event) =>
                setBoostsAvailable(Math.max(0, Math.min(9, Number(event.target.value))))
              }
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
              Strategy
            </label>
            <select
              value={strategy}
              onChange={(event) => setStrategy(event.target.value as Strategy)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            >
              {STRATEGY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={() => void handleGetRecommendations()}
            disabled={loading}
            className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {loading ? "Calculating…" : "Get recommendations"}
          </button>
          <p className="text-sm text-slate-500">Saved teams make it easy to revisit trade scenarios on mobile.</p>
        </div>
      </section>

      {recError ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {recError}
        </p>
      ) : null}

      {recommendations ? (
        <>
          <ChartCard
            title="Top recommendation comparison"
            description="Best +3 round projection in each trade-count group."
          >
            <ComparisonBarChart data={tradeComparison} />
          </ChartCard>

          <section className="space-y-6">
            {groupedRecommendations && groupedRecommendations.size === 0 ? (
              <p className="text-sm text-slate-500">
                No valid trade recommendations found. Try increasing your bank or adjusting
                locked and must-sell settings.
              </p>
            ) : null}

            {groupedRecommendations
              ? Array.from(groupedRecommendations.entries()).map(([tradeCount, group]) => (
                  <div
                    key={tradeCount}
                    className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
                  >
                    <h2 className="text-xl font-semibold text-slate-900">
                      {TRADE_COUNT_LABELS[tradeCount] ?? `${tradeCount}-trade options`}
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Top {group.length} recommendation{group.length === 1 ? "" : "s"} sorted by trade score.
                    </p>
                    <div className="mt-4 space-y-3">
                      {group.map((recommendation, index) => (
                        <RecommendationCard
                          key={`${tradeCount}-${index}`}
                          recommendation={recommendation}
                          playerIndex={playerIndex}
                        />
                      ))}
                    </div>
                  </div>
                ))
              : null}
          </section>
        </>
      ) : null}
    </main>
  );
}
