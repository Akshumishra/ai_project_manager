import { useCallback, useEffect, useRef, useState } from 'react';
import api, { getAccessToken } from '../api';
import { API } from '../config';
import { useWebSocket } from './useWebSocket';


export function useDocument() {
  const [docId, setDocId] = useState(null);
  const [documentData, setDocumentData] = useState(null);
  const [status, setStatus] = useState('Not connected');
  const [syncStatus, setSyncStatus] = useState('Saved'); // 'Saved', 'Saving', 'Error'
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState('viewer');

  const lastSnapshotRef = useRef('');
  const isTypingRef = useRef(false);
  const isSelectingRef = useRef(false);
  const debounceTimersRef = useRef(new Map());

  // ── Load document (REST fallback) ─────────────────────────────────
  const loadDocument = useCallback(async (id) => {
    const targetId = id ?? docId;
    if (!targetId) return null;
    setLoading(true);
    try {
      const res = await api.get(`/api/documents/${targetId}`);
      const data = res.data;
      const dataWithLocalIds = {
        ...data,
        blocks: (data.blocks || [])
          .map(b => ({ ...b, localId: b.block_id }))
          .sort((a, b) => parseFloat(a.position_key) - parseFloat(b.position_key))
      };
      setDocumentData(dataWithLocalIds);
      lastSnapshotRef.current = JSON.stringify(dataWithLocalIds);
      setDocId(targetId);
      return dataWithLocalIds;
    } catch (e) {
      console.error('Failed to load document:', e);
      setStatus('Disconnected');
      return null;
    } finally {
      setLoading(false);
    }
  }, [docId]);

  // ── WebSocket Connectivity ─────────────────────────────────────────
  const onInit = useCallback((message) => {
    setRole(message.role);
    const blocks = (message.data?.blocks || [])
      .map(b => ({ ...b, localId: b.block_id }))
      .sort((a, b) => parseFloat(a.position_key) - parseFloat(b.position_key));
    const dataWithLocalIds = { ...message.data, blocks };
    setDocumentData(dataWithLocalIds);
    lastSnapshotRef.current = JSON.stringify(dataWithLocalIds);
  }, []);

  const onUpdate = useCallback((message) => {
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
  }, []);

  const onInsert = useCallback((message) => {
    setDocumentData(prev => {
      if (!prev) return prev;
      if (prev.blocks.some(b => b.block_id === message.block.block_id)) return prev;
      
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

      const newBlock = { ...message.block, localId: message.block.block_id };
      const newBlocks = [...prev.blocks, newBlock];
      newBlocks.sort((a, b) => parseFloat(a.position_key) - parseFloat(b.position_key));
      return { ...prev, blocks: newBlocks };
    });
  }, []);

  const onDelete = useCallback((message) => {
    setDocumentData(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        blocks: prev.blocks.filter(b => b.block_id !== message.block_id)
      };
    });
  }, []);

  const onError = useCallback((message) => {
    if (message.message?.includes('View-only')) {
      setRole('viewer');
    } else {
      setSyncStatus('Error');
    }
  }, []);

  const { connectWebSocket, disconnectWebSocket, send } = useWebSocket({
    onInit, onUpdate, onInsert, onDelete, onError, setStatus
  });

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
      const sent = send({
        type: 'edit',
        block_id: id,
        content,
        block_type: type
      });

      if (sent) {
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
    loading,
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
