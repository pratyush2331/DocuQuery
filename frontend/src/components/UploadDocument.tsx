import { useRef, useState } from "react";
import { extractErrorMessage, uploadDocument } from "../services/api";

interface UploadDocumentProps {
  onUploaded: () => void;
}

function UploadDocument({ onUploaded }: UploadDocumentProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file later
    if (!file) return;

    setError(null);
    setIsUploading(true);
    try {
      await uploadDocument(file);
      onUploaded();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-section">
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        style={{ display: "none" }}
      />
      <button
        className="upload-btn"
        disabled={isUploading}
        onClick={() => inputRef.current?.click()}
      >
        {isUploading ? "Uploading..." : "+ Upload PDF"}
      </button>
      {error && <p className="upload-error">{error}</p>}
    </div>
  );
}

export default UploadDocument;
