import { DocumentResponse } from "../services/api";

interface DocumentListProps {
  documents: DocumentResponse[];
  selectedId: string | null;
  onSelect: (documentId: string) => void;
}

const STATUS_LABEL: Record<string, string> = {
  UPLOADED: "Uploaded",
  PROCESSING: "Processing...",
  COMPLETED: "Ready",
  FAILED: "Failed",
};

function DocumentList({ documents, selectedId, onSelect }: DocumentListProps) {
  if (documents.length === 0) {
    return <p className="doc-list-empty">No documents yet.</p>;
  }

  return (
    <ul className="doc-list-items">
      {documents.map((doc) => (
        <li
          key={doc.document_id}
          className={`doc-list-item ${
            doc.document_id === selectedId ? "doc-list-item--selected" : ""
          }`}
          onClick={() => onSelect(doc.document_id)}
          title={doc.error_message ?? undefined}
        >
          <span className="doc-icon">📄</span>
          <div className="doc-item-text">
            <span className="doc-item-name">{doc.document_name}</span>
            <span className={`doc-item-status doc-item-status--${doc.status}`}>
              {STATUS_LABEL[doc.status] ?? doc.status}
              {doc.page_count != null ? ` · ${doc.page_count}p` : ""}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default DocumentList;
