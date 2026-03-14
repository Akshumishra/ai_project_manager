import { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { marked } from "marked";
import {
  startTechDocAgentRequest,
  sendTechDocAgentMessage,
  saveTechDocRequest,
  DEFAULT_USER_ID,
} from "../api";

function ChatMessage({ role, content }) {
  return (
    <div className={`message ${role === "assistant" ? "ai" : "user"}`}>
      <div className="bubble">{content}</div>
    </div>
  );
}

export default function TechDoc() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const activeProjectId = searchParams.get("project_id");

  const [messages, setMessages] = useState([]);
  const [chatStatus, setChatStatus] = useState("Technical Document");
  const [documentMarkdown, setDocumentMarkdown] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);

  const chatBoxRef = useRef(null);
  const initialLoadedRef = useRef(false);

  useEffect(() => {
    if (activeProjectId && !initialLoadedRef.current) {
      initialLoadedRef.current = true;
      startInitialConversation();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  async function startInitialConversation() {
    setSending(true);
    setMessages([{ role: "assistant", content: "Drafting your technical document..." }]);

    try {
      const data = await startTechDocAgentRequest(activeProjectId, DEFAULT_USER_ID);

      if (data.status === "prerequisite_missing") {
        setChatStatus(data.message || "Prerequisite not met. Redirecting...");
        setTimeout(() => navigate(`${data.redirect}?project_id=${activeProjectId}`), 1000);
        return;
      }

      if (data.status === "completed") {
        setChatStatus("Technical document already complete. Redirecting...");
        setTimeout(() => navigate("/"), 1000);
        return;
      }

      setMessages([{ role: "assistant", content: data.content }]);
      if (data.document) setDocumentMarkdown(data.document);
      setChatStatus("Technical conversation started.");
    } catch {
      setMessages([{ role: "assistant", content: "Failed to start the technical conversation." }]);
      setChatStatus("Error loading draft.");
    } finally {
      setSending(false);
    }
  }

  async function sendMessage() {
    const message = inputValue.trim();
    if (!message || !activeProjectId || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInputValue("");
    setSending(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "Agent is thinking..." }]);

    try {
      const data = await sendTechDocAgentMessage(activeProjectId, message, documentMarkdown, DEFAULT_USER_ID);
      setMessages((prev) => {
        const withoutTyping = prev.filter((m) => m.content !== "Agent is thinking...");
        return [...withoutTyping, { role: "assistant", content: data.content }];
      });
      if (data.document) setDocumentMarkdown(data.document);
      setChatStatus(data.is_final ? "Document finalized. Ready to save." : "Reviewing tech stack choices.");
    } catch {
      setMessages((prev) => {
        const withoutTyping = prev.filter((m) => m.content !== "Agent is thinking...");
        return [...withoutTyping, { role: "assistant", content: "Error processing your request." }];
      });
    } finally {
      setSending(false);
    }
  }

  async function saveDocument() {
    setSaving(true);
    try {
      await saveTechDocRequest(activeProjectId, documentMarkdown, DEFAULT_USER_ID);
      alert("Technical Document saved successfully to the database!");
      window.location.href = "/";
    } catch {
      alert("Failed to save the technical document.");
    } finally {
      setSaving(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="shell">
      <section className="topbar">
        <div className="topbar-row">
          <div>
            <div className="eyebrow">Technical Document Agent</div>
            <h1 className="topbar-title">Technical Specification Editor</h1>
          </div>
          <div className="topbar-actions">
            <button className="secondary-btn" type="button" onClick={saveDocument} disabled={saving || !documentMarkdown}>
              {saving ? "Saving..." : "Save Document"}
            </button>
          </div>
        </div>
      </section>

      <div className="tech-doc-layout">
        <section className="chat-panel">
          <div className="chat-header">
            <p>{chatStatus}</p>
          </div>

          <div className="chat-box" ref={chatBoxRef}>
            {messages.map((msg, i) => (
              <ChatMessage key={i} role={msg.role} content={msg.content} />
            ))}
          </div>

          <div className="input-area">
            <input
              className="chat-input"
              placeholder="Type your message..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
            />
            <button className="send-btn" type="button" onClick={sendMessage} disabled={sending}>
              Send
            </button>
          </div>
        </section>

        <div className="doc-panel">
          <div className="doc-panel-header">
            <h2>Technical Document Preview</h2>
          </div>
          <div
            className="doc-preview"
            dangerouslySetInnerHTML={{
              __html: documentMarkdown
                ? marked.parse(documentMarkdown)
                : "<p style='color: var(--muted)'>The technical document will appear here once the agent generates a draft.</p>",
            }}
          />
        </div>
      </div>
    </div>
  );
}
