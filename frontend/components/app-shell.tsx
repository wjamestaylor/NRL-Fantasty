"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/trade-lab", label: "Trade Lab" },
  { href: "/player-research", label: "Player Research" },
  { href: "/planner", label: "Planner" },
  { href: "/news", label: "News" },
  { href: "/system-health", label: "System Health" },
] as const;

type AuthMode = "login" | "register";

function navLinkClass(active: boolean): string {
  return active
    ? "rounded-full bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
    : "rounded-full px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900";
}

function NavigationLinks({
  pathname,
  onNavigate,
  stacked = false,
}: {
  pathname: string;
  onNavigate?: () => void;
  stacked?: boolean;
}) {
  return (
    <nav className={stacked ? "grid gap-2" : "hidden items-center gap-2 md:flex"}>
      {NAV_ITEMS.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={navLinkClass(active)}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isReady, login, logout, register, user } = useAuth();
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [authOpen, setAuthOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const authTitle = useMemo(
    () => (authMode === "login" ? "Sign in" : "Create account"),
    [authMode],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      if (authMode === "login") {
        await login(email, password);
      } else {
        await register(email, password, displayName || undefined);
      }
      setAuthOpen(false);
      setPassword("");
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "Could not complete authentication.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen((value) => !value)}
              className="inline-flex rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 md:hidden"
            >
              {mobileOpen ? "Close" : "Menu"}
            </button>
            <Link href="/" className="min-w-0">
              <p className="truncate text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                Fantasy NRL
              </p>
              <p className="truncate text-lg font-bold text-slate-900">Trade Lab</p>
            </Link>
          </div>

          <NavigationLinks pathname={pathname} />

          <div className="flex items-center gap-2">
            {user ? (
              <>
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-semibold text-slate-900">{user.display_name}</p>
                  <p className="text-xs text-slate-500">{user.email}</p>
                </div>
                <button
                  type="button"
                  onClick={logout}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Sign out
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setAuthOpen(true)}
                className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800"
              >
                {isReady ? "Sign in" : "Loading…"}
              </button>
            )}
          </div>
        </div>

        {mobileOpen ? (
          <div className="border-t border-slate-200 bg-white px-4 py-4 md:hidden sm:px-6">
            <NavigationLinks
              pathname={pathname}
              stacked
              onNavigate={() => setMobileOpen(false)}
            />
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              {user ? `Signed in as ${user.display_name}.` : "Sign in to save teams across sessions."}
            </div>
          </div>
        ) : null}
      </header>

      <div className="mx-auto flex min-h-[calc(100vh-73px)] w-full max-w-7xl flex-col">
        {children}
      </div>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-4 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span>Shared navigation, auth, saved teams, charts, and health probes are enabled in Phase 6.</span>
          <span>API health: /health/live and /health/ready</span>
        </div>
      </footer>

      {authOpen ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/50 px-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Account
                </p>
                <h2 className="mt-1 text-2xl font-bold text-slate-900">{authTitle}</h2>
              </div>
              <button
                type="button"
                onClick={() => setAuthOpen(false)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
              >
                Close
              </button>
            </div>

            <div className="mt-4 flex gap-2 rounded-full bg-slate-100 p-1">
              {(["login", "register"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => {
                    setAuthMode(mode);
                    setError(null);
                  }}
                  className={`flex-1 rounded-full px-4 py-2 text-sm font-semibold transition ${
                    authMode === mode
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500"
                  }`}
                >
                  {mode === "login" ? "Sign in" : "Register"}
                </button>
              ))}
            </div>

            <form className="mt-4 space-y-3" onSubmit={(event) => void handleSubmit(event)}>
              {authMode === "register" ? (
                <input
                  type="text"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Display name"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
                />
              ) : null}
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Email"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
                required
              />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Password"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
                required
              />
              {error ? <p className="text-sm text-rose-700">{error}</p> : null}
              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
              >
                {busy ? "Working…" : authTitle}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
