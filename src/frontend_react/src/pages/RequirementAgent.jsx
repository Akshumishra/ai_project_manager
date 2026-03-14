import { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { marked } from "marked";
import {
  startRequirementAgentRequest,
  sendRequirementAgentMessage,
  getProjectRequest,
  DEFAULT_USER_ID,
} from "../api";
import { getActiveProject, setActiveProject, getUserBackground } from "../storage";

function isRequirementSpec(content) {
  return (
    typeof content === "string" &&
    content.includes("Requirement Specification") &&
    content.includes("Problem the Project Solves")
  );
}

function ChatMessage({ role, content }) {
  return (
    <div className={`message ${role === "assistant" ? "ai" : "user"}`}>
      <div className="bubble">{content}</div>
    </div>
  );
}

function CanvasPanel({ content }) {
  return (
    <section className="canvas-panel">
      <div className="canvas-header">
        <h2>Requirement Specification</h2>
      </div>
      <div
        className="canvas-body"
        dangerouslySetInnerHTML={{ __html: marked.parse(content) }}
      />
    </section>
  );
}

export default function RequirementAgent() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const storedProject = getActiveProject();
  const activeProjectId = searchParams.get("project_id") || storedProject.project_id;
  const savedKey = `req_saved_${activeProjectId}`;

  const [projectTitle, setProjectTitle] = useState(storedProject.project_title || "");
  const [projectDescription, setProjectDescription] = useState(storedProject.project_description || "");
  const [messages, setMessages] = useState([]);
  const [chatStatus, setChatStatus] = useState("Starting requirement conversation...");
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const [specContent, setSpecContent] = useState(null);

  const chatBoxRef = useRef(null);
  const initialLoadedRef = useRef(false);

  useEffect(() => {
    if (!activeProjectId) {
      navigate("/create-project");
      return;
    }

    async function loadProject() {
      setSending(true);
      try {
        if (!projectTitle) {
          const data = await getProjectRequest(activeProjectId);
          const title = data.project_title || "";
          const desc = data.project_description || "";
          setProjectTitle(title);
          setProjectDescription(desc);
          setActiveProject({ project_id: activeProjectId, project_title: title, project_description: desc });
        }
        await startInitialConversation();
      } catch {
        setChatStatus("Unable to load project details.");
      } finally {
        setSending(false);
      }
    }

    loadProject();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  function handleAIResponse(content) {
    if (isRequirementSpec(content)) {
      setChatStatus("Requirement specification ready. Review the canvas and continue chatting to refine.");
      setSpecContent(content);
    }
  }

  async function startInitialConversation() {
    if (initialLoadedRef.current) return;
    initialLoadedRef.current = true;

    setChatStatus("Agent is preparing the conversation...");
    setMessages([{ role: "assistant", content: "Typing..." }]);

    try {
      const background = getUserBackground(DEFAULT_USER_ID);
      const data = await startRequirementAgentRequest(activeProjectId, DEFAULT_USER_ID, background);

      // Edge case: Backend says we are already done
      if (data.status === "completed") {
        setChatStatus("Requirement gathering already complete. Redirecting...");
        setTimeout(() => navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`, { replace: true }), 500);
        return;
      }

      setMessages((_prev) => {
        const withoutTyping = _prev.filter((m) => m.content !== "Typing...");

        // Resumed session — history returned
        if (data.status === "resumed" || (data.messages && data.messages.length > 0)) {
          setChatStatus("Conversation resumed.");
          const history = data.messages || [];
          const lastAI = [...history].reverse().find((m) => m.role === "assistant");
          if (lastAI) handleAIResponse(lastAI.content);
          return history;
        }

        // Fresh start
        setChatStatus("Requirement conversation started.");
        handleAIResponse(data.content);
        return [...withoutTyping, { role: "assistant", content: data.content }];
      });

      if (data.saved) {
        setChatStatus("Requirement spec saved. Redirecting...");
        setTimeout(() => navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`), 500);
      }
    } catch (err) {
      console.error("Start Conversation Error:", err);
      setMessages([{
        role: "assistant",
        content: "Unable to start the requirement conversation. Check that the backend is running.",
      }]);
      setChatStatus("Could not start the conversation.");
    }
  }

  async function sendMessage() {
    const message = inputValue.trim();
    if (!message || !activeProjectId || sending) return;

    setSending(true);
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInputValue("");
    setMessages((prev) => [...prev, { role: "assistant", content: "Typing..." }]);

    try {
      const data = await sendRequirementAgentMessage(activeProjectId, message, DEFAULT_USER_ID);

      setMessages((prev) => {
        const withoutTyping = prev.filter((m) => m.content !== "Typing...");
        return [...withoutTyping, { role: "assistant", content: data.content }];
      });

      if (data.saved) {
        setChatStatus("Requirement specification saved! Redirecting...");
        setTimeout(() => navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`), 800);
      } else if (data.content) {
        setChatStatus("Requirement conversation in progress.");
        handleAIResponse(data.content);
      }
    } catch {
      setMessages((prev) => {
        const withoutTyping = prev.filter((m) => m.content !== "Typing...");
        return [
          ...withoutTyping,
          { role: "assistant", content: "Agent request failed. Confirm that the backend is running." },
        ];
      });
      setChatStatus("Communication error.");
    } finally {
      setSending(false);
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
            <div className="eyebrow">Requirement Agent</div>
            <h1 className="topbar-title">{projectTitle || "Requirement Gathering"}</h1>
            {projectDescription && <p className="topbar-subtitle">{projectDescription}</p>}
          </div>
          <div className="topbar-actions" />
        </div>
      </section>

      <div className={`layout ${specContent ? "with-canvas" : ""}`}>
        <section className="chat-panel">
          <div className="chat-header">
            <p>Project Conversation</p>
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
            <button
              className="send-btn"
              type="button"
              onClick={sendMessage}
              disabled={sending}
            >
              Send
            </button>
          </div>
        </section>

        {specContent && <CanvasPanel content={specContent} />}
      </div>
    </div>
  );
}
