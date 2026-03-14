import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { marked } from "marked";
import {
  startRequirementAgentRequest,
  sendRequirementAgentMessage,
  getProjectRequest,
  saveRequirementDocRequest,
} from "../api";
import { getActiveProject, setActiveProject, getUserBackground } from "../utils/storage";
import { useAuth } from "../context/AuthContext";

function ChatMessage({ role, content }) {
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

  const storedProject = getActiveProject();
  const activeProjectId = searchParams.get("project_id") || storedProject.project_id;

  const [projectTitle, setProjectTitle] = useState(storedProject.project_title || "");
  const [messages, setMessages] = useState([]);
  const [chatStatus, setChatStatus] = useState("Initializing agent...");
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [specContent, setSpecContent] = useState("");

  const chatBoxRef = useRef(null);

  useEffect(() => {
    if (!activeProjectId) {
      navigate("/create-project");
      return;
    }

    if (!user?.id) return;

    const init = async () => {
      setLoading(true);
      try {
        if (!projectTitle) {
          const data = await getProjectRequest(activeProjectId);
          setProjectTitle(data.name || "My Project");
          setActiveProject({ 
            project_id: activeProjectId, 
            project_title: data.name, 
            project_description: data.description 
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
        
        // Extract spec if present in history
        const lastAI = [...initialMessages].reverse().find(m => m.role === "assistant");
        if (lastAI && lastAI.content.includes("Requirement Specification")) {
          setSpecContent(lastAI.content);
        }
        
        setChatStatus("Ready to chat");
      } catch (err) {
        console.error("Agent init failed:", err);
        setChatStatus("Failed to start agent.");
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [activeProjectId, navigate, projectTitle, user]);

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
      const res = await sendRequirementAgentMessage(activeProjectId, text, user.id);
      
      const finalMessages = [...newMessages, { role: "assistant", content: res.content }];
      setMessages(finalMessages);

      if (res.content.includes("Requirement Specification")) {
        setSpecContent(res.content);
      }

      if (res.saved) {
        setTimeout(() => navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`), 1500);
      }
    } catch (err) {
      console.error("Message failed:", err);
      setMessages([...newMessages, { role: "assistant", content: "Error: Could not send message." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="agent-workspace">
      <header className="workspace-header">
        <div className="project-info">
          <span className="eyebrow">Requirement Gathering</span>
          <h1>{projectTitle}</h1>
        </div>
        <div className="agent-status" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className="h-stack gap-2">
            <span className={`status-dot ${loading ? "busy" : "idle"}`}></span>
            <span style={{ fontSize: '14px', color: 'var(--gray-600)' }}>{chatStatus}</span>
          </div>
        </div>
      </header>

      <div className="workspace-body">
        <section className="chat-panel">
          <div className="messages" ref={chatBoxRef}>
            {messages.map((m, i) => <ChatMessage key={i} role={m.role} content={m.content} />)}
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
              placeholder="Ask a question or provide more details..." 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading || !inputValue.trim()}>Send</button>
          </div>
        </section>

        <section className="canvas-panel">
          <div className="canvas-header">
            <h2>Specification Canvas</h2>
          </div>
          <div className="canvas-content">
            <div className="canvas-container">
              <div className="inner-canvas-scroller">
                {specContent ? (
                  <div className="markdown-body" dangerouslySetInnerHTML={{ __html: marked.parse(specContent) }} />
                ) : (
                  <p className="placeholder">The requirement specification will appear here as the conversation progresses.</p>
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
