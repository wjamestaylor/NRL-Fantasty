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

export default function TradeLabPage() {
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
      </div>
    </main>
  );
}
