import { useState, useRef, useEffect } from "react";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesContainerRef = useRef(null);

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage, session_id: sessionId }),
      });

      if (!res.ok) {
        throw new Error(`Request failed (${res.status})`);
      }

      const data = await res.json();
      setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: err.message },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setMessages([]);
    setSessionId(null);
  }

  return (
    <div className="chat-container card">
      <div className="chat-header">
        <span className="chat-title">Chat with Agent</span>
        {messages.length > 0 && (
          <button className="clear-btn" onClick={handleClear}>
            Clear
          </button>
        )}
      </div>

      <div className="chat-messages" ref={messagesContainerRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            Ask something like "What is 4 + 9?" or "What time is it?"
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`chat-message chat-message-${msg.role}`}>
              <span className="chat-role">
                {msg.role === "user" ? "You" : msg.role === "error" ? "Error" : "Agent"}
              </span>
              <div className="chat-content">{msg.content}</div>
            </div>
          ))
        )}
        {loading && (
          <div className="chat-message chat-message-assistant">
            <span className="chat-role">Agent</span>
            <div className="chat-content chat-typing">Thinking...</div>
          </div>
        )}
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={loading}
          className="chat-input"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="chat-send-btn"
        >
          {loading ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
