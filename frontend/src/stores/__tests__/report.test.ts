import { describe, it, expect, beforeEach } from "vitest";
import { useReportStore } from "../report";
import type { BrandReport, AnalysisJob } from "@/types";

const mockReport: BrandReport = {
  id: "r1",
  brand: "Nike",
  competitors: ["Adidas"],
  model: "sonnet",
  status: "complete",
  sentiment_score: 0.7,
  scores: null,
  pillars: [],
  model_perceptions: [],
  competitor_positions: [],
  trend_data: [],
  created_at: "2025-01-01T00:00:00Z",
  completed_at: "2025-01-01T00:01:00Z",
};

const mockJobs: AnalysisJob[] = [
  { id: "j1", label: "AI Perception", status: "running", progress: 50 },
  { id: "j2", label: "News Sentiment", status: "idle", progress: 0 },
];

describe("useReportStore", () => {
  beforeEach(() => {
    useReportStore.setState({ currentReport: null, activeJobs: [] });
  });

  it("sets current report", () => {
    useReportStore.getState().setCurrentReport(mockReport);
    expect(useReportStore.getState().currentReport).toEqual(mockReport);
  });

  it("clears current report", () => {
    useReportStore.getState().setCurrentReport(mockReport);
    useReportStore.getState().setCurrentReport(null);
    expect(useReportStore.getState().currentReport).toBeNull();
  });

  it("sets active jobs", () => {
    useReportStore.getState().setActiveJobs(mockJobs);
    expect(useReportStore.getState().activeJobs).toHaveLength(2);
  });

  it("updates a specific job", () => {
    useReportStore.getState().setActiveJobs(mockJobs);
    useReportStore.getState().updateJob("j1", { status: "complete", progress: 100 });

    const updated = useReportStore.getState().activeJobs.find((j) => j.id === "j1");
    expect(updated?.status).toBe("complete");
    expect(updated?.progress).toBe(100);
  });

  it("does not affect other jobs when updating one", () => {
    useReportStore.getState().setActiveJobs(mockJobs);
    useReportStore.getState().updateJob("j1", { progress: 80 });

    const other = useReportStore.getState().activeJobs.find((j) => j.id === "j2");
    expect(other?.progress).toBe(0);
  });
});
