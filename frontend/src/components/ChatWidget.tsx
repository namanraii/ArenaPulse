import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Send,
  MessageSquare,
  X,
  Sparkles,
} from 'lucide-react';
import { useSpeech } from '../hooks/useSpeech';
import { api } from '../services/api';
import { LANGUAGES } from '../utils/constants';
import type { ChatResult } from '../types';

interface ChatWidgetProps {
  language: string;
  voiceEnabled?: boolean;
}

export function ChatWidget({
  language,
  voiceEnabled = false,
}: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<
    Array<{ role: 'user' | 'assistant'; text: string; sources?: unknown[] }>
  >([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatLang, setChatLang] = useState(language);
  const [voiceOut, setVoiceOut] = useState(voiceEnabled);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fabRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setVoiceOut(voiceEnabled);
  }, [voiceEnabled]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      fabRef.current?.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleFocusTrap = (e: KeyboardEvent) => {
      if (e.key !== 'Tab' || !dialogRef.current) return;
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        'button, textarea, select, [href], [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', handleFocusTrap);
    return () => document.removeEventListener('keydown', handleFocusTrap);
  }, [isOpen]);

  const speech = useSpeech(chatLang);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (speech.transcript && speech.isListening === false) {
      setInput(speech.transcript);
    }
  }, [speech.transcript, speech.isListening]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text) return;
    setInput('');
    setError(null);
    setMessages((m) => [...m, { role: 'user', text }]);
    setLoading(true);
    try {
      const result: ChatResult = await api.chat(text, chatLang);
      setMessages((m) => [
        ...m,
        { role: 'assistant', text: result.response, sources: result.sources },
      ]);
      if (voiceOut) {
        speech.speak(result.response);
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to send message';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [input, chatLang, voiceOut, speech]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
    if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const toggleMic = () => {
    if (speech.isListening) {
      speech.stopListening();
    } else {
      speech.startListening();
    }
  };

  return (
    <>
      {!isOpen && (
        <button
          ref={fabRef}
          className="fab chat-fab"
          onClick={() => setIsOpen(true)}
          aria-label="Open chat"
        >
          <MessageSquare size={24} />
        </button>
      )}
      {isOpen && (
        <div
          ref={dialogRef}
          className="chat-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="chat-title"
          aria-describedby="chat-desc"
        >
          <div className="chat-header">
            <div>
              <strong id="chat-title">ArenaPulse Concierge</strong>
              <span id="chat-desc" className="chat-status">
                {speech.supported ? 'Voice enabled' : 'Text only'}
              </span>
            </div>
            <div className="chat-controls">
              <select
                value={chatLang}
                onChange={(e) => setChatLang(e.target.value)}
                aria-label="Chat language"
              >
                {Object.entries(LANGUAGES).map(([code, name]) => (
                  <option key={code} value={code}>
                    {name}
                  </option>
                ))}
              </select>
              <button
                className={voiceOut ? 'active' : ''}
                onClick={() => setVoiceOut((v) => !v)}
                aria-label={
                  voiceOut ? 'Disable voice output' : 'Enable voice output'
                }
                title="Voice output"
              >
                {voiceOut ? <Volume2 size={16} /> : <VolumeX size={16} />}
              </button>
              <button onClick={() => setIsOpen(false)} aria-label="Close chat">
                <X size={18} />
              </button>
            </div>
          </div>
          <div
            className="chat-messages"
            role="log"
            aria-live="polite"
            aria-atomic="false"
          >
            {messages.length === 0 && (
              <div className="chat-empty">
                <Sparkles size={32} />
                <p>Ask about routes, restrooms, transit, or match info.</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`chat-bubble ${msg.role}`}>
                <p>{msg.text}</p>
                {msg.sources && msg.sources.length > 0 && (
                  <span className="source-chip">Grounded</span>
                )}
              </div>
            ))}
            {loading && (
              <div className="chat-bubble assistant">
                <span className="typing">...</span>
              </div>
            )}
            {error && (
              <div className="chat-bubble assistant text-red-500">
                <p>{error}</p>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <div className="chat-input-row">
            {speech.supported && (
              <button
                className={`mic-btn ${speech.isListening ? 'listening' : ''}`}
                onMouseDown={speech.startListening}
                onMouseUp={speech.stopListening}
                onTouchStart={speech.startListening}
                onTouchEnd={speech.stopListening}
                onKeyDown={(e) => {
                  if (e.key === ' ' || e.key === 'Enter') {
                    e.preventDefault();
                    toggleMic();
                  }
                }}
                aria-label={
                  speech.isListening
                    ? 'Listening... release to stop'
                    : 'Press to speak'
                }
                aria-pressed={speech.isListening}
              >
                {speech.isListening ? <MicOff size={20} /> : <Mic size={20} />}
              </button>
            )}
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type or hold microphone..."
              rows={1}
              aria-label="Message"
            />
            <button onClick={send} aria-label="Send message">
              <Send size={18} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
