// Lightweight typed WebSocket client for live per-ply analysis.
//
// The backend keeps the focus lock alive for as long as this socket stays
// open; closing the tab / navigating away tears it down so the Celery
// background scanner can resume.

const API_URL =
  (typeof window !== "undefined" &&
    (process.env.NEXT_PUBLIC_API_URL as string | undefined)) ||
  "http://localhost:8000";

export type Stage = "shallow" | "standard" | "deep" | "enrich";

export interface MultiPV {
  rank: number;
  san: string;
  uci: string;
  eval_cp: number;
  pv_san: string[];
}

export interface Motif {
  type: string;
  attacker?: string;
  pinned?: string;
  target?: string;
  front?: string;
  back?: string;
  square?: string;
  squares?: string[];
}

export interface PlyEvent {
  move_number?: number;
  color?: "white" | "black";
  move_san?: string;
  best_move_san?: string;
  classification?: string;
  eval_before?: number;
  eval_after?: number;
  centipawn_loss?: number;
  win_percent_before?: number;
  win_percent_after?: number;
  accuracy_percent?: number;
  is_critical_moment?: boolean;
  multipv?: MultiPV[];
  motifs?: Motif[];
  features?: Record<string, unknown>;
  comment?: string | null;
  completed_stages?: Stage[];
  fen?: string;
}

export interface AnalysisSocketHandlers {
  onHello?: (totalPlies: number, stages: Stage[]) => void;
  onPly?: (ply: number, stage: Stage, data: PlyEvent) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
  onStatusChange?: (status: "connecting" | "open" | "closed" | "error") => void;
}

export interface AnalysisSocket {
  setFocus(ply: number): void;
  requestDeepAll(): void;
  cancelDeepAll(): void;
  close(): void;
}

function buildWsUrl(gameId: string): string {
  const base = API_URL.replace(/^http/, "ws");
  return `${base}/ws/games/${gameId}/analysis`;
}

export function connectAnalysisSocket(
  gameId: string,
  handlers: AnalysisSocketHandlers = {},
): AnalysisSocket {
  handlers.onStatusChange?.("connecting");
  const ws = new WebSocket(buildWsUrl(gameId));

  ws.onopen = () => handlers.onStatusChange?.("open");
  ws.onerror = () => handlers.onStatusChange?.("error");
  ws.onclose = () => handlers.onStatusChange?.("closed");

  ws.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data);
      switch (msg.type) {
        case "hello":
          handlers.onHello?.(msg.total_plies, msg.stages);
          break;
        case "ply":
          handlers.onPly?.(msg.ply, msg.stage, msg.data);
          break;
        case "done":
          handlers.onDone?.();
          break;
        case "error":
          handlers.onError?.(msg.message);
          break;
      }
    } catch {
      // ignore malformed frames
    }
  };

  const send = (payload: Record<string, unknown>) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  };

  return {
    setFocus(ply: number) {
      send({ type: "focus", ply });
    },
    requestDeepAll() {
      send({ type: "request_deep_all" });
    },
    cancelDeepAll() {
      send({ type: "cancel_deep_all" });
    },
    close() {
      send({ type: "close" });
      try {
        ws.close();
      } catch {
        // ignore
      }
    },
  };
}
