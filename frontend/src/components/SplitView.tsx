import { Fragment, useEffect, useState } from "react";
import {
  Group,
  Panel,
  Separator,
} from "react-resizable-panels";
import { useDroppable } from "@dnd-kit/core";
import type { SplitPane, SessionEntry } from "../types";
import { SplitPaneView } from "./SplitPaneView";

// --- Drop zone (right edge, visible during drag) ---

function DropZone({ isDragging }: { isDragging: boolean }) {
  const { isOver, setNodeRef } = useDroppable({ id: "split-drop-zone" });

  if (!isDragging) return null;

  return (
    <div
      ref={setNodeRef}
      className={`w-14 flex items-center justify-center border-2 border-dashed rounded-lg transition-colors mx-1 shrink-0 ${
        isOver
          ? "border-slack-accent bg-slack-accent/10"
          : "border-slack-border/30 bg-transparent"
      }`}
    >
      <span
        className={`text-2xl ${
          isOver ? "text-slack-accent" : "text-slack-muted/40"
        }`}
      >
        +
      </span>
    </div>
  );
}

// --- Resize handle ---

function ResizeHandle() {
  return (
    <Separator className="w-1 hover:w-1.5 bg-slack-border/30 hover:bg-slack-accent/50 transition-all cursor-col-resize shrink-0" />
  );
}

// --- Main ---

interface Props {
  panes: SplitPane[];
  activePaneId: string | null;
  canAddPane: boolean;
  isDragging: boolean;
  onActivate: (paneId: string) => void;
  onClose: (paneId: string) => void;
  onSessionUpdate: (paneId: string, session: SessionEntry) => void;
  onRefreshGroup: () => void;
  onInputChange: (paneId: string, value: string) => void;
  onSend: (paneId: string) => void;
  onPasteImages: (
    paneId: string,
    updater: (
      prev: { data: string; preview: string }[],
    ) => { data: string; preview: string }[],
  ) => void;
}

export function SplitView({
  panes,
  activePaneId,
  canAddPane,
  isDragging,
  onActivate,
  onClose,
  onSessionUpdate,
  onRefreshGroup,
  onInputChange,
  onSend,
  onPasteImages,
}: Props) {
  // レスポンシブ: 画面幅に基づくペイン数制限
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);
  useEffect(() => {
    const handler = () => setWindowWidth(window.innerWidth);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);

  const maxVisiblePanes =
    windowWidth < 768 ? 1 : windowWidth < 1200 ? 2 : 4;
  const visiblePanes = panes.slice(0, maxVisiblePanes);

  return (
    <div className="flex-1 flex min-w-0 min-h-0">
      <Group orientation="horizontal" className="flex-1">
        {visiblePanes.map((pane, i) => (
          <Fragment key={pane.paneId}>
            {i > 0 && <ResizeHandle />}
            <Panel
              minSize={15}
              defaultSize={100 / visiblePanes.length}
            >
              <SplitPaneView
                pane={pane}
                isActive={pane.paneId === activePaneId}
                showCloseButton={visiblePanes.length > 1}
                onActivate={() => onActivate(pane.paneId)}
                onClose={() => onClose(pane.paneId)}
                onSessionUpdate={(s) => onSessionUpdate(pane.paneId, s)}
                onRefreshGroup={onRefreshGroup}
                onInputChange={(v) => onInputChange(pane.paneId, v)}
                onSend={() => onSend(pane.paneId)}
                onPasteImages={(updater) =>
                  onPasteImages(pane.paneId, updater)
                }
              />
            </Panel>
          </Fragment>
        ))}
      </Group>

      {canAddPane && <DropZone isDragging={isDragging} />}
    </div>
  );
}
