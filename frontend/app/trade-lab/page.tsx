"use client";

import { useEffect, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

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

type Strategy = "conservative" | "balanced" | "aggressive";

const STRATEGY_OPTIONS: { value: Strategy; label: string }[] = [
  { value: "conservative", label: "Conservative" },
  { value: "balanced", label: "Balanced" },
  { value: "aggressive", label: "Aggressive" },
];

const TRADE_COUNT_LABELS: Record<number, string> = {
  1: "Best 1-Trade Options",
  2: "Best 2-Trade Options",
  3: "Best 3-Trade Options",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCash(amount: number): string {
  return `${amount >= 0 ? "+" : "-"}$${Math.abs(amount).toLocaleString()}`;
}

function groupByTradeCount(
  recs: TradeRecommendation[],
): Map<number, TradeRecommendation[]> {
  const map = new Map<number, TradeRecommendation[]>();
  for (const rec of recs) {
    const group = map.get(rec.trade_count) ?? [];
    group.push(rec);
    map.set(rec.trade_count, group);
  }
  return map;
}

// ── Sub-components ────────────────────────────────────────────────────────────

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
      onClick={onClick}
      className={`rounded px-2 py-0.5 text-xs font-semibold transition ${
        active ? color : "bg-slate-100 text-slate-500 hover:bg-slate-200"
      }`}
    >
      {label}
    </button>
  );
}

function RecommendationCard({
  rec,
  playerIndex,
}: {
  rec: TradeRecommendation;
  playerIndex: Map<string, PlayerInfo>;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap gap-4 text-sm">
        <div>
          <span className="font-medium text-slate-700">Score: </span>
          <span className="font-bold">{rec.total_trade_score.toFixed(2)}</span>
        </div>
        <div>
          <span className="font-medium text-slate-700">Pts +3R: </span>
          <span
            className={
              rec.projected_gain_next_3 >= 0
                ? "text-green-700 font-semibold"
                : "text-red-700 font-semibold"
            }
          >
            {rec.projected_gain_next_3 >= 0 ? "+" : ""}
            {rec.projected_gain_next_3.toFixed(1)}
          </span>
        </div>
        <div>
          <span className="font-medium text-slate-700">Pts +6R: </span>
          <span
            className={
              rec.projected_gain_next_6 >= 0
                ? "text-green-700 font-semibold"
                : "text-red-700 font-semibold"
            }
          >
            {rec.projected_gain_next_6 >= 0 ? "+" : ""}
            {rec.projected_gain_next_6.toFixed(1)}
          </span>
        </div>
        <div>
          <span className="font-medium text-slate-700">Cash: </span>
          <span
            className={
              rec.cash_impact >= 0
                ? "text-green-700 font-semibold"
                : "text-red-700 font-semibold"
            }
          >
            {formatCash(rec.cash_impact)}
          </span>
        </div>
        <div>
          <span className="font-medium text-slate-700">Risk: </span>
          <span>{rec.risk_score.toFixed(2)}</span>
        </div>
      </div>

      <div className="mt-3 space-y-1">
        {rec.trades.map((t, i) => {
          const outPlayer = playerIndex.get(t.out_player_id);
          const inPlayer = playerIndex.get(t.in_player_id);
          return (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span className="rounded bg-red-100 px-2 py-0.5 text-red-800 font-medium">
                OUT: {outPlayer?.name ?? t.out_player_id}
                {outPlayer ? ` ($${outPlayer.price.toLocaleString()})` : ""}
              </span>
              <span className="text-slate-400">→</span>
              <span className="rounded bg-green-100 px-2 py-0.5 text-green-800 font-medium">
                IN: {inPlayer?.name ?? t.in_player_id}
                {inPlayer ? ` ($${inPlayer.price.toLocaleString()})` : ""}
              </span>
            </div>
          );
        })}
      </div>

      <p className="mt-3 text-xs text-slate-500 italic">{rec.explanation}</p>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function TradeLabPage() {
  const baseUrl =
    typeof window !== "undefined"
      ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000")
      : "http://localhost:8000";

  // All available players for the picker
  const [allPlayers, setAllPlayers] = useState<PlayerInfo[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Squad builder state
  const [squad, setSquad] = useState<SquadMember[]>([]);
  const [pickerSearch, setPickerSearch] = useState("");

  // Team context
  const [bank, setBank] = useState(150000);
  const [tradesAvailable, setTradesAvailable] = useState<1 | 2 | 3>(2);
  const [boostsAvailable, setBoostsAvailable] = useState(1);
  const [strategy, setStrategy] = useState<Strategy>("balanced");

  // Recommendations
  const [recommendations, setRecommendations] = useState<
    TradeRecommendation[] | null
  >(null);
  const [recError, setRecError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Load players on mount
  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`${baseUrl}/players/analytics`);
        if (!res.ok) throw new Error("Failed to load players");
        const data = (await res.json()) as PlayerInfo[];
        setAllPlayers(data);
      } catch {
        setLoadError(
          "Could not load player list. Start the backend to enable the squad builder.",
        );
      }
    };
    void load();
  }, [baseUrl]);

  // Derived: player index for recommendation display
  const playerIndex = new Map<string, PlayerInfo>(
    allPlayers.map((p) => [p.id, p]),
  );
  squad.forEach((m) => playerIndex.set(m.id, m));

  // Squad builder helpers
  const squadIds = new Set(squad.map((m) => m.id));

  const filteredPlayers = allPlayers.filter((p) => {
    if (squadIds.has(p.id)) return false;
    const q = pickerSearch.toLowerCase();
    return (
      !q ||
      p.name.toLowerCase().includes(q) ||
      p.team.toLowerCase().includes(q) ||
      p.positions.some((pos) => pos.toLowerCase().includes(q))
    );
  });

  function addToSquad(player: PlayerInfo) {
    setSquad((prev) => [
      ...prev,
      { ...player, locked: false, mustSell: false },
    ]);
  }

  function removeFromSquad(id: string) {
    setSquad((prev) => prev.filter((m) => m.id !== id));
  }

  function toggleLock(id: string) {
    setSquad((prev) =>
      prev.map((m) =>
        m.id === id
          ? { ...m, locked: !m.locked, mustSell: m.locked ? m.mustSell : false }
          : m,
      ),
    );
  }

  function toggleMustSell(id: string) {
    setSquad((prev) =>
      prev.map((m) =>
        m.id === id
          ? {
              ...m,
              mustSell: !m.mustSell,
              locked: m.mustSell ? m.locked : false,
            }
          : m,
      ),
    );
  }

  // Submit to backend
  async function handleGetRecommendations() {
    if (squad.length === 0) {
      setRecError("Add at least one player to your squad before running recommendations.");
      return;
    }
    setLoading(true);
    setRecError(null);
    setRecommendations(null);

    try {
      const payload = {
        squad: squad.map((m) => m.id),
        bank,
        trades_available: tradesAvailable,
        boosts_available: boostsAvailable,
        strategy,
        locked_players: squad.filter((m) => m.locked).map((m) => m.id),
        must_sell: squad.filter((m) => m.mustSell).map((m) => m.id),
      };

      const res = await fetch(`${baseUrl}/trade/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const detail = (await res.json().catch(() => ({}))) as {
          detail?: string;
        };
        throw new Error(detail.detail ?? `Request failed (${res.status})`);
      }

      const data = (await res.json()) as RecommendationsResponse;
      setRecommendations(data.recommendations);
    } catch (err) {
      setRecError(
        err instanceof Error ? err.message : "Failed to fetch recommendations.",
      );
    } finally {
      setLoading(false);
    }
  }

  const groupedRecs = recommendations
    ? groupByTradeCount(recommendations)
    : null;

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 space-y-6 px-6 py-10">
      {/* Header */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Trade Lab</h1>
        <p className="mt-1 text-slate-600">
          Build your squad, set your budget, and get team-aware 1-, 2-, and
          3-trade recommendations.
        </p>
      </div>

      {loadError && (
        <p className="rounded border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {loadError}
        </p>
      )}

      {/* Squad Builder + Roster — side by side on wider screens */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Player Picker */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Squad Builder</h2>
          <p className="mt-1 text-xs text-slate-500">
            Search and add players to your squad.
          </p>

          <input
            type="text"
            placeholder="Search by name, team, or position…"
            value={pickerSearch}
            onChange={(e) => setPickerSearch(e.target.value)}
            className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
          />

          <ul className="mt-3 max-h-72 space-y-1 overflow-y-auto">
            {filteredPlayers.length === 0 && (
              <li className="text-xs text-slate-400 italic">
                {allPlayers.length === 0
                  ? "Loading players…"
                  : "No players match your search."}
              </li>
            )}
            {filteredPlayers.map((player) => (
              <li
                key={player.id}
                className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-slate-50"
              >
                <div className="min-w-0 flex-1">
                  <span className="truncate font-medium text-sm">
                    {player.name}
                  </span>
                  <span className="ml-2 text-xs text-slate-500">
                    {player.team} · {player.positions.join("/")} ·{" "}
                    ${player.price.toLocaleString()}
                  </span>
                </div>
                <button
                  onClick={() => addToSquad(player)}
                  className="ml-2 shrink-0 rounded bg-slate-800 px-2 py-1 text-xs font-medium text-white hover:bg-slate-700"
                >
                  Add
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Current Roster */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">
            Your Squad{" "}
            <span className="text-sm font-normal text-slate-500">
              ({squad.length} player{squad.length !== 1 ? "s" : ""})
            </span>
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            🔒 Lock = keep in squad. ⚡ Sell = prioritize for trade-out.
          </p>

          {squad.length === 0 ? (
            <p className="mt-4 text-sm text-slate-400 italic">
              No players added yet. Use the Squad Builder to add players.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {squad.map((member) => (
                <li
                  key={member.id}
                  className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <span className="truncate font-medium text-sm">
                      {member.name}
                    </span>
                    <span className="ml-2 text-xs text-slate-500">
                      {member.positions.join("/")} · $
                      {member.price.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <ToggleButton
                      active={member.locked}
                      label="🔒 Lock"
                      color="bg-blue-100 text-blue-800"
                      onClick={() => toggleLock(member.id)}
                    />
                    <ToggleButton
                      active={member.mustSell}
                      label="⚡ Sell"
                      color="bg-orange-100 text-orange-800"
                      onClick={() => toggleMustSell(member.id)}
                    />
                    <button
                      onClick={() => removeFromSquad(member.id)}
                      className="rounded px-2 py-0.5 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600"
                    >
                      ✕
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Team Settings */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Team Settings</h2>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Bank */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Bank ($)
            </label>
            <input
              type="number"
              min={0}
              step={1000}
              value={bank}
              onChange={(e) => setBank(Math.max(0, Number(e.target.value)))}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            />
          </div>

          {/* Trades Available */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Trades Available
            </label>
            <div className="flex gap-2">
              {([1, 2, 3] as const).map((n) => (
                <button
                  key={n}
                  onClick={() => setTradesAvailable(n)}
                  className={`flex-1 rounded-lg border py-2 text-sm font-medium transition ${
                    tradesAvailable === n
                      ? "border-slate-800 bg-slate-800 text-white"
                      : "border-slate-300 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          {/* Boosts */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Boosts Remaining
            </label>
            <input
              type="number"
              min={0}
              max={9}
              value={boostsAvailable}
              onChange={(e) =>
                setBoostsAvailable(
                  Math.max(0, Math.min(9, Number(e.target.value))),
                )
              }
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            />
          </div>

          {/* Strategy */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Strategy
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as Strategy)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            >
              {STRATEGY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => void handleGetRecommendations()}
          disabled={loading}
          className="rounded-lg bg-slate-800 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50 transition"
        >
          {loading ? "Calculating…" : "Get Recommendations"}
        </button>
        {squad.length === 0 && (
          <span className="text-sm text-slate-400">
            Add players to your squad first.
          </span>
        )}
      </div>

      {recError && (
        <p className="rounded border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {recError}
        </p>
      )}

      {/* Results */}
      {groupedRecs && (
        <div className="space-y-6">
          {groupedRecs.size === 0 && (
            <p className="text-sm text-slate-500">
              No valid trade recommendations found for the current squad and
              budget. Try increasing your bank or adjusting locked/must-sell
              settings.
            </p>
          )}

          {Array.from(groupedRecs.entries()).map(([tradeCount, recs]) => (
            <div
              key={tradeCount}
              className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <h2 className="text-lg font-semibold">
                {TRADE_COUNT_LABELS[tradeCount] ?? `${tradeCount}-Trade Options`}
              </h2>
              <p className="mt-1 text-xs text-slate-500">
                Top {recs.length} recommendation
                {recs.length !== 1 ? "s" : ""} — sorted by trade score.
              </p>

              <div className="mt-4 space-y-3">
                {recs.map((rec, i) => (
                  <RecommendationCard
                    key={i}
                    rec={rec}
                    playerIndex={playerIndex}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
