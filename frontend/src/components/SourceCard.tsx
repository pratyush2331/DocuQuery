import { useState } from "react";
import { RetrievedChunkInfo, Source } from "../services/api";

interface SourceCardProps {
  source: Source;
  chunk?: RetrievedChunkInfo;
}

function SourceCard({ source, chunk }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="source-card">
      <button
        className="source-card-header"
        onClick={() => setExpanded((v) => !v)}
      >
        <span>
          📄 {source.document_name} · Page {source.page_number}
        </span>
        <span className="source-card-toggle">{expanded ? "−" : "+"}</span>
      </button>
      {expanded && (
        <div className="source-card-body">
          {chunk ? (
            <>
              <p className="source-card-text">{chunk.text}</p>
              <p className="source-card-score">
                similarity: {(chunk.similarity_score * 100).toFixed(0)}%
              </p>
            </>
          ) : (
            <p className="source-card-text">No retrieved text available.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default SourceCard;
