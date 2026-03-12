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

function SpecModal({ content, onConfirm, onEdit, confirming }) {
  return (
    <div className="spec-modal-overlay">
      <div className="spec-modal">
        <div className="spec-modal-header">
          <h2>Requirement Specification</h2>
          <p className="spec-modal-sub">
            Review the generated document below. Click <strong>Confirm &amp; Save</strong> to
            proceed, or <strong>Go Back &amp; Edit</strong> to continue chatting.
          </p>
        </div>

        <div
          className="spec-modal-body"
          dangerouslySetInnerHTML={{ __html: marked.parse(content) }}
        />

        <div className="spec-modal-footer">
          <button className="ghost-btn" onClick={onEdit} disabled={confirming}>
            Go Back &amp; Edit
          </button>
          <button className="primary-btn" onClick={onConfirm} disabled={confirming}>
            {confirming ? "Saving..." : "Confirm & Save"}
          </button>
        </div>
      </div>
    </div>
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
  const [chatStatus, setChatStatus] = useState("Ask the first message to start the requirement conversation.");
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);

  const [specContent, setSpecContent] = useState(null);
  const [confirming, setConfirming] = useState(false);

  const chatBoxRef = useRef(null);
  const initialLoadedRef = useRef(false);

  useEffect(() => {
    if (!activeProjectId) {
      navigate("/create-project");
      return;
    }

    if (sessionStorage.getItem(savedKey) === "true") {
      navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`, { replace: true });
      return;
    }

    async function loadProject() {
      if (!projectTitle) {
        try {
          const data = await getProjectRequest(activeProjectId);
          const title = data.project_title || "";
          setProjectTitle(title);
          setActiveProject({
            project_id: activeProjectId,
            project_title: title,
            project_description: data.project_description || "",
          });
        } catch {
          setChatStatus("Unable to load project details.");
        }
      }
      await startInitialConversation();
    }

    loadProject();

  }, []);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  function handleAIResponse(content) {

    if (isRequirementSpec(content)) {
      setChatStatus("Requirement specification ready. Please review and confirm.");
      setSpecContent(content);
    }
  }

  async function startInitialConversation() {
    if (initialLoadedRef.current) return;
    initialLoadedRef.current = true;

    setSending(true);
    setChatStatus("Agent is preparing the first requirement question.");
    setMessages((prev) => [...prev, { role: "assistant", content: "Typing..." }]);

    try {
      const background = getUserBackground(DEFAULT_USER_ID);
      const data = await startRequirementAgentRequest(activeProjectId, DEFAULT_USER_ID, background);

      setMessages((_prev) => {
        const withoutTyping = _prev.filter((m) => m.content !== "Typing...");

        if (data.messages && data.messages.length > 0) {
          setChatStatus("Requirement conversation loaded.");

          const lastAI = [...data.messages].reverse().find((m) => m.role === "assistant");
          if (lastAI) handleAIResponse(lastAI.content);
          return data.messages;
        }

        setChatStatus("Requirement conversation started.");
        handleAIResponse(data.content);
        return [...withoutTyping, { role: "assistant", content: data.content }];
      });

      if (data.saved) {
        sessionStorage.setItem(savedKey, "true");
        navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`);
      }
    } catch {
      setMessages((prev) => {
        const withoutTyping = prev.filter((m) => m.content !== "Typing...");
        return [
          ...withoutTyping,
          {
            role: "assistant",
            content: "Unable to start the requirement conversation. Confirm that the backend is running.",
          },
        ];
      });
      setChatStatus("Could not start the conversation.");
    } finally {
      setSending(false);
    }
  }

  async function sendMessage(overrideMessage) {
    const message = (overrideMessage ?? inputValue).trim();
    if (!message || !activeProjectId || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInputValue("");
    setSending(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "Typing..." }]);

    try {
      const data = await sendRequirementAgentMessage(activeProjectId, message, DEFAULT_USER_ID);

      setMessages((prev) => {
        const withoutTyping = prev.filter((m) => m.content !== "Typing...");
        return [...withoutTyping, { role: "assistant", content: data.content }];
      });

      setChatStatus(data.saved ? "Requirement specification saved successfully." : "Requirement conversation in progress.");

      if (data.saved) {
        sessionStorage.setItem(savedKey, "true");
        navigate(`/tech-doc?project_id=${encodeURIComponent(activeProjectId)}`);
      } else {
        handleAIResponse(data.content);
      }
    } catch {
      setMessages((prev) => {
        const withoutTyping = prev.filter((m) => m.content !== "Typing...");
        return [
          ...withoutTyping,
          {
            role: "assistant",
            content: "The agent request failed. Confirm that the backend is running and the project exists.",
          },
        ];
      });
    } finally {
      setSending(false);
    }
  }

  async function handleSpecConfirm() {
    setConfirming(true);
    setSpecContent(null);
    await sendMessage("yes, the specification looks correct, please save it");
    setConfirming(false);
  }

  function handleSpecEdit() {
    setSpecContent(null);
    setChatStatus("Requirement conversation in progress.");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <>
      {/* Confirmation Modal */}
      {specContent && (
        <SpecModal
          content={specContent}
          onConfirm={handleSpecConfirm}
          onEdit={handleSpecEdit}
          confirming={confirming}
        />
      )}

      <div className="shell">
        <section className="topbar">
          <div className="topbar-row">
            <div>
              <div className="eyebrow">Requirement Agent</div>
              <h1 className="topbar-title">Requirement Gathering Agent</h1>
            </div>
            <div className="topbar-actions" />
          </div>
        </section>

        <div className="layout">
          <aside className="sidebar-card">
            <h2>Current Project</h2>
            <div className="project-card">
              <strong>{projectTitle || "Untitled Project"}</strong>
              <p>{projectDescription || "The project is active and ready for requirement gathering."}</p>
            </div>
          </aside>

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
                disabled={sending || !!specContent}
              />
              <button
                className="send-btn"
                type="button"
                onClick={() => sendMessage()}
                disabled={sending || !!specContent}
              >
                Send
              </button>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
