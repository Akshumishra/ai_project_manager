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

const EXTRACT_MARKER_REGEX = /^[—-]{1,5}\s*Requirement Specification\s*$/mi;
const EXTRACT_MARKER_TEXT = "— Requirement Specification";

function ChatMessage({ role, content }) {
  // Use multiline flag properly to match start of line
  const hasMarker = content.match(/^[—-]{1,5}\s*Requirement Specification\s*$/mi);

  if (role === "assistant" && hasMarker) {
    const parts = content.split(EXTRACT_MARKER_REGEX);
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
        <div className="bubble" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 20px' }}>
          <div className="thinking-dots">
            <span></span><span></span><span></span>
          </div>
          <span style={{ fontSize: '14px', color: 'var(--gray-500)', fontStyle: 'italic', fontWeight: '500' }}>Thinking...</span>
        </div>
      </div>
    );
  }

  // Heading fallback: only hide message if it looks like a complete spec document
  // (must start with # heading AND have at least 2 ## section headings)
  const markdownHeadingIndex = content.indexOf("# ");
  const sectionCount = (content.match(/^##\s/gm) || []).length;
  const looksLikeFullDoc = markdownHeadingIndex !== -1 && sectionCount >= 2 && (content.length - markdownHeadingIndex > 300);

  if (role === "assistant" && !hasMarker && looksLikeFullDoc) {
    const conversationalPart = content.slice(0, markdownHeadingIndex).trim();

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
  const [initializing, setInitializing] = useState(true);

  const chatBoxRef = useRef(null);
  const inputRef = useRef(null);
  const pollingIntervalRef = useRef(null);

  // 1. Initialization logic - Fixed to run once using initRef
  useEffect(() => {
    if (!activeProjectId || !user?.id || initRef.current) return;
    initRef.current = true;

    const init = async () => {
      setInitializing(true);
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
        const res = await startRequirementAgentRequest(activeProjectId, background);

        if (res.status === "completed") {
          navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`);
          return;
        }

        const initialMessages = res.messages && res.messages.length > 0 ? res.messages : [{ role: "assistant", content: res.content }];
        
        // Handle Thinking persistence in history
        if (res.thinking) {
          setChatStatus("Assistant is thinking...");
          setIsSending(true);
          
          // Add "..." message if not already present at the end
          if (initialMessages.length === 0 || initialMessages[initialMessages.length - 1].content !== "...") {
            setMessages([...initialMessages, { role: "assistant", content: "..." }]);
          } else {
            setMessages(initialMessages);
          }
          startPolling();
        } else {
          setMessages(initialMessages);
          setChatStatus("Ready to chat");
        }

        if (res.document) {
          setDocumentMarkdown(res.document);
        } else {
          const lastMsg = initialMessages[initialMessages.length - 1];
          const content = lastMsg?.content || "";
          if (lastMsg?.role === "assistant" && content.match(EXTRACT_MARKER_REGEX)) {
            const extracted = content.split(EXTRACT_MARKER_REGEX).slice(1).join("").trim();
            if (extracted) {
              setDocumentMarkdown(extracted);
            } else if (content.includes("# ")) {
              const fallbackParts = content.split("# ");
              if (fallbackParts.length > 1) {
                setDocumentMarkdown("# " + fallbackParts[1].trim());
              }
            }
          }
        }

      } catch (err) {
        console.error("Agent init failed:", err);
        setChatStatus("Failed to start agent.");
      } finally {
        setInitializing(false);
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
        const res = await startRequirementAgentRequest(activeProjectId, background);

        if (!res.thinking) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setIsSending(false);
          setChatStatus("Ready to chat");

          if (res.messages) {
            // Keep the "..." if still thinking, otherwise replace with full history
            if (res.thinking && (res.messages.length === 0 || res.messages[res.messages.length - 1].content !== "...")) {
                setMessages([...res.messages, { role: "assistant", content: "..." }]);
            } else {
                setMessages(res.messages);
            }
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
          } else if (res.messages && res.messages.length > 0) {
            const lastMsg = res.messages[res.messages.length - 1];
            // Resilient extraction
            const content = lastMsg?.content || "";
            if (lastMsg?.role === "assistant" && content.match(EXTRACT_MARKER_REGEX)) {
              const extracted = content.split(EXTRACT_MARKER_REGEX).slice(1).join("").trim();
              if (extracted) {
                 setDocumentMarkdown(extracted);
              } else {
                // Heading fallback: only if it looks like a full spec (2+ ## sections)
                const headingIdx = content.indexOf("# ");
                const sectionCount = (content.match(/^##\s/gm) || []).length;
                if (headingIdx !== -1 && sectionCount >= 2 && content.length - headingIdx > 300) {
                  setDocumentMarkdown("# " + content.split("# ").slice(1).join("# ").trim());
                }
              }
            }
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
      const res = await sendRequirementAgentMessage(activeProjectId, text);

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
        const markerRegex = /^[—-]{1,5}\s*Requirement Specification\s*$/mi;
        const hasMarker = res.content && res.content.match(markerRegex);
        const extracted = hasMarker
          ? res.content.split(markerRegex).slice(1).join("").trim()
          : null;
        if (extracted) {
          setDocumentMarkdown(extracted);
          setChatStatus("Requirement specification updated.");
        } else if (res.content) {
          // Heading fallback: only if it looks like a full spec (2+ ## sections)
          const headingIdx = res.content.indexOf("# ");
          const sectionCount = (res.content.match(/^##\s/gm) || []).length;
          if (headingIdx !== -1 && sectionCount >= 2 && res.content.length - headingIdx > 300) {
            setDocumentMarkdown("# " + res.content.split("# ").slice(1).join("# ").trim());
            setChatStatus("Requirement specification updated.");
          } else {
            setChatStatus("Ready to chat");
          }
        } else {
          setChatStatus("Ready to chat");
        }
      }
    } catch (err) {
      console.error("Message failed:", err);
      setMessages([...newMessages, { role: "assistant", content: "Error: Could not send message." }]);
      setChatStatus("Error occurred.");
    } finally {
      setIsSending(false);
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
      }
    }
  };

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    // Auto-expand height
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
            {initializing ? (
              <div className="message ai">
                <div className="bubble" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 20px' }}>
                  <div className="thinking-dots">
                    <span></span><span></span><span></span>
                  </div>
                  <span style={{ fontSize: '14px', color: 'var(--gray-500)', fontStyle: 'italic', fontWeight: '500' }}>Loading requirement agent...</span>
                </div>
              </div>
            ) : (
              messages.map((m, i) => <ChatMessage key={i} role={m.role} content={m.content} />)
            )}
          </div>
          <div className="input-area" style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', padding: '16px' }}>
            <textarea
              ref={inputRef}
              rows="1"
              placeholder="Ask a question or suggest changes..."
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={isSending}
              style={{
                flex: 1,
                resize: 'none',
                minHeight: '44px',
                maxHeight: '200px',
                padding: '12px 16px',
                borderRadius: '12px',
                border: '1px solid var(--gray-200)',
                background: isSending ? 'var(--gray-50)' : 'white',
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
              className={isSending ? "busy" : ""}
              style={{
                height: '44px',
                padding: '0 24px',
                background: isSending ? 'var(--brand-300)' : 'var(--brand-600)',
                color: 'white',
                opacity: 1,
                cursor: isSending ? 'wait' : (inputValue.trim() ? 'pointer' : 'not-allowed'),
                transition: 'all 0.2s ease'
              }}
            >
              Send
            </button>
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

