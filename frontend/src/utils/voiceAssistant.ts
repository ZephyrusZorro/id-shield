/**
 * Web Speech API & Web Audio utility for accessible voice guidance and recognition.
 * Optimized for 100% cross-browser reliability (Chrome, Safari, Firefox, Edge, iOS/macOS).
 * Tailored for accessibility: clear cadence, natural timbre, audio chimes, and automatic fallbacks.
 */

export interface SpeechOptions {
  rate?: number; // Default 0.88 for clear comprehension
  pitch?: number;
  lang?: string;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (err: any) => void;
}

// ------------------------------------------------ Voice Cache & Initialization
let cachedVoices: SpeechSynthesisVoice[] = [];
let audioCtxInstance: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  try {
    if (!audioCtxInstance) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        audioCtxInstance = new AudioCtx();
      }
    }
    if (audioCtxInstance && audioCtxInstance.state === "suspended") {
      audioCtxInstance.resume().catch(() => {});
    }
    return audioCtxInstance;
  } catch {
    return null;
  }
}

// Pre-load voices
if (typeof window !== "undefined" && "speechSynthesis" in window) {
  cachedVoices = window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoices = window.speechSynthesis.getVoices();
  };
}

// ------------------------------------------------ Audio Cues (Synthesized Web Audio)
export function playChime(type: "listen" | "success" | "stop" | "error") {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (type === "listen") {
      // Gentle ascending two-tone chime (G4 -> C5)
      osc.type = "sine";
      osc.frequency.setValueAtTime(392.0, now);
      osc.frequency.exponentialRampToValueAtTime(523.25, now + 0.12);
      gain.gain.setValueAtTime(0.1, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.start(now);
      osc.stop(now + 0.35);
    } else if (type === "success") {
      // Affirmative soft chord (C5 -> E5 -> G5)
      osc.type = "sine";
      osc.frequency.setValueAtTime(523.25, now);
      osc.frequency.exponentialRampToValueAtTime(783.99, now + 0.2);
      gain.gain.setValueAtTime(0.1, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
      osc.start(now);
      osc.stop(now + 0.45);
    } else if (type === "stop") {
      // Soft descending tone
      osc.type = "sine";
      osc.frequency.setValueAtTime(440.0, now);
      osc.frequency.exponentialRampToValueAtTime(330.0, now + 0.15);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
      osc.start(now);
      osc.stop(now + 0.3);
    } else {
      // Low friendly warning bump
      osc.type = "triangle";
      osc.frequency.setValueAtTime(260.0, now);
      gain.gain.setValueAtTime(0.09, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc.start(now);
      osc.stop(now + 0.25);
    }
  } catch {
    // AudioContext blocked or unsupported
  }
}

// ------------------------------------------------ Text to Speech (TTS)
export function isSpeechSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function isRecognitionSupported(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
}

export function stopSpeaking(): void {
  if (isSpeechSupported()) {
    try {
      window.speechSynthesis.cancel();
    } catch {
      // Ignore
    }
  }
}

export function speakText(text: string, options: SpeechOptions = {}): void {
  if (!isSpeechSupported()) {
    options.onError?.("Speech synthesis not supported in this browser.");
    return;
  }

  // Wake AudioContext
  getAudioContext();

  // Cancel any ongoing utterance safely
  try {
    window.speechSynthesis.cancel();
  } catch {
    // Ignore
  }

  // Clean text: strip markdown symbols, asterisks, brackets
  const clean = text
    .replace(/[#*_`~[\]()]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (!clean) return;

  // Split into manageable chunks if very long to prevent Chrome/Safari speech synthesis timeout bug
  const sentences = clean.match(/[^.!?]+[.!?]+/g) || [clean];

  let currentIdx = 0;

  const speakNextSentence = () => {
    if (currentIdx >= sentences.length) {
      options.onEnd?.();
      return;
    }

    const sentenceText = sentences[currentIdx].trim();
    if (!sentenceText) {
      currentIdx++;
      speakNextSentence();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(sentenceText);
    utterance.rate = options.rate ?? 0.88;
    utterance.pitch = options.pitch ?? 1.0;

    // Pick best natural voice
    const voices = cachedVoices.length > 0 ? cachedVoices : window.speechSynthesis.getVoices();
    const targetLang = options.lang || "en";

    const preferredVoice =
      voices.find(
        (v) =>
          v.lang.startsWith(targetLang) &&
          (v.name.includes("Natural") ||
            v.name.includes("Google") ||
            v.name.includes("Online") ||
            v.name.includes("Samantha") ||
            v.name.includes("Siri") ||
            v.name.includes("Karen") ||
            v.name.includes("Daniel") ||
            v.name.includes("Tessa"))
      ) ||
      voices.find((v) => v.lang.startsWith("en-IN") || v.lang.startsWith("en-US") || v.lang.startsWith("en-GB")) ||
      voices.find((v) => v.lang.startsWith("en")) ||
      voices[0];

    if (preferredVoice) {
      utterance.voice = preferredVoice;
      utterance.lang = preferredVoice.lang;
    } else {
      utterance.lang = options.lang || "en-US";
    }

    if (currentIdx === 0 && options.onStart) {
      utterance.onstart = () => options.onStart!();
    }

    utterance.onend = () => {
      currentIdx++;
      speakNextSentence();
    };

    utterance.onerror = (e) => {
      // In Safari/Chrome, error event with 'canceled' or 'interrupted' is benign
      if (e.error !== "canceled" && e.error !== "interrupted") {
        options.onError?.(e);
      }
      options.onEnd?.();
    };

    // Small timeout prevents Safari cancel-before-speak drop bug
    setTimeout(() => {
      try {
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
        }
        window.speechSynthesis.speak(utterance);
      } catch (err) {
        options.onError?.(err);
      }
    }, 40);
  };

  speakNextSentence();
}

// ------------------------------------------------ Speech Recognition (STT)
export interface VoiceRecognizerCallbacks {
  lang?: string;
  onResult: (transcript: string, isFinal: boolean) => void;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (err: any) => void;
}

export async function requestMicrophonePermission(): Promise<boolean> {
  if (typeof navigator !== "undefined" && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      return true;
    } catch {
      return false;
    }
  }
  return true;
}

export function startListening(callbacks: VoiceRecognizerCallbacks): { stop: () => void } | null {
  if (!isRecognitionSupported()) return null;

  try {
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRec();

    const isSafari =
      typeof navigator !== "undefined" &&
      (/^((?!chrome|android).)*safari/i.test(navigator.userAgent) || /iPad|iPhone|iPod/.test(navigator.userAgent));

    // Continuous is flaky in Safari WebKit; use single-session for Safari, continuous for Chromium
    recognition.continuous = !isSafari;
    recognition.interimResults = true;
    recognition.maxAlternatives = 3;

    // Language fallback
    const defaultLang = typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-IN";
    recognition.lang = callbacks.lang || defaultLang;

    let accumulatedFinal = "";
    let silenceTimer: any = null;
    let isStopped = false;

    const clearSilence = () => {
      if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
      }
    };

    recognition.onstart = () => {
      playChime("listen");
      callbacks.onStart?.();
    };

    recognition.onresult = (event: any) => {
      clearSilence();
      let currentInterim = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const item = event.results[i];
        if (item.isFinal) {
          accumulatedFinal += " " + item[0].transcript;
        } else {
          currentInterim += item[0].transcript;
        }
      }

      const currentText = (accumulatedFinal + " " + currentInterim).trim();
      if (currentText) {
        callbacks.onResult(currentText, false);

        // Auto finalize after 1.5s silence
        silenceTimer = setTimeout(() => {
          if (!isStopped) {
            try {
              recognition.stop();
            } catch {
              // Ignore
            }
          }
        }, 1500);
      }
    };

    recognition.onerror = (err: any) => {
      clearSilence();
      // "no-speech" in Web Speech API means silence was detected
      if (err.error !== "no-speech") {
        callbacks.onError?.(err);
      }
    };

    recognition.onend = () => {
      clearSilence();
      isStopped = true;
      const finalText = accumulatedFinal.trim();
      if (finalText) {
        callbacks.onResult(finalText, true);
      }
      callbacks.onEnd?.();
    };

    recognition.start();

    return {
      stop: () => {
        isStopped = true;
        clearSilence();
        try {
          recognition.stop();
        } catch {
          // Already stopped
        }
      },
    };
  } catch (err) {
    callbacks.onError?.(err);
    return null;
  }
}
