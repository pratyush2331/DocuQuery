import { useCallback, useEffect, useState } from "react";
import { DocumentResponse, listDocuments } from "./services/api";
import UploadDocument from "./components/UploadDocument";
import DocumentList from "./components/DocumentList";
import ChatWindow from "./components/ChatWindow";
import "./styles/App.css";

type BackendStatus = "checking" | "online" | "offline";

function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
      setBackendStatus("online");
    } catch {
      setBackendStatus("offline");
    }
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  // Poll while any document is still PROCESSING so status/page/chunk
  // counts update without a manual refresh.
  useEffect(() => {
    const hasPending = documents.some((d) => d.status === "PROCESSING");
    if (!hasPending) return;
    const interval = setInterval(refreshDocuments, 1500);
    return () => clearInterval(interval);
  }, [documents, refreshDocuments]);

  const handleUploaded = () => {
    refreshDocuments();
  };

  const selectedDocument = documents.find((d) => d.document_id === selectedId) ?? null;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1 className="app-title">DocuQuery</h1>

        <UploadDocument onUploaded={handleUploaded} />

        <div className="doc-list">
          <DocumentList
            documents={documents}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>

        <div className={`backend-status backend-status--${backendStatus}`}>
          <span className="status-dot" />
          {backendStatus === "checking" && "Checking backend..."}
          {backendStatus === "online" && "Backend online"}
          {backendStatus === "offline" &&
            "Backend offline — start it with uvicorn app.main:app --reload"}
        </div>
      </aside>

      <main className="main-area">
        <header className="main-header">
          <span className={selectedDocument ? "" : "doc-name-placeholder"}>
            {selectedDocument ? selectedDocument.document_name : "No document selected"}
          </span>
        </header>

        <ChatWindow document={selectedDocument} />
      </main>
    </div>
  );
}

export default App;
