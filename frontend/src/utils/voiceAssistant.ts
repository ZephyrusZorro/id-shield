/**
 * Web Speech API & Web Audio utility for accessible voice guidance and recognition.
 * Optimized for elderly accessibility: clear cadence, natural timbre, audio chimes.
 */

export interface SpeechOptions {
  rate?: number; // Default 0.88 for elderly comprehension
  pitch?: number;
  lang?: string;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (err: any) => void;
}

// ------------------------------------------------ Audio Cues (Synthesized)
export function playChime(type: "listen" | "success" | "stop" | "error") {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
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
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.start(now);
      osc.stop(now + 0.35);
    } else if (type === "success") {
      // Affirmative soft chord (C5 -> E5 -> G5)
      osc.type = "sine";
      osc.frequency.setValueAtTime(523.25, now);
      osc.frequency.exponentialRampToValueAtTime(783.99, now + 0.2);
      gain.gain.setValueAtTime(0.09, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
      osc.start(now);
      osc.stop(now + 0.45);
    } else if (type === "stop") {
      // Soft descending tone
      osc.type = "sine";
      osc.frequency.setValueAtTime(440.0, now);
      osc.frequency.exponentialRampToValueAtTime(330.0, now + 0.15);
      gain.gain.setValueAtTime(0.07, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
      osc.start(now);
      osc.stop(now + 0.3);
    } else {
      // Low friendly warning bump
      osc.type = "triangle";
      osc.frequency.setValueAtTime(260.0, now);
      gain.gain.setValueAtTime(0.08, now);
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
  return (
    typeof window !== "undefined" &&
    Boolean((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)
  );
}

export function stopSpeaking(): void {
  if (isSpeechSupported()) {
    window.speechSynthesis.cancel();
  }
}

export function speakText(text: string, options: SpeechOptions = {}): void {
  if (!isSpeechSupported()) return;

  // Cancel any ongoing utterance
  window.speechSynthesis.cancel();

  // Clean text: strip markdown symbols, asterisks, brackets
  const clean = text
    .replace(/[#*_`~[\]()]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (!clean) return;

  const utterance = new SpeechSynthesisUtterance(clean);
  // Default to 0.88 rate for calm, unhurried, elderly-friendly enunciation
  utterance.rate = options.rate ?? 0.88;
  utterance.pitch = options.pitch ?? 1.0;

  const targetLang = options.lang || "en";
  const voices = window.speechSynthesis.getVoices();
  const preferredVoice =
    voices.find((v) => v.lang.startsWith(targetLang) && (v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("Online"))) ||
    voices.find((v) => v.lang.startsWith(targetLang));

  if (preferredVoice) {
    utterance.voice = preferredVoice;
  }

  if (options.onStart) utterance.onstart = () => options.onStart!();
  if (options.onEnd) utterance.onend = () => options.onEnd!();
  if (options.onError) utterance.onerror = (e) => options.onError!(e);

  window.speechSynthesis.speak(utterance);
}

// ------------------------------------------------ Speech Recognition (STT)
export interface VoiceRecognizerCallbacks {
  lang?: string;
  onResult: (transcript: string, isFinal: boolean) => void;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (err: any) => void;
}

export function startListening(callbacks: VoiceRecognizerCallbacks): { stop: () => void } | null {
  if (!isRecognitionSupported()) return null;

  const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  const recognition = new SpeechRec();

  // Continuous listening with interim results for real-time responsiveness
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 3;

  // Language: fallback from user selection -> device locale -> en-IN -> en-US
  const defaultLang = typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-IN";
  recognition.lang = callbacks.lang || defaultLang;

  let accumulatedFinal = "";
  let silenceTimer: any = null;

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

      // Trigger automatic final submission after 1.4s of silence after speaking
      silenceTimer = setTimeout(() => {
        try {
          recognition.stop();
        } catch {
          // ignore
        }
      }, 1400);
    }
  };

  recognition.onerror = (err: any) => {
    clearSilence();
    callbacks.onError?.(err);
  };

  recognition.onend = () => {
    clearSilence();
    const finalText = accumulatedFinal.trim();
    if (finalText) {
      callbacks.onResult(finalText, true);
    }
    callbacks.onEnd?.();
  };

  try {
    recognition.start();
  } catch (err) {
    callbacks.onError?.(err);
    return null;
  }

  return {
    stop: () => {
      clearSilence();
      try {
        recognition.stop();
      } catch {
        // Already stopped
      }
    },
  };
}

