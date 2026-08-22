import { useState } from "react";
import { RetrievedChunkInfo } from "../services/api";

interface RetrievedContextProps {
  chunks: RetrievedChunkInfo[];
}

function RetrievedContext({ chunks }: RetrievedContextProps) {
  const [visible, setVisible] = useState(false);

  if (chunks.length === 0) return null;

  return (
    <div className="retrieved-context">
      <button
        className="retrieved-context-toggle"
        onClick={() => setVisible((v) => !v)}
      >
        {visible ? "Hide" : "View"} retrieved context ({chunks.length} chunks)
      </button>
      {visible && (
        <div className="retrieved-context-list">
          {chunks.map((chunk) => (
            <div key={chunk.chunk_id} className="retrieved-context-item">
              <div className="retrieved-context-item-header">
                <span>Page {chunk.page_number}</span>
                <span>{(chunk.similarity_score * 100).toFixed(0)}% match</span>
              </div>
              <p className="retrieved-context-item-text">{chunk.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RetrievedContext;
