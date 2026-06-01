const scenarios = ["conservative", "balanced", "aggressive"];

export default function PlannerPage() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Planner</h1>
        <p className="mt-2 text-slate-600">
          Round-by-round bye and cash curve planning for next 3/6/10 rounds.
        </p>

        <h2 className="mt-6 text-lg font-semibold">Scenario mode</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {scenarios.map((scenario) => (
            <span
              key={scenario}
              className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium capitalize"
            >
              {scenario}
            </span>
          ))}
        </div>
      </div>
    </main>
  );
}
