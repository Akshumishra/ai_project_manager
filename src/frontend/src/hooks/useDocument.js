import { useCallback, useEffect, useRef, useState } from 'react';
import api, { getAccessToken } from '../api';
import { API } from '../config';


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
            if (!prev) {
              console.log('[WS UPDATE] No previous document data');
              return prev;
            }
            const existingBlock = prev.blocks.find(b => b.block_id === message.block_id);
            const serverTimestampMs = message.timestamp * 1000;
            console.log(`[WS UPDATE] Comparing | Local: ${existingBlock?.last_edited || 'none'} | Server: ${serverTimestampMs}`);
            
            if (existingBlock && existingBlock.last_edited && existingBlock.last_edited > serverTimestampMs) {
              console.log('[WS UPDATE] Discarded: Local edit is newer');
              return prev; 
            }
            
            console.log('[WS UPDATE] Applied to local state!');
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
            // 1. If the block already exists by REAL ID, skip.
            if (prev.blocks.some(b => b.block_id === message.block.block_id)) return prev;
            
            // 2. If it was our own insertion (by client_id), replace our temp block with the real one.
            const hasTemp = message.client_id && prev.blocks.some(b => b.block_id === message.client_id);
            if (hasTemp) {
              return {
                ...prev,
                blocks: prev.blocks.map(b => 
                  b.block_id === message.client_id 
                    ? { ...message.block, localId: b.localId, _focusOnMount: b._focusOnMount, _cursorAt: b._cursorAt } 
                    : b
                )
              };
            }

            // 3. Otherwise, it's someone else's insertion. Add it and sort.
            const newBlock = { ...message.block, localId: message.block.block_id };
            const newBlocks = [...prev.blocks, newBlock];
            newBlocks.sort((a, b) => parseFloat(a.position_key) - parseFloat(b.position_key));
            return { ...prev, blocks: newBlocks };
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
      
      // Ignore normal closures or policy violations (e.g. invalid token, session replaced)
      if (event.code === 1000 || event.code === 1008) {
        console.log("WebSocket closed normally by backend. Not reconnecting.");
        setStatus('Disconnected');
        return; // Break the infinite loop
      }
      
      setStatus('Reconnecting...');
      console.log("Connection dropped abnormally, trying to reconnect...");
      
      const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
      reconnectTimeoutRef.current = setTimeout(async () => {
        reconnectAttemptsRef.current++;
        // On retry, use the current token from state/store
        const token = getAccessToken();
        if (connectWebSocketRef.current) {
          connectWebSocketRef.current(targetId, token);
        }
      }, delay);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      // Let onclose handle the reconnection logic
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
  const updateBlock = useCallback((id, content, type) => {
    // Optimistic local update
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

    // Per-block Debounced Sync
    setSyncStatus('Saving');
    if (debounceTimersRef.current.has(id)) {
      clearTimeout(debounceTimersRef.current.get(id));
    }

    const timer = setTimeout(async () => {
      debounceTimersRef.current.delete(id);
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
    }, 500); // 500ms debounce
    
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
