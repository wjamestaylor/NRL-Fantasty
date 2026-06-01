const signals = [
  "Named in starting side",
  "Bench risk or role squeeze",
  "Injury concern or return timeline",
  "Suspension or availability risk",
  "Origin/rest risk",
  "Role change or minutes upside",
  "Coach quote upgrade or downgrade",
  "Late reshuffle watchlist",
];

export default function NewsPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 sm:py-10">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">News & Alerts</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
          News signal ingestion turns team and injury updates into structured trade-risk
          flags that feed directly into recommendation confidence.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {signals.map((signal) => (
          <div key={signal} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">
              Signal
            </p>
            <p className="mt-3 text-base font-medium text-slate-800">{signal}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
