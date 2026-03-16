import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { marked } from "marked";
import {
  startRequirementAgentRequest,
  sendRequirementAgentMessage,
  getProjectRequest,
  completeRequirementStepRequest,
} from "../api";
import { getActiveProject, setActiveProject, getUserBackground } from "../utils/storage";
import { useAuth } from "../context/AuthContext";

function ChatMessage({ role, content }) {
  const docMarker = "— Requirement Specification";

  if (role === "assistant" && content.includes(docMarker)) {
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
              Requirement Specification has been updated in the canvas.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (content === "...") {
    return (
      <div className="message ai">
        <div className="bubble">
          <div className="spinner-sm"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`message ${role === "assistant" ? "ai" : "user"}`}>
      <div className="bubble">
        {role === "assistant" ? <div dangerouslySetInnerHTML={{ __html: marked.parse(content) }} /> : content}
      </div>
    </div>
  );
}

export default function RequirementAgentPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const initRef = useRef(false);

  const storedProject = getActiveProject();
  const activeProjectId = searchParams.get("project_id") || storedProject.project_id;

  const [projectTitle, setProjectTitle] = useState(storedProject.project_title || "");
  const [messages, setMessages] = useState([]);
  const [chatStatus, setChatStatus] = useState("Initializing agent...");
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [documentMarkdown, setDocumentMarkdown] = useState("");
  const [isCompleting, setIsCompleting] = useState(false);

  const chatBoxRef = useRef(null);
  const pollingIntervalRef = useRef(null);

  // 1. Initialization logic - Fixed to run once using initRef
  useEffect(() => {
    if (!activeProjectId || !user?.id || initRef.current) return;
    initRef.current = true;

    const init = async () => {
      setChatStatus("Checking project status...");
      try {
        let currentTitle = projectTitle;

        // Always get latest project info
        const data = await getProjectRequest(activeProjectId);
        if (!currentTitle) {
          currentTitle = data.project_title || data.name || "My Project";
          setProjectTitle(currentTitle);
          setActiveProject({
            project_id: activeProjectId,
            project_title: currentTitle,
            project_description: data.project_description || data.description
          });
        }

        const background = getUserBackground(user.id);
        const res = await startRequirementAgentRequest(activeProjectId, user.id, background);

        if (res.status === "completed") {
          navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`);
          return;
        }

        const initialMessages = res.messages && res.messages.length > 0 ? res.messages : [{ role: "assistant", content: res.content }];
        setMessages(initialMessages);

        if (res.document) {
          setDocumentMarkdown(res.document);
        }

        // Handle Thinking persistence
        if (res.thinking) {
          setChatStatus("Assistant is thinking...");
          setIsSending(true);
          startPolling();
        } else {
          setChatStatus("Ready to chat");
        }

      } catch (err) {
        console.error("Agent init failed:", err);
        setChatStatus("Failed to start agent.");
      }
    };

    init();

    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, [activeProjectId, user?.id]);

  // 2. Polling logic to handle "thinking" state persistence
  const startPolling = () => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const background = getUserBackground(user.id);
        const res = await startRequirementAgentRequest(activeProjectId, user.id, background);

        if (!res.thinking) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setIsSending(false);
          setChatStatus("Ready to chat");

          if (res.messages) {
            setMessages(res.messages);
          }
          if (res.status === "completed") {
            setChatStatus("Requirement gathering complete! Redirecting...");
            setTimeout(() => {
              navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`);
            }, 2000);
            return;
          }
          if (res.document) {
            setDocumentMarkdown(res.document);
          }
        }
      } catch (err) {
        console.error("Polling failed:", err);
      }
    }, 3000);
  };

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  const sendMessage = async () => {
    const text = inputValue.trim();
    if (!text || isSending || !user?.id) return;

    setIsSending(true);
    setInputValue("");
    const newMessages = [...messages, { role: "user", content: text }];
    setMessages([...newMessages, { role: "assistant", content: "..." }]);

    try {
      setChatStatus("Assistant is thinking...");
      const res = await sendRequirementAgentMessage(activeProjectId, text, user.id);

      setMessages([...newMessages, { role: "assistant", content: res.content }]);

      if (res.status === "completed") {
        setChatStatus("Requirement gathering complete! Redirecting...");
        setTimeout(() => {
          navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`);
        }, 2000);
      } else if (res.document) {
        setDocumentMarkdown(res.document);
        setChatStatus("Requirement specification updated.");
      } else {
        setChatStatus("Ready to chat");
      }
    } catch (err) {
      console.error("Message failed:", err);
      setMessages([...newMessages, { role: "assistant", content: "Error: Could not send message." }]);
      setChatStatus("Error occurred.");
    } finally {
      setIsSending(false);
    }
  };

  const handleCompletePhase = async () => {
    if (isCompleting) return;
    setIsCompleting(true);
    setChatStatus("Finalizing requirement phase...");
    try {
      await completeRequirementStepRequest(activeProjectId);
      navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`);
    } catch (err) {
      console.error("Failed to complete step:", err);
      setChatStatus("Error finalizing phase.");
    } finally {
      setIsCompleting(false);
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
            <span className="eyebrow">Requirement Gathering</span>
            <h1>{projectTitle}</h1>
          </div>
        </div>
        <div className="agent-status">
          <div className="h-stack gap-2">
            <span className={`status-dot ${isSending ? "busy" : "idle"}`}></span>
            <span style={{ fontSize: '14px', color: 'var(--gray-600)' }}>{chatStatus}</span>
          </div>
        </div>
      </header>

      <div className="workspace-body">
        <section className="chat-panel">
          <div className="messages" ref={chatBoxRef}>
            {messages.map((m, i) => <ChatMessage key={i} role={m.role} content={m.content} />)}
          </div>
          <div className="input-area">
            <input
              type="text"
              placeholder="Ask a question or suggest changes..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              disabled={isSending}
            />
            <button onClick={sendMessage} disabled={isSending || !inputValue.trim()}>Send</button>
          </div>
        </section>

        <section className="canvas-panel">
          <div className="canvas-header">
            <h2>Requirement Specification</h2>
            <div className="h-stack gap-2">
              <button
                className="btn btn-primary btn-sm"
                onClick={handleCompletePhase}
                disabled={isCompleting || !documentMarkdown}
              >
                {isCompleting ? "Completing..." : "Complete Phase"}
              </button>
            </div>
          </div>
          <div className="canvas-content">
            <div className="canvas-container">
              <div className="inner-canvas-scroller">
                {documentMarkdown ? (
                  <div dangerouslySetInnerHTML={{ __html: marked.parse(documentMarkdown) }} />
                ) : (
                  <p className="placeholder">The requirement specification will appear here once generated.</p>
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

