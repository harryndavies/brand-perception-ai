export type AnalysisStatus = "pending" | "processing" | "complete" | "failed";

export type JobStatus = "idle" | "pending" | "running" | "complete" | "failed";

export interface BrandPillar {
  name: string;
  description: string;
  confidence: number;
  sources: string[];
}

export interface ModelPerception {
  model: string;
  summary: string;
  sentiment: number;
  key_themes: string[];
}

export interface CompetitorPosition {
  brand: string;
  premium_score: number;
  lifestyle_score: number;
}

export interface TrendPoint {
  date: string;
  sentiment: number;
  model: string;
}

export interface BrandScores {
  brand_recognition: number;
  sentiment: number;
  innovation: number;
  value_perception: number;
  market_positioning: number;
}

export type ModelOption = "sonnet" | "haiku" | "opus";

export interface BrandReport {
  id: string;
  brand: string;
  competitors: string[];
  model: ModelOption;
  status: AnalysisStatus;
  sentiment_score: number | null;
  scores: BrandScores | null;
  pillars: BrandPillar[];
  model_perceptions: ModelPerception[];
  competitor_positions: CompetitorPosition[];
  trend_data: TrendPoint[];
  created_at: string;
  completed_at: string | null;
}

export interface AnalysisJob {
  id: string;
  label: string;
  status: JobStatus;
  progress: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  team: string;
  has_api_key: boolean;
}

export interface Schedule {
  id: string;
  brand: string;
  competitors: string[];
  model: ModelOption;
  interval_days: number;
  next_run: string;
  active: boolean;
  created_at: string;
}
