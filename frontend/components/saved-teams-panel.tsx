"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { getApiBaseUrl, parseApiError } from "@/lib/api";
import type { SavedTeamPayload, SavedTeamRecord } from "@/lib/team";

export function SavedTeamsPanel({
  payload,
  onLoad,
}: {
  payload: SavedTeamPayload;
  onLoad: (payload: SavedTeamPayload) => void;
}) {
  const { token, user } = useAuth();
  const [teams, setTeams] = useState<SavedTeamRecord[]>([]);
  const [name, setName] = useState("Current team");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadTeams = useCallback(async () => {
    if (!token) {
      return;
    }

    const response = await fetch(`${getApiBaseUrl()}/user-teams`, {
      headers: { Authorization: "Bearer " + token },
    });

    if (!response.ok) {
      throw new Error(await parseApiError(response));
    }
    setTeams((await response.json()) as SavedTeamRecord[]);
  }, [token]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const timer = window.setTimeout(() => {
      void loadTeams().catch((error: unknown) => {
        setStatus(error instanceof Error ? error.message : "Could not load saved teams.");
      });
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadTeams, token]);

  async function handleSave() {
    if (!token) {
      return;
    }

    setLoading(true);
    setStatus(null);

    try {
      const response = await fetch(`${getApiBaseUrl()}/user-teams`, {
        method: "POST",
        headers: {
          Authorization: "Bearer " + token,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          notes: notes || undefined,
          team: payload,
        }),
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      setStatus("Team saved.");
      await loadTeams();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not save team.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Saved teams</h2>
          <p className="text-sm text-slate-500">
            Save and reload team setups across sessions.
          </p>
        </div>
        {user ? (
          <p className="text-sm text-slate-600">Signed in as {user.display_name}</p>
        ) : null}
      </div>

      {!user ? (
        <p className="mt-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          Sign in from the top navigation to save team setups between sessions.
        </p>
      ) : (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Saved team name"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            />
            <input
              type="text"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Notes (optional)"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              onClick={() => void handleSave()}
              disabled={loading || name.trim().length === 0}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
            >
              {loading ? "Saving…" : "Save current team"}
            </button>
            <button
              onClick={() => void loadTeams()}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Refresh list
            </button>
          </div>

          {status ? <p className="mt-3 text-sm text-slate-600">{status}</p> : null}

          <div className="mt-4 space-y-3">
            {teams.length === 0 ? (
              <p className="text-sm text-slate-400">No saved teams yet.</p>
            ) : (
              teams.map((team) => (
                <div
                  key={team.id}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h3 className="font-semibold text-slate-900">{team.name}</h3>
                      {team.notes ? (
                        <p className="mt-1 text-sm text-slate-600">{team.notes}</p>
                      ) : null}
                      <p className="mt-1 text-xs text-slate-500">
                        Updated {new Date(team.updated_at).toLocaleString()}
                      </p>
                    </div>
                    <button
                      onClick={() => onLoad(team.team)}
                      className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
                    >
                      Load team
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
