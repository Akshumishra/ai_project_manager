import { useCallback, useRef, useEffect } from 'react';
import { getAccessToken } from '../api';
import { API } from '../config';

export function useWebSocket({ 
  onInit, 
  onUpdate, 
  onInsert, 
  onDelete, 
  onError, 
  setStatus 
}) {
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const connectWebSocketRef = useRef(null);

  const connectWebSocket = useCallback((targetId, accessToken) => {
    if (socketRef.current) {
      socketRef.current.onclose = null;
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
        case 'init':   onInit?.(message); break;
        case 'update': onUpdate?.(message); break;
        case 'insert': onInsert?.(message); break;
        case 'delete': onDelete?.(message); break;
        case 'error':  onError?.(message); break;
        default: break;
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
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectAttemptsRef.current++;
        const token = getAccessToken();
        connectWebSocketRef.current?.(targetId, token);
      }, delay);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }, [onInit, onUpdate, onInsert, onDelete, onError, setStatus]);

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
  }, [setStatus]);

  const send = useCallback((data) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  return { connectWebSocket, disconnectWebSocket, send };
}
