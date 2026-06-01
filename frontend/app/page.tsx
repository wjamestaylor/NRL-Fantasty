import Link from "next/link";

const highlights = [
  "Shared navigation and account-aware workflow across every screen",
  "Saved team setups that persist between sessions",
  "Visual charts for price trends, projections, and planning trade-offs",
  "Mobile-first layouts tuned for quick decision-making on smaller screens",
];

const screens = [
  {
    href: "/trade-lab",
    name: "Trade Lab",
    description: "Build a squad, run recommendations, and compare trade outcomes.",
  },
  {
    href: "/player-research",
    name: "Player Research",
    description: "Inspect recent trends, minutes, and short-term projections.",
  },
  {
    href: "/planner",
    name: "Planner",
    description: "Model multi-round scenarios with bye coverage and cash flow.",
  },
  {
    href: "/news",
    name: "News & Alerts",
    description: "Track the signals that shape confidence and risk decisions.",
  },
  {
    href: "/system-health",
    name: "System Health",
    description: "Review ingestion status, probes, and operational readiness.",
  },
];

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 sm:py-10">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-500">
          Phase 6
        </p>
        <h1 className="mt-2 text-3xl font-bold text-slate-900 sm:text-4xl">
          Fantasy NRL Trade Lab
        </h1>
        <p className="mt-3 max-w-3xl text-base text-slate-600 sm:text-lg">
          Build your squad context, compare trade paths, save setups to your account,
          and monitor the product with charts and production-ready health checks.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {highlights.map((item) => (
          <div key={item} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium leading-6 text-slate-700">{item}</p>
          </div>
        ))}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">Explore the product</h2>
            <p className="mt-1 text-sm text-slate-500">
              Start with recommendations, research, or longer-range planning.
            </p>
          </div>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {screens.map((screen) => (
            <Link
              key={screen.href}
              href={screen.href}
              className="rounded-xl border border-slate-200 bg-slate-50 p-5 transition hover:border-slate-300 hover:bg-slate-100"
            >
              <h3 className="text-lg font-semibold text-slate-900">{screen.name}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{screen.description}</p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
