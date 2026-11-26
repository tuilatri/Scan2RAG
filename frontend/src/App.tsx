import React, { useState } from 'react';
import { Navbar } from '@/components/layout/navbar';
import { SplitPane } from '@/components/layout/split-pane';
import { ChatContainer } from '@/components/chat/chat-container';
import { PdfViewerPanel } from '@/components/pdf/pdf-viewer-panel';
import { OcrReviewContainer } from '@/components/ocr/ocr-review-container';
import { useChatStream } from '@/hooks/use-chat-stream';
import { usePdfViewer } from '@/hooks/use-pdf-viewer';
import { useBackendHealth } from '@/hooks/use-backend-health';
import { Citation } from '@/types/chat';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'chat' | 'ocr'>('chat');
  const { status: backendStatus } = useBackendHealth();

  // Streaming Hook
  const {
    messages,
    isStreaming,
    streamStatus,
    currentCitations,
    error,
    sendMessage,
    stopStream,
  } = useChatStream();

  // Synchronized PDF Viewer Hook
  const {
    activeDocId,
    activePage,
    activeCitation,
    isSidebarOpen,
    jumpToCitation,
    jumpToPage,
    toggleSidebar,
  } = usePdfViewer({ initialDocId: 'thông_tư_88', initialPage: 1 });

  const handleCitationSelect = (citation: Citation) => {
    jumpToCitation(citation);
  };

  return (
    <div className="flex min-h-screen flex-col bg-background font-sans antialiased text-foreground">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        backendStatus={backendStatus}
      />

      {/* Main Dual-Pane Area */}
      <main className="flex-1 overflow-hidden">
        {activeTab === 'chat' ? (
          <SplitPane
            isRightPaneOpen={isSidebarOpen}
            onToggleRightPane={toggleSidebar}
            leftPane={
              <ChatContainer
                messages={messages}
                isStreaming={isStreaming}
                streamStatus={streamStatus}
                currentCitations={currentCitations}
                error={error}
                activeCitationId={activeCitation?.id}
                onSendMessage={sendMessage}
                onStopStreaming={stopStream}
                onCitationSelect={handleCitationSelect}
              />
            }
            rightPane={
              <PdfViewerPanel
                activeDocId={activeDocId}
                activePage={activePage}
                activeCitation={activeCitation}
              />
            }
          />
        ) : (
          <OcrReviewContainer />
        )}
      </main>
    </div>
  );
};

export default App;
