const baseFields = [
  "price",
  "recent scores",
  "average",
  "rolling average",
  "minutes",
  "starting/bench role",
  "injury status",
  "next opponents",
  "bye availability",
  "projection",
];

async function isBreakevenAvailable(): Promise<boolean> {
  const apiBaseUrl = process.env.NRL_API_BASE_URL;
  if (!apiBaseUrl) {
    return false;
  }

  try {
    const response = await fetch(`${apiBaseUrl}/health/data-sources`, { cache: "no-store" });
    if (!response.ok) {
      return false;
    }
    const payload = (await response.json()) as {
      features?: { player_breakeven?: { enabled?: boolean } };
    };
    return payload.features?.player_breakeven?.enabled === true;
  } catch {
    return false;
  }
}

export default async function PlayerResearchPage() {
  const breakevenAvailable = await isBreakevenAvailable();
  const fields = breakevenAvailable ? [...baseFields, "breakeven"] : baseFields;

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Player Research</h1>
        <p className="mt-2 text-slate-600">
          Unified player explorer fields used by recommendation and planner workflows.
        </p>
        <ul className="mt-4 list-disc space-y-1 pl-5 text-slate-700">
          {fields.map((field) => (
            <li key={field}>{field}</li>
          ))}
        </ul>
        {!breakevenAvailable ? (
          <p className="mt-4 text-sm text-slate-500">
            Breakeven is hidden until the player feed reports complete coverage.
          </p>
        ) : null}
      </div>
    </main>
  );
}
