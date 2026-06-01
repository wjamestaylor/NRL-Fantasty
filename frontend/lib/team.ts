export type Strategy = "conservative" | "balanced" | "aggressive";

export type SavedTeamPayload = {
  squad: string[];
  bank: number;
  trades_available: number;
  boosts_available: number;
  strategy: Strategy;
  locked_players?: string[];
  must_sell?: string[];
  planning_horizon?: number;
  compare_all_scenarios?: boolean;
};

export type SavedTeamRecord = {
  id: string;
  name: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  team: SavedTeamPayload;
};
