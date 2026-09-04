import { Component, type ErrorInfo, type ReactNode } from "react";
import { Empty } from "@/core/ui";

type State = { message: string | null };

/** Tuval paketi yuklenemezse tum forkOS kabugunu dusurmek yerine hata gosterir. */
export class CanvasErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { message: null };

  static getDerivedStateFromError(error: unknown): State {
    return { message: error instanceof Error ? error.message : "Tuval yüklenemedi" };
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    // Yalnizca yerel tarayici konsolu; harici telemetri yok.
    console.error("Not tuvali başlatılamadı", error, info);
  }

  render() {
    if (this.state.message) {
      return (
        <div className="flex min-h-[36rem] items-center justify-center p-6">
          <Empty variant="page" title="Tuval açılamadı">
            {this.state.message}
          </Empty>
        </div>
      );
    }
    return this.props.children;
  }
}
