import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { marked } from "marked";
import {
  startTechDocAgentRequest,
  sendTechDocAgentMessage,
  saveTechDocRequest,
  generateTasksRequest,
} from "../api";
import { useAuth } from "../context/AuthContext";
import { getActiveProject } from "../utils/storage";

const TECH_DOC_MARKER_REGEX = /^[—-]{1,5}\s*Technical Specification\s*$/mi;
const ARCH_OVERVIEW_MARKER = "## Architecture Overview";

const extractTechDoc = (content) => {
  if (!content) return null;

  if (content.match(TECH_DOC_MARKER_REGEX)) {
    return content.split(TECH_DOC_MARKER_REGEX).slice(1).join("").trim();
  }

  if (content.includes(ARCH_OVERVIEW_MARKER)) {
    const parts = content.split(ARCH_OVERVIEW_MARKER);
    return ARCH_OVERVIEW_MARKER + "\n\n" + parts.slice(1).join(ARCH_OVERVIEW_MARKER).trim();
  }

  return null;
};

function ChatMessage({ role, content }) {
  if (!content) return null;
  const hasTechMarker = content.match(TECH_DOC_MARKER_REGEX);
  const hasArchMarker = content.includes(ARCH_OVERVIEW_MARKER);
  const docMarker = hasTechMarker || hasArchMarker;

  if (role === "assistant" && docMarker) {
    const parts = hasTechMarker ? content.split(TECH_DOC_MARKER_REGEX) : content.split(ARCH_OVERVIEW_MARKER);
    const conversationalPart = parts[0].trim();

    return (
      <div className="message ai">
        <div className="bubble">
          {conversationalPart && <div dangerouslySetInnerHTML={{ __html: marked.parse(conversationalPart) }} />}
          <div className="spec-notice" style={{
            marginTop: conversationalPart ? '12px' : '0',
            padding: '12px',
            borderRadius: '12px',
            border: '1px solid var(--brand-200)',
            background: 'var(--brand-50)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <span style={{ fontSize: '20px' }}>📄</span>
            <p style={{ margin: 0, fontSize: '14px', color: 'var(--brand-700)', fontWeight: '500' }}>
              Technical Specification has been updated in the canvas.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (content === "...") {
    return (
      <div className="message ai">
        <div className="bubble" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 20px' }}>
          <div className="thinking-dots">
            <span></span><span></span><span></span>
          </div>
          <span style={{ fontSize: '14px', color: 'var(--gray-500)', fontStyle: 'italic', fontWeight: '500' }}>Thinking...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`message ${role === "assistant" ? "ai" : "user"}`}>
      <div className="bubble">
        <div dangerouslySetInnerHTML={{ __html: marked.parse(content) }} />
      </div>
    </div>
  );
}

export default function TechDocPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const activeProjectId = searchParams.get("project_id");
  const storedProject = getActiveProject();

  const [messages, setMessages] = useState([]);
  const [chatStatus, setChatStatus] = useState("Preparing technical document...");
  const [projectTitle, setProjectTitle] = useState(storedProject?.project_title || "");
  const [documentMarkdown, setDocumentMarkdown] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [initializing, setInitializing] = useState(true);
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);

  const chatBoxRef = useRef(null);
  const inputRef = useRef(null);
  const initRef = useRef(false);
  const pollingIntervalRef = useRef(null);

  const startPolling = () => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const data = await startTechDocAgentRequest(activeProjectId, user?.id);
        if (data.status !== "thinking") {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setSending(false);
          setChatStatus("Ready");

          if (data.messages && data.messages.length > 0) {
            setMessages(data.messages);
            const reversedMessages = [...data.messages].reverse();
            for (const msg of reversedMessages) {
                if (msg.role === "assistant" && msg.content) {
                    const extracted = extractTechDoc(msg.content);
                    if (extracted) {
                        setDocumentMarkdown(extracted);
                        break;
                    }
                }
            }
          }
          if (data.document) {
            setDocumentMarkdown(data.document);
          }
        }
      } catch (err) {
        console.error("Tech Doc polling failed:", err);
      }
    }, 3000);
  };

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

  useEffect(() => {
    if (!activeProjectId || !user?.id || initRef.current) return;
    initRef.current = true;

    const init = async () => {
      setInitializing(true);
      try {
        const data = await startTechDocAgentRequest(activeProjectId, user.id);

        if (data.status === "prerequisite_missing") {
          navigate(`/requirement-agent?project_id=${activeProjectId}`);
          return;
        }

        if (data.status === "completed") {
          navigate("/");
          return;
        }

        if (data.thinking) {
          setChatStatus("Assistant is thinking...");
          setSending(true);
          startPolling();
        }

        if (data.content || data.message) {
          const initialContent = data.content || data.message;
          setMessages([{ role: "assistant", content: initialContent }]);
          const extracted = extractTechDoc(initialContent);
          if (extracted) setDocumentMarkdown(extracted);
        } else if (data.messages && data.messages.length > 0) {
          setMessages(data.messages);
          const reversedMessages = [...data.messages].reverse();
          for (const msg of reversedMessages) {
            if (msg.role === "assistant" && msg.content) {
              const extracted = extractTechDoc(msg.content);
              if (extracted) {
                setDocumentMarkdown(extracted);
                break;
              }
            }
          }
        }

        if (data.document) {
          setDocumentMarkdown(data.document);
        }

        if (data.project_title) {
          setProjectTitle(data.project_title);
        }

        if (!data.thinking) setChatStatus("Ready");
      } catch (err) {
        console.error("Tech Doc failed to start:", err);
        setChatStatus("Error loading draft.");
      } finally {
        setInitializing(false);
      }
    };

    init();
  }, [activeProjectId, user?.id, navigate]);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages, sending]);

  const sendMessage = async () => {
    const text = inputValue.trim();
    if (!text || sending || initializing || !user?.id) return;

    setSending(true);
    setInputValue("");
    const newMessages = [...messages, { role: "user", content: text }];
    setMessages([...newMessages, { role: "assistant", content: "..." }]);
    setChatStatus("Thinking...");

    try {
      const res = await sendTechDocAgentMessage(activeProjectId, text, documentMarkdown, user.id);
      
      if (res.thinking) {
          startPolling();
          return;
      }

      setMessages([...newMessages, { role: "assistant", content: res.content }]);
      if (res.document) {
        setDocumentMarkdown(res.document);
        setChatStatus("Document updated.");
      } else if (res.content) {
        const extracted = extractTechDoc(res.content);
        if (extracted) {
          setDocumentMarkdown(extracted);
          setChatStatus("Document updated.");
        } else {
          setChatStatus("Ready");
        }
      }
    } catch (err) {
      console.error("Message failed:", err);
      setMessages([...newMessages, { role: "assistant", content: "Error: Could not process request. Please try again." }]);
      setChatStatus("Error occurred.");
    } finally {
      if (!pollingIntervalRef.current) {
          setSending(false);
      }
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
      }
    }
  };

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSave = async () => {
    if (!user?.id || !documentMarkdown) return;
    setSaving(true);
    setChatStatus("Saving document...");
    try {
      await saveTechDocRequest(activeProjectId, documentMarkdown, user.id);
      setChatStatus("Document saved! Redirecting to task generation...");
      setTimeout(() => {
        navigate(`/project/${activeProjectId}/generating-tasks`);
      }, 1500);
    } catch (err) {
      console.error("Save failed:", err);
      setChatStatus("Failed to save document. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const isBusy = sending || saving || initializing;

  return (
    <div className="agent-workspace">
      <header className="workspace-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            className="btn-close"
            onClick={() => navigate('/')}
            style={{ fontSize: '24px', background: 'var(--gray-100)', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            &larr;
          </button>
          <div className="project-info">
            <span className="eyebrow">Technical Document</span>
            <h1>{projectTitle || "Project Technical Document"}</h1>
          </div>
        </div>
        <div className="agent-status">
          <div className="h-stack gap-2">
            <span className={`status-dot ${isBusy ? "busy" : "idle"}`}></span>
            <span style={{ fontSize: '14px', color: 'var(--gray-600)' }}>{chatStatus}</span>
          </div>
        </div>
      </header>

      <div className="workspace-body">
        <section className="chat-panel">
          <div className="messages" ref={chatBoxRef}>
            {initializing ? (
              <div className="message ai">
                <div className="bubble" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 20px' }}>
                  <div className="thinking-dots">
                    <span></span><span></span><span></span>
                  </div>
                  <span style={{ fontSize: '14px', color: 'var(--gray-500)', fontStyle: 'italic', fontWeight: '500' }}>Loading technical document...</span>
                </div>
              </div>
            ) : (
              messages.map((m, i) => (
                <ChatMessage key={i} role={m.role} content={m.content} />
              ))
            )}
          </div>
          <div className="input-area" style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', padding: '16px' }}>
            <textarea
              ref={inputRef}
              rows="1"
              placeholder="Suggest edits or ask about the technical design..."
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={isBusy}
              style={{
                flex: 1,
                resize: 'none',
                minHeight: '44px',
                maxHeight: '200px',
                padding: '12px 16px',
                borderRadius: '12px',
                border: '1px solid var(--gray-200)',
                background: isBusy ? 'var(--gray-50)' : 'white',
                fontFamily: 'inherit',
                fontSize: '15px',
                lineHeight: '1.5',
                overflowY: 'auto',
                transition: 'border-color 0.2s',
              }}
            />
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim()}
              style={{
                height: '44px',
                padding: '0 24px',
                background: sending ? 'var(--brand-300)' : 'var(--brand-600)',
                color: 'white',
                opacity: 1,
                cursor: sending ? 'wait' : (inputValue.trim() ? 'pointer' : 'not-allowed'),
                transition: 'all 0.2s ease'
              }}
            >
              Send
            </button>
          </div>
        </section>

        <section className="canvas-panel">
          <div className="canvas-header">
            <h2>Technical Document</h2>
            <div className="h-stack gap-2">
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSave}
                disabled={saving || isBusy || !documentMarkdown}
              >
                {saving ? "Saving..." : "Save Document"}
              </button>
            </div>
          </div>
          <div className="canvas-content">
            <div className="canvas-container">
              <div className="inner-canvas-scroller">
                {documentMarkdown ? (
                  <div dangerouslySetInnerHTML={{ __html: marked.parse(documentMarkdown) }} />
                ) : (
                  <p className="placeholder">The technical document will appear here once generated.</p>
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
