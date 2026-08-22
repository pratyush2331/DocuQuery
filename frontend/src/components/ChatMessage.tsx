import { ChatResponse } from "../services/api";
import SourceCard from "./SourceCard";
import RetrievedContext from "./RetrievedContext";

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
  isError?: boolean;
}

function ChatMessage({ message }: { message: ChatMessageData }) {
  const isUser = message.role === "user";

  return (
    <div className={`chat-message chat-message--${message.role}`}>
      <div className="chat-message-label">{isUser ? "You" : "AI"}</div>
      <div
        className={`chat-message-bubble ${
          message.isError ? "chat-message-bubble--error" : ""
        }`}
      >
        {message.text}
      </div>

      {!isUser && message.response && message.response.sources.length > 0 && (
        <div className="chat-message-sources">
          <div className="chat-message-sources-label">Sources</div>
          {message.response.sources.map((source) => (
            <SourceCard
              key={source.chunk_id}
              source={source}
              chunk={message.response!.retrieved_chunks.find(
                (c) => c.chunk_id === source.chunk_id
              )}
            />
          ))}
          <RetrievedContext chunks={message.response.retrieved_chunks} />
        </div>
      )}
    </div>
  );
}

export default ChatMessage;
