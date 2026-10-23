import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { messageStore } from '../src/message/messageStore';
import { MessageContextRef, Message, MessageThread } from '../src/message/types';
import { subscribeToThread, isMessageSyncConfigured } from '../src/message/messageSync';
import { getCurrentUserId } from '../services/firebaseAuth';
import { Z_LAYERS } from '../constants/zLayers';

interface MessageThreadPanelProps {
  context: MessageContextRef;
  title?: string;
  subtitle?: string;
  onClose: () => void;
}

const formatTime = (timestamp: number) =>
  new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

export const MessageThreadPanel: React.FC<MessageThreadPanelProps> = ({ context, title, subtitle, onClose }) => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  const refreshMessages = () => {
    messageStore.pruneExpired();
    setMessages(messageStore.getMessages(context));
  };

  const thread = messageStore.getThread(context);
  const threadStatus = thread?.metadata.status || 'active';
  const isReadOnly = threadStatus === 'closed' || threadStatus === 'locked';
  const closedReason = thread?.metadata.closedReason;

  // Auto-scroll to newest message (top of reversed list)
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [messages]);

  // Keyboard accessibility: Escape to close
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Speech recognition setup (Web Speech API - uses phone's native STT)
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput(prev => prev ? `${prev} ${transcript}` : transcript);
      setIsListening(false);
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    return () => recognitionRef.current?.stop();
  }, []);

  useEffect(() => {
    refreshMessages();
  }, [context]);

  // Sprint M3: Real-time updates from Firestore
  // WSP NOTE: Subscribe to remote changes, merge with local state
  useEffect(() => {
    if (!isMessageSyncConfigured()) {
      console.log('[MessageThreadPanel] Firestore not configured - local only');
      return;
    }

    const unsubscribe = subscribeToThread(context, (remoteThread: MessageThread | null) => {
      if (!remoteThread) return;

      // Merge remote messages with local store
      // Remote messages that don't exist locally will be added
      const localThread = messageStore.getThread(context);
      const localMessageIds = new Set(localThread?.messages.map(m => m.id) || []);

      let hasNewMessages = false;
      for (const remoteMsg of remoteThread.messages) {
        if (!localMessageIds.has(remoteMsg.id)) {
          // New message from another device - add to local store
          console.log('[MessageThreadPanel] New remote message:', remoteMsg.id);
          hasNewMessages = true;
        }
      }

      // If we have new messages, refresh the UI
      if (hasNewMessages || remoteThread.messages.length !== (localThread?.messages.length || 0)) {
        // Update local store with merged data
        // For simplicity, just refresh from the store (which has the local copy)
        // In production, we'd do proper merge logic
        refreshMessages();
      }
    });

    return () => {
      if (unsubscribe) {
        console.log('[MessageThreadPanel] Unsubscribing from thread updates');
        unsubscribe();
      }
    };
  }, [context]);

  const handleMicClick = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('Speech not supported on this device');
      return;
    }
    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      try {
        recognitionRef.current?.start();
        setIsListening(true);
      } catch {
        setError('Failed to start speech recognition');
      }
    }
  };

  const handleSend = () => {
    if (!input.trim()) return;

    try {
      const authorId = getCurrentUserId();
      if (!authorId) throw new Error('Sign in before sending a message.');
      messageStore.addMessage({
        context,
        authorId,
        authorDisplayName: 'You',
        text: input.trim(),
      });
      setInput('');
      setError(null);
      refreshMessages();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      console.error('[MessageThreadPanel] Send error:', err);
    }
  };

  return (
    <div
      className="fixed inset-0"
      style={{ zIndex: Z_LAYERS.messagePanel }}
    >
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <motion.div
        className="absolute inset-x-0 top-0 bg-gray-950/95 rounded-b-3xl shadow-2xl flex flex-col"
        style={{
          maxHeight: '85vh',
          paddingTop: 'max(16px, env(safe-area-inset-top))'
        }}
        initial={{ y: '-100%' }}
        animate={{ y: 0 }}
        exit={{ y: '-100%' }}
        transition={{ type: 'spring', stiffness: 260, damping: 30 }}
      >
        <div className="px-6 pt-5 pb-3 border-b border-white/10 flex items-center justify-between">
          <div className="flex-1">
            <p className="text-white font-semibold text-lg">{title || 'Message Board'}</p>
            {subtitle && <p className="text-white/60 text-sm">{subtitle}</p>}
            {isReadOnly && (
              <div className="mt-2 px-3 py-1.5 bg-amber-900/60 rounded-full inline-flex items-center gap-2">
                <span className="text-amber-300 text-xs font-semibold">
                  {threadStatus === 'closed' ? '🔒 SOLD / READ-ONLY' : '🔒 LOCKED'}
                </span>
                {closedReason && (
                  <span className="text-amber-400/70 text-xs">({closedReason})</span>
                )}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white text-2xl"
            aria-label="Close message board"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-center text-white/60 text-sm">No messages yet. Start the thread below.</p>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className="bg-gray-900/80 rounded-2xl p-3 text-white shadow-lg">
              <div className="flex justify-between text-xs text-white/60">
                <span>{msg.authorDisplayName || 'Anonymous'}</span>
                <span>{formatTime(msg.createdAt)}</span>
              </div>
              <p className="mt-1 text-sm whitespace-pre-wrap">{msg.text}</p>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div
          className="px-6 border-t border-white/10 bg-gray-950/95"
          style={{ paddingTop: '16px', paddingBottom: 'max(16px, env(safe-area-inset-bottom))' }}
        >
          {error && (
            <div className="mb-3 px-4 py-2 bg-red-900/60 rounded-lg text-red-200 text-sm">
              {error}
            </div>
          )}
          {isReadOnly ? (
            <div className="text-center py-4">
              <p className="text-white/60 text-sm">
                This thread is {threadStatus === 'closed' ? 'closed' : 'locked'}. No new messages allowed.
              </p>
              {closedReason && (
                <p className="text-white/40 text-xs mt-1">Reason: {closedReason}</p>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSend();
                }}
                placeholder={isListening ? 'Listening...' : 'Share info with nearby community...'}
                className="flex-1 rounded-2xl bg-gray-900/80 text-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/70"
              />
              <button
                onClick={handleMicClick}
                className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-colors ${
                  isListening ? 'bg-red-600 text-white animate-pulse' : 'bg-gray-700/80 text-white hover:bg-gray-600/80'
                }`}
                aria-label={isListening ? 'Stop listening' : 'Voice input'}
              >
                🎤
              </button>
              <button
                onClick={handleSend}
                className="px-4 h-12 rounded-2xl bg-blue-600 text-white font-semibold disabled:opacity-50 flex items-center justify-center"
                disabled={!input.trim()}
              >
                Send
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};
