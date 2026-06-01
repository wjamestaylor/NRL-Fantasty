const signals = [
  "named in starting side",
  "bench risk",
  "injury concern",
  "suspension",
  "Origin/rest risk",
  "role change",
  "coach quote boost/downgrade",
];

export default function NewsPage() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">News & Alerts</h1>
        <p className="mt-2 text-slate-600">
          News signal layer converts team/news updates into structured trade-risk flags.
        </p>
        <ul className="mt-4 list-disc space-y-1 pl-5 text-slate-700">
          {signals.map((signal) => (
            <li key={signal}>{signal}</li>
          ))}
        </ul>
      </div>
    </main>
  );
}
