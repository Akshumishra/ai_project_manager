import { useCallback, useEffect, useRef, useState } from 'react';
import api, { getAccessToken } from '../../../shared/api/api';
import { API } from '../../../shared/config/config';


export function useDocument() {
  const [docId, setDocId] = useState(null);
  const [documentData, setDocumentData] = useState(null);
  const [status, setStatus] = useState('Not connected');
  const [syncStatus, setSyncStatus] = useState('Saved'); // 'Saved', 'Saving', 'Error'
  const [role, setRole] = useState('viewer');

  const lastSnapshotRef = useRef('');
  const isTypingRef = useRef(false);
  const isSelectingRef = useRef(false);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const debounceTimersRef = useRef(new Map());

  // ── Load document (REST fallback) ─────────────────────────────────
  const loadDocument = useCallback(async (id) => {
    const targetId = id ?? docId;
    if (!targetId) return null;
    try {
      const res = await api.get(`/api/documents/${targetId}`);
      const data = res.data;
      const dataWithLocalIds = {
        ...data,
        blocks: (data.blocks || []).map(b => ({ ...b, localId: b.block_id }))
      };
      setDocumentData(dataWithLocalIds);
      lastSnapshotRef.current = JSON.stringify(dataWithLocalIds);
      setDocId(targetId);
      return dataWithLocalIds;
    } catch (e) {
      console.error('Failed to load document:', e);
      setStatus('Disconnected');
      return null;
    }
  }, [docId]);

  // ── WebSocket Connectivity ─────────────────────────────────────────
  const connectWebSocketRef = useRef(null);

  const connectWebSocket = useCallback((targetId, accessToken) => {
    if (socketRef.current) {
      socketRef.current.onclose = null; // Prevent reconnect loop from the old socket
      socketRef.current.close(1000, "Session replaced locally");
    }

    const wsBase = API.replace(/^http/, 'ws');
    const wsUrl = `${wsBase}/ws/${targetId}?token=${accessToken}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setStatus('Connected (Real-time)');
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      switch (message.type) {
        case 'init':
          setRole(message.role);
          const blocks = (message.data?.blocks || []).map(b => ({ ...b, localId: b.block_id }));
          const dataWithLocalIds = { ...message.data, blocks };
          setDocumentData(dataWithLocalIds);
          lastSnapshotRef.current = JSON.stringify(dataWithLocalIds);
          break;
          
        case 'update':
          console.log('[WS UPDATE] Received:', message);
          setDocumentData(prev => {
            if (!prev) return prev;
            const existingBlock = prev.blocks.find(b => b.block_id === message.block_id);
            const serverTimestampMs = message.timestamp * 1000;
            
            if (existingBlock && existingBlock.last_edited && existingBlock.last_edited > serverTimestampMs) {
              return prev; 
            }
            
            return {
              ...prev,
              blocks: prev.blocks.map(b =>
                b.block_id === message.block_id
                  ? { ...b, content: message.content, type: message.block_type }
                  : b
              )
            };
          });
          break;
          
        case 'insert':
          console.log('[WS INSERT] Received:', message);
          setDocumentData(prev => {
            if (!prev) return prev;
            if (prev.blocks.some(b => b.block_id === message.block.block_id)) return prev;
            
            const matchingTemp = prev.blocks.find(b => 
              (message.client_id && b.block_id === message.client_id) || 
              (!message.client_id && String(b.block_id).startsWith('temp_') && b.position_key === message.block.position_key && b.type === message.block.type)
            );

            let nextBlocks;
            if (matchingTemp) {
              nextBlocks = prev.blocks.map(b => 
                b.block_id === matchingTemp.block_id 
                  ? { ...message.block, localId: b.localId, _focusOnMount: b._focusOnMount, _cursorAt: b._cursorAt } 
                  : b
              );
            } else {
              const newBlock = { ...message.block, localId: message.block.block_id };
              nextBlocks = [...prev.blocks, newBlock];
            }
            
            nextBlocks.sort((a, b) => parseFloat(a.position_key) - parseFloat(b.position_key));
            return { ...prev, blocks: nextBlocks };
          });
          break;

        case 'delete':
          console.log('[WS DELETE] Received:', message);
          setDocumentData(prev => {
            if (!prev) return prev;
            return {
              ...prev,
              blocks: prev.blocks.filter(b => b.block_id !== message.block_id)
            };
          });
          break;

        case 'error':
          if (message.message.includes('View-only')) {
            setRole('viewer');
          } else {
            setSyncStatus('Error');
          }
          break;
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket disconnected', event.code);
      if (event.code === 1000 || event.code === 1008) {
        setStatus('Disconnected');
        return;
      }
      
      setStatus('Reconnecting...');
      const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
      reconnectTimeoutRef.current = setTimeout(async () => {
        reconnectAttemptsRef.current++;
        const token = getAccessToken();
        if (connectWebSocketRef.current) {
          connectWebSocketRef.current(targetId, token);
        }
      }, delay);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }, []);

  useEffect(() => {
    connectWebSocketRef.current = connectWebSocket;
  }, [connectWebSocket]);

  const disconnectWebSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.onclose = null;
      socketRef.current.close(1000, "User left editor");
      socketRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    setStatus('Disconnected');
  }, []);

  useEffect(() => {
    return () => disconnectWebSocket();
  }, [disconnectWebSocket]);

  // ── Block CRUD ────────────────────────────────────────────────────
  const updateBlock = useCallback((id, content, type, forceSync = false) => {
    setDocumentData(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        blocks: prev.blocks.map(b =>
          b.block_id === id ? { ...b, content, type, last_edited: Date.now() } : b
        ),
      };
    });

    if (String(id).startsWith('temp_')) return;

    const performSync = async () => {
      if (socketRef.current?.readyState === WebSocket.OPEN && role === 'editor') {
        socketRef.current.send(JSON.stringify({
          type: 'edit',
          block_id: id,
          content,
          block_type: type
        }));
        setSyncStatus('Saved');
      } else if (role === 'editor') {
        try {
          await api.patch(`/api/block/${id}`, { content, type });
          setSyncStatus('Saved');
        } catch (err) {
          console.error('REST update failure:', err);
          setSyncStatus('Error');
        }
      }
    }

    if (forceSync) {
      if (debounceTimersRef.current.has(id)) {
        clearTimeout(debounceTimersRef.current.get(id));
        debounceTimersRef.current.delete(id);
      }
      setSyncStatus('Saving');
      performSync();
      return;
    }

    setSyncStatus('Saving');
    if (debounceTimersRef.current.has(id)) {
      clearTimeout(debounceTimersRef.current.get(id));
    }

    const timer = setTimeout(async () => {
      debounceTimersRef.current.delete(id);
      performSync();
    }, 500); 
    
    debounceTimersRef.current.set(id, timer);
  }, [role]);

  const deleteBlock = useCallback(async (id) => {
    try {
      await api.delete(`/api/block/${id}`);
      setDocumentData(prev => {
        if (!prev) return prev;
        const blocks = prev.blocks.filter(b => b.block_id !== id);
        const next = { ...prev, blocks };
        lastSnapshotRef.current = JSON.stringify(next);
        return next;
      });
    } catch (err) {
      console.error('Failed to delete block:', err);
    }
  }, []);

  const addBlockAfter = useCallback(async (currentDocId, prevBlockId, nextBlockId, content = '', type = 'paragraph', clientId = null, positionKey = null) => {
    try {
      const res = await api.post(`/api/block/documents/${currentDocId}`, {
        content,
        type,
        prev_block_id: prevBlockId,
        next_block_id: nextBlockId,
        client_id: clientId,
        position_key: positionKey
      });
      return res.data;
    } catch (err) {
      console.error('Failed to add block:', err);
      return null;
    }
  }, []);

  const createNewDocument = useCallback(async (title = 'Untitled Document') => {
    try {
      const res = await api.post('/api/documents', { title });
      return res.data;
    } catch (err) {
      console.error('Failed to create document:', err);
      throw err;
    }
  }, []);

  return {
    docId, setDocId,
    documentData, setDocumentData,
    lastSnapshotRef,
    status,
    syncStatus,
    role,
    isTypingRef,
    isSelectingRef,
    loadDocument,
    updateBlock,
    deleteBlock,
    addBlockAfter,
    connectWebSocket,
    createNewDocument,
    disconnectWebSocket
  };
}
