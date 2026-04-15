"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiJson } from "@/lib/api";
import {
  connectAnalysisSocket,
  type AnalysisSocket,
  type PlyEvent,
  type Stage,
} from "@/lib/analysisSocket";

export interface MoveAnalysisRow {
  move_number: number;
  color: "white" | "black";
  san?: string;
  move_san: string;
  best_move_san?: string;
  eval_before: number;
  eval_after: number;
  classification: string;
  comment?: string | null;
  fen?: string | null;
  win_percent_before?: number | null;
  win_percent_after?: number | null;
  accuracy_percent?: number | null;
  is_critical_moment?: boolean | null;
  maia?: {
    top1_san?: string | null;
    top1_prob?: number | null;
    match_played?: boolean | null;
    rating_used?: number | null;
  } | null;
  details?: {
    multipv?: PlyEvent["multipv"];
    motifs?: PlyEvent["motifs"];
    features?: Record<string, unknown>;
  };
  completed_stages?: Stage[];
}

export interface AnalysisSummary {
  blunders?: number;
  mistakes?: number;
  inaccuracies?: number;
  avg_eval_loss?: number;
  phase_scores?: Record<string, number>;
  time_trouble?: boolean;
  accuracy_white?: number | null;
  accuracy_black?: number | null;
  opening_eco?: string | null;
  opening_name?: string | null;
  phase_acpl?: Record<string, number> | null;
  motif_counts?: Record<string, number> | null;
}

export interface StageProgress {
  shallow: number;
  standard: number;
  deep: number;
  enrich: number;
  total: number;
}

interface UseGameAnalysisState {
  analysis: MoveAnalysisRow[];
  summary: AnalysisSummary | null;
  stageProgress: StageProgress;
  status: "connecting" | "open" | "closed" | "error" | "idle";
  setFocus: (ply: number) => void;
  requestDeepAll: () => void;
}

function emptyStageProgress(): StageProgress {
  return { shallow: 0, standard: 0, deep: 0, enrich: 0, total: 0 };
}

function recomputeStageProgress(rows: MoveAnalysisRow[]): StageProgress {
  const p = emptyStageProgress();
  p.total = rows.length;
  for (const row of rows) {
    const stages = row.completed_stages ?? [];
    if (stages.includes("shallow")) p.shallow += 1;
    if (stages.includes("standard")) p.standard += 1;
    if (stages.includes("deep")) p.deep += 1;
    if (stages.includes("enrich")) p.enrich += 1;
  }
  return p;
}

function upsertRow(rows: MoveAnalysisRow[], ply: number, event: PlyEvent, stage: Stage): MoveAnalysisRow[] {
  const next = rows.slice();
  const idx = ply;
  const existing = next[idx];
  const merged: MoveAnalysisRow = {
    ...(existing ?? ({
      move_number: event.move_number ?? 0,
      color: event.color ?? "white",
      move_san: event.move_san ?? "",
      eval_before: event.eval_before ?? 0,
      eval_after: event.eval_after ?? 0,
      classification: event.classification ?? "ok",
    } as MoveAnalysisRow)),
    ...Object.fromEntries(
      Object.entries({
        move_number: event.move_number,
        color: event.color,
        move_san: event.move_san,
        best_move_san: event.best_move_san,
        eval_before: event.eval_before,
        eval_after: event.eval_after,
        classification: event.classification,
        win_percent_before: event.win_percent_before,
        win_percent_after: event.win_percent_after,
        accuracy_percent: event.accuracy_percent,
        is_critical_moment: event.is_critical_moment,
        fen: event.fen,
        comment: event.comment,
      }).filter(([, v]) => v !== undefined),
    ),
  };
  const details = { ...(existing?.details ?? {}) };
  if (event.multipv) details.multipv = event.multipv;
  if (event.motifs) details.motifs = event.motifs;
  if (event.features) details.features = event.features;
  merged.details = details;
  if (event.completed_stages) {
    merged.completed_stages = event.completed_stages;
  } else if (stage) {
    const s = new Set(merged.completed_stages ?? []);
    s.add(stage);
    merged.completed_stages = Array.from(s) as Stage[];
  }
  next[idx] = merged;
  return next;
}

export function useGameAnalysis(gameId: string | undefined): UseGameAnalysisState {
  const [analysis, setAnalysis] = useState<MoveAnalysisRow[]>([]);
  const [summary, setSummary] = useState<AnalysisSummary | null>(null);
  const [stageProgress, setStageProgress] = useState<StageProgress>(emptyStageProgress());
  const [status, setStatus] = useState<UseGameAnalysisState["status"]>("idle");
  const socketRef = useRef<AnalysisSocket | null>(null);
  const focusDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!gameId) return;
    let cancelled = false;

    setStatus("connecting");

    apiJson<{ moves: MoveAnalysisRow[]; summary: AnalysisSummary | null }>(
      `/api/games/${gameId}/analysis`,
    )
      .then((data) => {
        if (cancelled) return;
        const ordered = (data.moves ?? []).map((m, i) => ({
          ...m,
          // plies are 0-indexed in the live stream; REST returns them in move_number+color order
          // which already matches the natural 0..N-1 order after "color DESC" tiebreak.
          __ply: i,
        }));
        setAnalysis(ordered);
        setSummary(data.summary ?? null);
        setStageProgress(recomputeStageProgress(ordered));
      })
      .catch(() => {
        if (cancelled) return;
        setAnalysis([]);
        setSummary(null);
        setStageProgress(emptyStageProgress());
      });

    const socket = connectAnalysisSocket(gameId, {
      onStatusChange: setStatus,
      onHello: () => {
        // no-op; total_plies is derived from PGN on the frontend
      },
      onPly: (ply, stage, data) => {
        setAnalysis((prev) => {
          const next = upsertRow(prev, ply, data, stage);
          setStageProgress(recomputeStageProgress(next));
          return next;
        });
      },
      onDone: () => setStatus("closed"),
      onError: () => setStatus("error"),
    });
    socketRef.current = socket;

    return () => {
      cancelled = true;
      socket.close();
      socketRef.current = null;
      if (focusDebounce.current) {
        clearTimeout(focusDebounce.current);
        focusDebounce.current = null;
      }
    };
  }, [gameId]);

  const setFocus = useCallback((ply: number) => {
    if (!socketRef.current) return;
    if (focusDebounce.current) clearTimeout(focusDebounce.current);
    focusDebounce.current = setTimeout(() => {
      socketRef.current?.setFocus(ply);
    }, 150);
  }, []);

  const requestDeepAll = useCallback(() => {
    socketRef.current?.requestDeepAll();
  }, []);

  return useMemo(
    () => ({ analysis, summary, stageProgress, status, setFocus, requestDeepAll }),
    [analysis, summary, stageProgress, status, setFocus, requestDeepAll],
  );
}
