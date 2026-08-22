import { useEffect, useRef, useState } from "react";
import { DocumentResponse, askQuestion, extractErrorMessage } from "../services/api";
import ChatMessage, { ChatMessageData } from "./ChatMessage";

interface ChatWindowProps {
  document: DocumentResponse | null;
}

// function ChatWindow({ document }: ChatWindowProps) {
//   const [messages, setMessages] = useState<ChatMessageData[]>([]);
//   const [input, setInput] = useState("");
//   const [isLoading, setIsLoading] = useState(false);
//   const bottomRef = useRef<HTMLDivElement>(null);

//   // Reset the conversation whenever the selected document changes.
//   useEffect(() => {
//     setMessages([]);
//     setInput("");
//   }, [document?.document_id]);

function storageKey(documentId: string) {
  return `pdf-rag-chat-history:${documentId}`;
}

function ChatWindow({ document }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load this document's saved history whenever the selected document changes.
  useEffect(() => {
    setInput("");
    if (!document) {
      setMessages([]);
      return;
    }
    const saved = localStorage.getItem(storageKey(document.document_id));
    setMessages(saved ? JSON.parse(saved) : []);
  }, [document?.document_id]);

  // Persist to localStorage every time messages change.
  useEffect(() => {
    if (!document) return;
    localStorage.setItem(storageKey(document.document_id), JSON.stringify(messages));
  }, [messages, document?.document_id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const canAsk = !!document && document.status === "COMPLETED" && !isLoading;

  const handleSend = async () => {
    const question = input.trim();
    if (!question || !document || !canAsk) return;

    const userMessage: ChatMessageData = {
      id: crypto.randomUUID(),
      role: "user",
      text: question,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await askQuestion(document.document_id, question);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: response.answer,
          response,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: extractErrorMessage(err),
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <section className="chat-window">
        {!document ? (
          <div className="chat-empty-state">
            <p>Upload a PDF to start asking questions about it.</p>
          </div>
        ) : document.status !== "COMPLETED" ? (
          <div className="chat-empty-state">
            {document.status === "FAILED" ? (
              <p className="chat-empty-state-error">
                Processing failed: {document.error_message}
              </p>
            ) : (
              <p>Processing "{document.document_name}"...</p>
            )}
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-empty-state">
            <p>Ask a question about "{document.document_name}".</p>
            <p className="chat-empty-state-sub">
              Answers are grounded only in this document's content.
            </p>
          </div>
        ) : (
          <div className="chat-message-list">
            {messages.map((m) => (
              <ChatMessage key={m.id} message={m} />
            ))}
            {isLoading && (
              <div className="chat-message chat-message--assistant">
                <div className="chat-message-label">AI</div>
                <div className="chat-message-bubble chat-message-bubble--loading">
                  Thinking...
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </section>

      <footer className="chat-input-bar">
        {messages.length > 0 && (
          // <button
          //   className="clear-chat-btn"
          //   onClick={() => setMessages([])}
          //   title="Clear chat"
          // >
          <button
            className="clear-chat-btn"
            onClick={() => {
              setMessages([]);
              if (document) localStorage.removeItem(storageKey(document.document_id));
            }}
            title="Clear chat"
          >
            Clear
          </button>
        )}
        <input
          type="text"
          placeholder={
            canAsk ? "Ask a question..." : "Select a ready document to ask questions"
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!canAsk}
          className="chat-input"
        />
        <button
          className="send-btn"
          disabled={!canAsk || !input.trim()}
          onClick={handleSend}
        >
          Send
        </button>
      </footer>
    </>
  );
}

export default ChatWindow;
