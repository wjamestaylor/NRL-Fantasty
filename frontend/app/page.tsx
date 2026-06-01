import Link from "next/link";

const keyRecommendations = [
  "Best 1-, 2-, and 3-trade combinations",
  "Projected gain over 3 and 6 rounds",
  "Cash impact and bye-round coverage effects",
  "Role/minutes and risk-aware trade explanations",
];

const screens = [
  { href: "/trade-lab", name: "Trade Lab" },
  { href: "/player-research", name: "Player Research" },
  { href: "/planner", name: "Planner" },
  { href: "/news", name: "News & Alerts" },
  { href: "/system-health", name: "System Health" },
];

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-10">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-3xl font-bold">Fantasy NRL Trade Lab</h1>
        <p className="mt-2 text-slate-600">
          Given your roster, bank, and risk preference, find the best trade paths this round.
        </p>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">MVP value</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700">
          {keyRecommendations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">Screens</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {screens.map((screen) => (
            <Link
              key={screen.href}
              href={screen.href}
              className="rounded-lg border border-slate-200 px-4 py-3 font-medium hover:bg-slate-50"
            >
              {screen.name}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
