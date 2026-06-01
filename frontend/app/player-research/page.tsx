const fields = [
  "price",
  "recent scores",
  "average",
  "breakeven (placeholder for future data feed)",
  "rolling average",
  "minutes",
  "starting/bench role",
  "injury status",
  "next opponents",
  "bye availability",
  "projection",
];

export default function PlayerResearchPage() {
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
      </div>
    </main>
  );
}
