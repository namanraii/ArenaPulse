import { useState, useCallback, useRef, useEffect } from 'react'

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

interface SpeechState {
  isListening: boolean
  isSpeaking: boolean
  transcript: string
  error: string | null
  supported: boolean
}

export function useSpeech(language: string = 'en-US') {
  const [state, setState] = useState<SpeechState>({
    isListening: false,
    isSpeaking: false,
    transcript: '',
    error: null,
    supported: true,
  })

  const recognitionRef = useRef<any>(null)
  const synthRef = useRef<SpeechSynthesis | null>(null)

  useEffect(() => {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognitionAPI) {
      setState((s) => ({ ...s, supported: false, error: 'Voice input not supported in this browser.' }))
      return
    }
    const recognition = new SpeechRecognitionAPI()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = language

    recognition.onstart = () => setState((s) => ({ ...s, isListening: true, error: null }))
    recognition.onend = () => setState((s) => ({ ...s, isListening: false }))
    recognition.onresult = (event: any) => {
      let transcript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript
      }
      setState((s) => ({ ...s, transcript }))
    }
    recognition.onerror = (event: any) => {
      setState((s) => ({ ...s, error: event.error, isListening: false }))
    }

    recognitionRef.current = recognition
    synthRef.current = window.speechSynthesis

    return () => {
      recognition.stop()
    }
  }, [language])

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return
    setState((s) => ({ ...s, transcript: '' }))
    try {
      recognitionRef.current.start()
    } catch {
      // already started
    }
  }, [])

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return
    recognitionRef.current.stop()
  }, [])

  const speak = useCallback(
    (text: string) => {
      if (!synthRef.current) return
      synthRef.current.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = language
      utterance.onstart = () => setState((s) => ({ ...s, isSpeaking: true }))
      utterance.onend = () => setState((s) => ({ ...s, isSpeaking: false }))
      synthRef.current.speak(utterance)
    },
    [language]
  )

  const cancelSpeak = useCallback(() => {
    if (!synthRef.current) return
    synthRef.current.cancel()
    setState((s) => ({ ...s, isSpeaking: false }))
  }, [])

  return {
    ...state,
    startListening,
    stopListening,
    speak,
    cancelSpeak,
  }
}
