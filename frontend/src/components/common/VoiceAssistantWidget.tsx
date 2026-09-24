import { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Sparkles,
  X,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Send,
  Globe,
  Loader2,
} from "lucide-react";
import {
  speakText,
  stopSpeaking,
  startListening,
  isSpeechSupported,
  playChime,
  requestMicrophonePermission,
} from "../../utils/voiceAssistant";
import type { VoiceBriefResponse, VoiceQueryResponse } from "../../types/api";

export function VoiceAssistantWidget() {
  const location = useLocation();
  const navigate = useNavigate();

  const [isOpen, setIsOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [speedMode, setSpeedMode] = useState<"elderly" | "normal">("elderly");
  const [selectedLang, setSelectedLang] = useState<string>("en-IN");
  const [transcript, setTranscript] = useState("");
  const [typedInput, setTypedInput] = useState("");
  const [spokenSubtitle, setSpokenSubtitle] = useState("");
  const [voiceBrief, setVoiceBrief] = useState<VoiceBriefResponse | null>(null);
  const [loadingBrief, setLoadingBrief] = useState(false);
  const [lastAction, setLastAction] = useState<string | null>(null);

  const activeListenerRef = useRef<{ stop: () => void } | null>(null);

  // Extract caseId if on /cases/:caseId
  const caseMatch = location.pathname.match(/\/cases\/([^/]+)/);
  const currentCaseId = caseMatch ? caseMatch[1] : null;

  const currentRate = speedMode === "elderly" ? 0.86 : 1.0;

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      if (activeListenerRef.current) {
        activeListenerRef.current.stop();
      }
    };
  }, []);

  // Fetch voice brief when case changes or widget opens on a case
  useEffect(() => {
    if (!currentCaseId) {
      setVoiceBrief(null);
      return;
    }
    const fetchBrief = async () => {
      try {
        setLoadingBrief(true);
        const res = await fetch(`/api/cases/${currentCaseId}/voice-brief`);
        if (res.ok) {
          const data: VoiceBriefResponse = await res.json();
          setVoiceBrief(data);
        }
      } catch {
        // Fallback silently if offline or test
      } finally {
        setLoadingBrief(false);
      }
    };
    fetchBrief();
  }, [currentCaseId]);

  // Listen for trigger from page buttons (e.g. CaseDetailPage "Voice Summary" button)
  useEffect(() => {
    const handleVoiceSpeakBrief = () => {
      setIsOpen(true);
      if (voiceBrief) {
        speakWithCaptions(voiceBrief.spoken_text);
      } else if (currentCaseId) {
        fetch(`/api/cases/${currentCaseId}/voice-brief`)
          .then((res) => res.json())
          .then((data: VoiceBriefResponse) => {
            setVoiceBrief(data);
            speakWithCaptions(data.spoken_text);
          })
          .catch(() => {
            speakWithCaptions("Sorry, could not load the case summary right now.");
          });
      }
    };
    window.addEventListener("idshield:voice-speak-brief", handleVoiceSpeakBrief);
    return () => window.removeEventListener("idshield:voice-speak-brief", handleVoiceSpeakBrief);
  }, [voiceBrief, currentCaseId, currentRate, selectedLang]);

  // Execute oral speech with captions
  const speakWithCaptions = (text: string, onDone?: () => void) => {
    if (!isSpeechSupported()) {
      setSpokenSubtitle(text);
      return;
    }
    setIsSpeaking(true);
    setSpokenSubtitle(text);

    speakText(text, {
      rate: currentRate,
      lang: selectedLang,
      onStart: () => setIsSpeaking(true),
      onEnd: () => {
        setIsSpeaking(false);
        onDone?.();
      },
      onError: () => {
        setIsSpeaking(false);
      },
    });
  };

  // Halt speech
  const handleStopSpeech = () => {
    stopSpeaking();
    setIsSpeaking(false);
    playChime("stop");
    setSpokenSubtitle("");
  };

  // Intelligent Natural Language Query Processor (Handles both Spoken and Typed inputs)
  const processQuery = async (queryText: string) => {
    const raw = queryText.toLowerCase().trim();
    if (!raw) return;

    setTranscript(queryText);

    // Instant stop check
    if (raw.includes("stop") || raw.includes("quiet") || raw.includes("silence") || raw.includes("shut up")) {
      handleStopSpeech();
      setLastAction("Stopped speech");
      return;
    }

    // Call intelligent backend query API
    try {
      setIsThinking(true);
      const endpoint = currentCaseId
        ? `/api/cases/${currentCaseId}/voice-query`
        : `/api/voice-query`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: queryText,
          current_path: location.pathname,
        }),
      });

      if (!response.ok) {
        throw new Error("Query failed");
      }

      const data: VoiceQueryResponse = await response.json();
      setIsThinking(false);

      // Execute any UI action requested
      if (data.action) {
        if (data.action.startsWith("switch_tab:")) {
          const tabName = data.action.replace("switch_tab:", "");
          window.dispatchEvent(new CustomEvent("idshield:switch-tab", { detail: tabName }));
          setLastAction(`Switched to ${tabName} tab`);
        } else if (data.action.startsWith("navigate:")) {
          const path = data.action.replace("navigate:", "");
          navigate(path);
          setLastAction(`Navigated to ${path}`);
        }
      } else {
        setLastAction(`Answered question: "${queryText}"`);
      }

      // Play success chime & speak answer aloud
      playChime("success");
      speakWithCaptions(data.answer);
    } catch {
      setIsThinking(false);
      playChime("error");
      const fallback = `I could not process "${queryText}". You can ask: "Is this document fake?", "What is the risk score?", or "Who is the applicant?".`;
      speakWithCaptions(fallback);
      setLastAction("Could not process query");
    }
  };

  // Toggle voice recognition
  const toggleListening = async () => {
    if (isListening) {
      activeListenerRef.current?.stop();
      setIsListening(false);
      return;
    }

    // Stop speaking if talking
    if (isSpeaking) {
      stopSpeaking();
      setIsSpeaking(false);
    }

    const hasMic = await requestMicrophonePermission();
    if (!hasMic) {
      playChime("error");
      setTranscript("Microphone permission was denied. You can type your question in the box below!");
      return;
    }

    const listener = startListening({
      lang: selectedLang,
      onStart: () => {
        setIsListening(true);
        setTranscript("Listening for your voice... speak now.");
      },
      onResult: (resultText, isFinal) => {
        setTranscript(resultText);
        if (isFinal && resultText.trim().length > 0) {
          setIsListening(false);
          processQuery(resultText);
        }
      },
      onEnd: () => {
        setIsListening(false);
      },
      onError: () => {
        setIsListening(false);
        playChime("error");
        setTranscript("Microphone audio not detected. Try typing your question below.");
      },
    });

    if (listener) {
      activeListenerRef.current = listener;
    } else {
      setTranscript("Voice recognition is not supported in this browser. Please type your question below.");
    }
  };

  // Explaining current page when not on a case
  const speakCurrentPageOverview = () => {
    if (currentCaseId && voiceBrief) {
      speakWithCaptions(voiceBrief.spoken_text);
      return;
    }
    processQuery("What is this page?");
  };

  // Handle Typed Form Submission
  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!typedInput.trim()) return;
    const q = typedInput.trim();
    setTypedInput("");
    processQuery(q);
  };

  return (
    <aside
      aria-label="Voice accessibility assistant"
      className="fixed bottom-6 right-6 z-40 flex flex-col items-end pointer-events-none"
    >
      {/* Expanded Voice Dialog Box */}
      {isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Voice Guidance Panel"
          className="pointer-events-auto mb-3 w-[92vw] max-w-md rounded-2xl border-2 border-blue-500/80 bg-white/95 dark:bg-[#0E1526]/95 backdrop-blur-xl shadow-2xl shadow-blue-500/20 p-5 text-slate-900 dark:text-slate-100 transition-all duration-300 animate-in fade-in slide-in-from-bottom-5"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-200/80 dark:border-slate-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white shadow-glow-blue">
                <Sparkles size={18} />
              </div>
              <div>
                <h2 className="text-sm font-extrabold text-navy-900 dark:text-white flex items-center gap-1.5">
                  Voice Assistant
                  <span className="rounded-full bg-blue-100 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300 px-2 py-0.5 text-[10px] font-bold">
                    Smart AI
                  </span>
                </h2>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                  Accessible spoken guidance & conversational Q&A
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                aria-label="Close voice assistant dialog"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Controls: Speech Cadence & Voice Accent Selector */}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-100/80 dark:bg-slate-900/60 p-2 text-xs">
            {/* Speed Toggle */}
            <div className="flex items-center gap-1.5">
              <Clock size={13} className="text-blue-500" />
              <div className="inline-flex rounded-lg bg-white dark:bg-slate-800 p-0.5 shadow-sm border border-slate-200/60 dark:border-slate-700/60">
                <button
                  type="button"
                  onClick={() => setSpeedMode("elderly")}
                  className={`rounded-md px-2 py-0.5 text-[11px] font-bold transition-all ${
                    speedMode === "elderly"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                  title="Calm 0.86x cadence for elderly comprehension"
                >
                  Relaxed (0.86x)
                </button>
                <button
                  type="button"
                  onClick={() => setSpeedMode("normal")}
                  className={`rounded-md px-2 py-0.5 text-[11px] font-bold transition-all ${
                    speedMode === "normal"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                  title="Standard 1.0x rate"
                >
                  Standard
                </button>
              </div>
            </div>

            {/* Accent Selector */}
            <div className="flex items-center gap-1 text-[11px]">
              <Globe size={12} className="text-slate-400" />
              <select
                value={selectedLang}
                onChange={(e) => setSelectedLang(e.target.value)}
                className="rounded-md border border-slate-200/80 dark:border-slate-700 bg-white dark:bg-slate-800 px-1.5 py-0.5 text-[11px] font-medium text-slate-700 dark:text-slate-300 focus:outline-none"
                aria-label="Select voice accent"
              >
                <option value="en-IN">English (India)</option>
                <option value="en-US">English (US)</option>
                <option value="en-GB">English (UK)</option>
              </select>
            </div>
          </div>

          {/* Spoken Subtitle Display (High Contrast, Large Font for Accessibility) */}
          {(isSpeaking || spokenSubtitle) && (
            <div
              aria-live="polite"
              className="mt-3 rounded-xl border border-blue-200 dark:border-blue-900/60 bg-blue-50/70 dark:bg-blue-950/40 p-3.5"
            >
              <div className="flex items-center justify-between text-[11px] font-bold text-blue-700 dark:text-blue-300 mb-1">
                <span className="flex items-center gap-1.5">
                  <Volume2 size={14} className={isSpeaking ? "animate-pulse text-blue-600" : ""} />
                  {isSpeaking ? "Speaking answer aloud..." : "Last Spoken Answer"}
                </span>
                {isSpeaking && (
                  <button
                    type="button"
                    onClick={handleStopSpeech}
                    className="flex items-center gap-1 text-rose-600 dark:text-rose-400 hover:underline font-bold text-[11px]"
                  >
                    <VolumeX size={12} />
                    Stop
                  </button>
                )}
              </div>
              <p className="text-sm sm:text-base font-semibold text-navy-950 dark:text-blue-50 leading-relaxed">
                "{spokenSubtitle}"
              </p>
            </div>
          )}

          {/* Live Recognition Transcript / Thinking State */}
          {isThinking && (
            <div className="mt-3 flex items-center gap-2 rounded-xl border border-blue-200 dark:border-blue-900/60 bg-blue-50/40 dark:bg-blue-950/30 p-3 text-xs text-blue-600 dark:text-blue-400 font-medium">
              <Loader2 size={16} className="animate-spin text-blue-500" />
              <span>Analyzing case evidence and finding answer...</span>
            </div>
          )}

          {transcript && !isSpeaking && !isThinking && (
            <div
              aria-live="polite"
              className="mt-3 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/60 dark:bg-emerald-950/40 p-3"
            >
              <p className="text-[11px] font-bold text-emerald-700 dark:text-emerald-300 uppercase tracking-wider mb-0.5">
                {isListening ? "Listening..." : "Recognized Input"}
              </p>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                {transcript}
              </p>
            </div>
          )}

          {/* Status Feedback */}
          {lastAction && (
            <div className="mt-2 text-[11px] font-medium text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <Zap size={11} className="text-amber-500" />
              <span>{lastAction}</span>
            </div>
          )}

          {/* Main Action Buttons */}
          <div className="mt-3 grid grid-cols-2 gap-2.5">
            {/* Hold to Speak / Toggle Mic Button */}
            <button
              type="button"
              onClick={toggleListening}
              className={`flex items-center justify-center gap-2 rounded-xl py-3 px-4 font-bold text-sm transition-all shadow-md active:scale-95 ${
                isListening
                  ? "bg-rose-600 text-white animate-pulse shadow-rose-500/30"
                  : "bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/25"
              }`}
              aria-label={isListening ? "Stop listening" : "Start speaking voice command"}
            >
              {isListening ? (
                <>
                  <MicOff size={18} />
                  <span>Stop Mic</span>
                </>
              ) : (
                <>
                  <Mic size={18} />
                  <span>Tap to Speak</span>
                </>
              )}
            </button>

            {/* Read Page / Case Summary Aloud */}
            <button
              type="button"
              onClick={speakCurrentPageOverview}
              disabled={isSpeaking || loadingBrief || isThinking}
              className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 py-3 px-4 font-bold text-sm transition-all shadow-sm active:scale-95 disabled:opacity-50"
              aria-label="Read summary aloud"
            >
              <Volume2 size={18} className="text-blue-500" />
              <span>{currentCaseId ? "Speak Case" : "Read Page"}</span>
            </button>
          </div>

          {/* Natural Language Text Input Box (Guarantees 100% Accuracy Even If Mic Mishears) */}
          <form onSubmit={handleTextSubmit} className="mt-3 flex items-center gap-1.5">
            <input
              type="text"
              value={typedInput}
              onChange={(e) => setTypedInput(e.target.value)}
              placeholder="Ask anything (e.g. 'Is this fake?', 'What is the risk score?')"
              className="flex-1 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none"
              aria-label="Type question for voice assistant"
            />
            <button
              type="submit"
              disabled={!typedInput.trim() || isThinking}
              className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 transition-colors shrink-0"
              title="Submit question"
            >
              <Send size={13} />
            </button>
          </form>

          {/* If on Case Page, Show Brief Findings */}
          {currentCaseId && voiceBrief && (
            <div className="mt-3 rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/50 p-3 text-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  {voiceBrief.has_warnings ? (
                    <AlertTriangle size={14} className="text-amber-500" />
                  ) : (
                    <CheckCircle2 size={14} className="text-emerald-500" />
                  )}
                  Verification Summary ({voiceBrief.recommendation?.replace(/_/g, " ") ?? "Evaluating"})
                </span>
                <span className="font-mono font-bold text-slate-500 text-[11px]">
                  Risk: {voiceBrief.risk_score ?? "—"}/100
                </span>
              </div>
              <ul className="space-y-1 text-slate-600 dark:text-slate-400">
                {voiceBrief.summary_bullets.map((b, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 text-[11px] leading-relaxed">
                    <span className="text-blue-500 font-bold">•</span>
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Quick Voice / Natural Question Chips */}
          <div className="mt-3 pt-2.5 border-t border-slate-200/80 dark:border-slate-800/80">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Ask or tap any question:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {[
                "Is this document fake?",
                "What is the risk score?",
                "Who is the applicant?",
                "Do the names match?",
                "Show documents",
                "Check tampering",
                "Help me",
              ].map((cmd) => (
                <button
                  key={cmd}
                  type="button"
                  onClick={() => processQuery(cmd)}
                  className="rounded-lg border border-slate-200 dark:border-slate-700/80 bg-slate-50 dark:bg-slate-800/60 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-300 transition-colors"
                >
                  "{cmd}"
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Floating Trigger Button */}
      <button
        type="button"
        onClick={() => {
          if (!isOpen) {
            setIsOpen(true);
            playChime("listen");
          } else {
            setIsOpen(false);
            if (isSpeaking) handleStopSpeech();
          }
        }}
        aria-label="Toggle Voice Assistant"
        className={`pointer-events-auto group relative flex h-14 w-14 items-center justify-center rounded-2xl shadow-xl transition-all duration-300 hover:scale-105 active:scale-95 focus:outline-none focus:ring-4 focus:ring-blue-500/40 ${
          isListening
            ? "bg-rose-600 text-white shadow-rose-500/40 animate-pulse ring-4 ring-rose-400/50"
            : isSpeaking
              ? "bg-amber-500 text-white shadow-amber-500/40 ring-4 ring-amber-300/50"
              : "bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/35"
        }`}
        title="Open Voice Assistant (For elderly & hands-free assistance)"
      >
        {/* Soundwave animation ring */}
        {(isListening || isSpeaking) && (
          <span className="absolute -inset-1 rounded-2xl bg-inherit opacity-40 animate-ping" />
        )}

        {isListening ? (
          <Mic size={24} className="animate-bounce" />
        ) : isSpeaking ? (
          <Volume2 size={24} className="animate-pulse" />
        ) : (
          <Mic size={24} className="transition-transform group-hover:scale-110" />
        )}

        {/* Small badge if case brief available */}
        {currentCaseId && !isOpen && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold text-white shadow-sm ring-2 ring-white dark:ring-slate-900">
            ✓
          </span>
        )}
      </button>
    </aside>
  );
}
