import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Send,
  MessageSquare,
  X,
  Globe,
  Sparkles,
} from 'lucide-react'
import { useSpeech } from '../hooks/useSpeech'
import { api } from '../services/api'
import { LANGUAGES } from '../utils/constants'
import type { ChatResult } from '../types'

export function ChatWidget({ language }: { language: string }) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string; sources?: unknown[] }>>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [chatLang, setChatLang] = useState(language)
  const [voiceOut, setVoiceOut] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fabRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50)
    } else {
      fabRef.current?.focus()
    }
  }, [isOpen])

  const speech = useSpeech(chatLang)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (speech.transcript && speech.isListening === false) {
      setInput(speech.transcript)
    }
  }, [speech.transcript, speech.isListening])

  const send = useCallback(async () => {
    const text = input.trim()
    if (!text) return
    setInput('')
    setError(null)
    setMessages((m) => [...m, { role: 'user', text }])
    setLoading(true)
    try {
      const result: ChatResult = await api.chat(text, chatLang)
      setMessages((m) => [...m, { role: 'assistant', text: result.response, sources: result.sources }])
      if (voiceOut) {
        speech.speak(result.response)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to send message')
    } finally {
      setLoading(false)
    }
  }, [input, chatLang, voiceOut, speech])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
    if (e.key === 'Escape') {
      setIsOpen(false)
    }
  }

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
        <div className="chat-panel" role="dialog" aria-modal="true" aria-label="Concierge chat">
          <div className="chat-header">
            <div>
              <strong>ArenaPulse Concierge</strong>
              <span className="chat-status">
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
                aria-label={voiceOut ? 'Disable voice output' : 'Enable voice output'}
                title="Voice output"
              >
                {voiceOut ? <Volume2 size={16} /> : <VolumeX size={16} />}
              </button>
              <button onClick={() => setIsOpen(false)} aria-label="Close chat">
                <X size={18} />
              </button>
            </div>
          </div>
          <div className="chat-messages" role="log" aria-live="polite" aria-atomic="false">
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
                aria-label={speech.isListening ? 'Listening...' : 'Hold to speak'}
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
  )
}
