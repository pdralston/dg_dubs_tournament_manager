import { useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { API_BASE_URL } from '../config/api';

interface UseWebSocketProps {
  tournamentId: number;
  onMatchUpdate: () => void;
}

export const useWebSocket = ({ tournamentId, onMatchUpdate }: UseWebSocketProps) => {
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // Create WebSocket connection
    const socket = io(API_BASE_URL, {
      transports: ['websocket', 'polling']
    });

    socketRef.current = socket;

    // Join tournament room
    socket.emit('join_tournament', { tournament_id: tournamentId });

    // Listen for match updates
    socket.on('match_updated', (data) => {
      console.log('Match updated:', data);
      if (data.tournament_id === tournamentId) {
        onMatchUpdate();
      }
    });

    // Handle connection events
    socket.on('connect', () => {
      console.log('Connected to WebSocket server');
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from WebSocket server');
    });

    // Cleanup on unmount
    return () => {
      socket.emit('leave_tournament', { tournament_id: tournamentId });
      socket.disconnect();
    };
  }, [tournamentId, onMatchUpdate]);

  return socketRef.current;
};
