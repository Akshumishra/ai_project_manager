import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import CanvasPanel from '../components/agent/CanvasPanel';
import ChatBox from '../components/agent/ChatBox';
import { startRequirementAgentRequest, sendRequirementAgentMessage } from '../api';
import { getProjectContext, setAgentState, getAgentState } from '../utils/agent_storage';

export default function RequirementAgent() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [canvasContent, setCanvasContent] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const initAgent = async () => {
      try {
        const { userId, background } = getProjectContext(projectId);
        const savedState = getAgentState(projectId, 'requirement');
        
        if (savedState) {
          setMessages(savedState.messages || []);
          setCanvasContent(savedState.canvasContent || '');
        }

        const data = await startRequirementAgentRequest(projectId, userId, background);
        if (!savedState) {
          setMessages([{ role: 'assistant', content: data.message }]);
          setCanvasContent(data.canvas_content || '');
        }
      } catch (err) {
        console.error('Failed to start requirement agent:', err);
      }
    };
    initAgent();
  }, [projectId]);

  const handleSendMessage = async (text) => {
    setLoading(true);
    const newMessages = [...messages, { role: 'user', content: text }];
    setMessages(newMessages);

    try {
      const { userId } = getProjectContext(projectId);
      const data = await sendRequirementAgentMessage(projectId, text, userId);
      
      const updatedMessages = [...newMessages, { role: 'assistant', content: data.message }];
      setMessages(updatedMessages);
      setCanvasContent(data.canvas_content);
      
      setAgentState(projectId, 'requirement', {
        messages: updatedMessages,
        canvasContent: data.canvas_content
      });

      if (data.is_complete) {
        navigate(`/project/${projectId}/tech-doc`);
      }
    } catch (err) {
      console.error('Message failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="agent-page">
      <div className="agent-container">
        <ChatBox 
          messages={messages} 
          onSend={handleSendMessage} 
          loading={loading}
          title="Requirement Gathering Agent"
        />
        <CanvasPanel content={canvasContent} />
      </div>
    </div>
  );
}
