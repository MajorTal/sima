'use client';

import type { Event, Memory } from '@/lib/types';
import MemoryPanel from './MemoryPanel';
import StreamPanel from './StreamPanel';

interface FourPanelLayoutProps {
  onEventClick?: (event: Event) => void;
  onMemoryClick?: (memory: Memory) => void;
}

export default function FourPanelLayout({
  onEventClick,
  onMemoryClick,
}: FourPanelLayoutProps) {
  return (
    <div className="four-panel-grid h-[calc(100vh-200px)]">
      {/* Top Left: Memories */}
      <MemoryPanel
        onMemoryClick={onMemoryClick}
        maxCoreMemories={5}
        maxRecentMemories={10}
      />

      {/* Top Right: Subconscious (Module Outputs) */}
      <StreamPanel
        stream="subconscious"
        title="Subconscious"
        maxEvents={50}
        onEventClick={onEventClick}
      />

      {/* Bottom Left: Inner Monologue (Conscious/Workspace) */}
      <StreamPanel
        stream="conscious"
        title="Inner Monologue"
        maxEvents={50}
        onEventClick={onEventClick}
      />

      {/* Bottom Right: External Chat */}
      <StreamPanel
        stream="external"
        title="External Chat"
        maxEvents={50}
        onEventClick={onEventClick}
      />
    </div>
  );
}
