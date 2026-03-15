import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { marked } from "marked";
import {
  startTechDocAgentRequest,
  sendTechDocAgentMessage,
  saveTechDocRequest,
} from "../api";
import { useAuth } from "../context/AuthContext";
import { getActiveProject } from "../utils/storage";

function ChatMessage({ role, content }) {
  const docMarker = content.includes("— Technical Specification") 
    ? "— Technical Specification" 
    : (content.includes("## Architecture Overview") ? "## Architecture Overview" : null);
  
  if (role === "assistant" && docMarker) {
    const parts = content.split(docMarker);
    const conversationalPart = parts[0].trim();
    
    return (
      <div className={`message ai`}>
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
  const [projectTitle, setProjectTitle] = useState(storedProject.project_title || "");
  const [documentMarkdown, setDocumentMarkdown] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const chatBoxRef = useRef(null);

  useEffect(() => {
    if (!activeProjectId) {
      navigate("/");
      return;
    }

    if (!user?.id) return;

    const init = async () => {
      setLoading(true);
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

        if (data.content || data.message) {
          const initialContent = data.content || data.message;
          setMessages([{ role: "assistant", content: initialContent }]);
        } else if (data.messages && data.messages.length > 0) {
          setMessages(data.messages);
        }

        if (data.document) setDocumentMarkdown(data.document);
        if (!projectTitle && storedProject.project_title) {
          setProjectTitle(storedProject.project_title);
        }
        setChatStatus("Technical document agent ready");
      } catch (err) {
        console.error("Tech Doc failed to start:", err);
        setChatStatus("Error loading draft.");
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [activeProjectId, navigate, user, projectTitle, storedProject.project_title]);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async () => {
    const text = inputValue.trim();
    if (!text || loading || !user?.id) return;

    setLoading(true);
    setInputValue("");
    const newMessages = [...messages, { role: "user", content: text }];
    setMessages([...newMessages, { role: "assistant", content: "..." }]);

    try {
      const res = await sendTechDocAgentMessage(activeProjectId, text, documentMarkdown, user.id);
      setMessages([...newMessages, { role: "assistant", content: res.content }]);
      if (res.document) setDocumentMarkdown(res.document);
    } catch (err) {
      console.error("Message failed:", err);
      setMessages([...newMessages, { role: "assistant", content: "Error: Process failed." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!user?.id) return;
    setSaving(true);
    try {
      await saveTechDocRequest(activeProjectId, documentMarkdown, user.id);
      navigate(`/project/${activeProjectId}`);
    } catch (err) {
      console.error("Save failed:", err);
      alert("Failed to save document.");
    } finally {
      setSaving(false);
    }
  };

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
          <span className={`status-dot ${loading ? "busy" : "idle"}`}></span>
          {chatStatus}
        </div>
      </header>

      <div className="workspace-body">
        <section className="chat-panel">
          <div className="messages" ref={chatBoxRef}>
            {messages.map((m, i) => (
              <ChatMessage key={i} role={m.role} content={m.content} />
            ))}
            {loading && (
              <div className="message ai">
                <div className="bubble">
                  <div className="spinner-sm"></div>
                </div>
              </div>
            )}
          </div>
          <div className="input-area">
            <input
              type="text"
              placeholder="Suggest edits or ask about the technical design..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading || !inputValue.trim()}>
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
                disabled={saving}
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
                  <p className="placeholder">The technical document will appear here.</p>
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
