import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import DocPreview from '../components/agent/DocPreview';
import ChatBox from '../components/agent/ChatBox';
import { startTechDocAgentRequest, sendTechDocAgentMessage, saveTechDocRequest } from '../api';
import { getProjectContext, setAgentState, getAgentState } from '../utils/agent_storage';

export default function TechDocAgent() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [docMarkdown, setDocMarkdown] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const initAgent = async () => {
      try {
        const { userId } = getProjectContext(projectId);
        const savedState = getAgentState(projectId, 'techdoc');
        
        if (savedState) {
          setMessages(savedState.messages || []);
          setDocMarkdown(savedState.docMarkdown || '');
        }

        const data = await startTechDocAgentRequest(projectId, userId);
        if (!savedState) {
          setMessages([{ role: 'assistant', content: data.message }]);
          setDocMarkdown(data.document_markdown || '');
        }
      } catch (err) {
        console.error('Failed to start tech doc agent:', err);
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
      const data = await sendTechDocAgentMessage(projectId, text, docMarkdown, userId);
      
      const updatedMessages = [...newMessages, { role: 'assistant', content: data.message }];
      setMessages(updatedMessages);
      setDocMarkdown(data.document_markdown);
      
      setAgentState(projectId, 'techdoc', {
        messages: updatedMessages,
        docMarkdown: data.document_markdown
      });
    } catch (err) {
      console.error('Message failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDoc = async () => {
    setLoading(true);
    try {
      const { userId } = getProjectContext(projectId);
      await saveTechDocRequest(projectId, docMarkdown, userId);
      navigate(`/project/${projectId}/add-member`);
    } catch (err) {
      console.error('Save failed:', err);
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
          title="Technical Documentation Agent"
        />
        <DocPreview 
          content={docMarkdown} 
          onSave={handleSaveDoc}
          loading={loading}
        />
      </div>
    </div>
  );
}
