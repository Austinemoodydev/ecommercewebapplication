(function () {
    "use strict";

    const root = document.querySelector(".ai-chat");
    if (!root) return;

    const launcher = root.querySelector(".ai-chat__launcher");
    const panel = root.querySelector(".ai-chat__panel");
    const closeButton = root.querySelector(".ai-chat__close");
    const form = root.querySelector(".ai-chat__form");
    const input = root.querySelector("textarea");
    const submit = form.querySelector("button[type='submit']");
    const messages = root.querySelector(".ai-chat__messages");
    const count = root.querySelector(".ai-chat__count");
    const micButton = root.querySelector(".ai-chat__mic");
    const speakButton = root.querySelector(".ai-chat__speak");
    const voiceStatus = root.querySelector(".ai-chat__voice-status");
    const csrf = form.querySelector("[name='csrfmiddlewaretoken']").value;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const canRecord = Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
    const canSpeak = "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
    let inFlight = false;
    let mediaRecorder = null;
    let mediaStream = null;
    let audioChunks = [];
    let stopTimer = null;
    let recognition = null;
    let listening = false;
    let readReplies = false;

    function setVoiceStatus(message) { voiceStatus.textContent = message; }
    function setListening(active) {
        listening = active;
        micButton.classList.toggle("is-listening", active);
        micButton.setAttribute("aria-pressed", String(active));
        micButton.setAttribute("aria-label", active ? "Stop recording" : "Speak your question");
        micButton.querySelector("i").className = active ? "bi bi-stop-fill" : "bi bi-mic-fill";
    }
    function updateInput(text) {
        input.value = text.trim().slice(0, 600);
        count.textContent = input.value.length;
        input.focus();
    }
    function stopMediaStream() {
        window.clearTimeout(stopTimer);
        if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
    }

    async function uploadRecording(blob) {
        if (!blob.size) {
            setVoiceStatus("No audio was captured. Please try again.");
            return;
        }
        micButton.disabled = true;
        setVoiceStatus("Converting your voice to text…");
        const body = new FormData();
        body.append("audio", blob, "voice-message." + (blob.type.includes("mp4") ? "mp4" : "webm"));
        try {
            const response = await fetch(root.dataset.voiceEndpoint, {
                method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": csrf}, body
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Voice transcription failed.");
            updateInput(data.transcript || "");
            setVoiceStatus("Voice captured. Review the message, then press Send.");
        } catch (error) {
            setVoiceStatus(error.message || "Voice transcription failed. Type your question instead.");
        } finally {
            micButton.disabled = false;
        }
    }

    async function startRecording() {
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({audio: true});
            const preferredType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]
                .find((type) => MediaRecorder.isTypeSupported(type));
            mediaRecorder = preferredType
                ? new MediaRecorder(mediaStream, {mimeType: preferredType})
                : new MediaRecorder(mediaStream);
            audioChunks = [];
            mediaRecorder.addEventListener("dataavailable", (event) => {
                if (event.data.size) audioChunks.push(event.data);
            });
            mediaRecorder.addEventListener("stop", () => {
                const blob = new Blob(audioChunks, {type: mediaRecorder.mimeType || "audio/webm"});
                setListening(false);
                stopMediaStream();
                uploadRecording(blob);
            }, {once: true});
            mediaRecorder.start();
            setListening(true);
            setVoiceStatus("Recording… Speak now, then tap the red stop button.");
            stopTimer = window.setTimeout(() => {
                if (mediaRecorder?.state === "recording") mediaRecorder.stop();
            }, 20000);
        } catch (error) {
            setListening(false);
            stopMediaStream();
            setVoiceStatus(error.name === "NotAllowedError"
                ? "Microphone permission was denied. Allow it in your browser settings and try again."
                : "The microphone could not start. Check that another app is not using it.");
        }
    }

    if (!canRecord && SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.lang = "en-KE";
        recognition.interimResults = true;
        recognition.continuous = false;
        recognition.addEventListener("start", () => { setListening(true); setVoiceStatus("Listening… Speak now."); });
        recognition.addEventListener("result", (event) => {
            let transcript = "";
            for (let index = 0; index < event.results.length; index += 1) transcript += event.results[index][0].transcript;
            updateInput(transcript);
        });
        recognition.addEventListener("end", () => {
            setListening(false);
            setVoiceStatus(input.value ? "Voice captured. Review it, then press Send." : "Listening stopped.");
        });
        recognition.addEventListener("error", (event) => {
            setListening(false);
            const errors = {"not-allowed": "Allow microphone access in your browser settings.", "no-speech": "No speech was detected. Try again.", "audio-capture": "No microphone was found.", "network": "Voice recognition could not connect."};
            setVoiceStatus(errors[event.error] || "Voice input is unavailable. Type your question instead.");
        });
    } else if (!canRecord) {
        micButton.hidden = true;
        setVoiceStatus("Voice input is not supported by this browser.");
    }

    if (!canSpeak) speakButton.hidden = true;
    function speak(text) {
        if (!readReplies || !canSpeak || !text) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "en-KE";
        utterance.rate = 1;
        const voices = window.speechSynthesis.getVoices();
        utterance.voice = voices.find((voice) => voice.lang.toLowerCase() === "en-ke")
            || voices.find((voice) => voice.lang.toLowerCase().startsWith("en")) || null;
        window.speechSynthesis.speak(utterance);
    }

    speakButton.addEventListener("click", () => {
        readReplies = !readReplies;
        speakButton.classList.toggle("is-active", readReplies);
        speakButton.setAttribute("aria-pressed", String(readReplies));
        speakButton.setAttribute("aria-label", readReplies ? "Stop reading assistant replies aloud" : "Read assistant replies aloud");
        speakButton.querySelector("i").className = readReplies ? "bi bi-volume-up-fill" : "bi bi-volume-mute-fill";
        if (!readReplies) window.speechSynthesis.cancel();
        setVoiceStatus(readReplies ? "Spoken replies are on." : "Spoken replies are off.");
    });

    function setOpen(open) { panel.hidden = !open; launcher.setAttribute("aria-expanded", String(open)); if (open) input.focus(); }
    function addMessage(text, role) {
        const item = document.createElement("div");
        item.className = "ai-chat__message ai-chat__message--" + role;
        item.textContent = text;
        messages.appendChild(item);
        messages.scrollTop = messages.scrollHeight;
        return item;
    }

    launcher.addEventListener("click", () => setOpen(panel.hidden));
    closeButton.addEventListener("click", () => {
        setOpen(false);
        if (mediaRecorder?.state === "recording") mediaRecorder.stop();
        if (recognition && listening) recognition.stop();
        if (canSpeak) window.speechSynthesis.cancel();
    });
    micButton.addEventListener("click", async () => {
        if (inFlight) return;
        if (canRecord) {
            if (mediaRecorder?.state === "recording") mediaRecorder.stop(); else await startRecording();
        } else if (recognition) {
            if (listening) recognition.stop(); else try { recognition.start(); } catch (error) { setVoiceStatus("Voice input is already starting."); }
        }
    });
    input.addEventListener("input", () => { count.textContent = input.value.length; });
    input.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const message = input.value.trim();
        if (!message || inFlight) return;
        inFlight = true;
        if (mediaRecorder?.state === "recording") mediaRecorder.stop();
        if (recognition && listening) recognition.stop();
        submit.disabled = true; micButton.disabled = true; input.disabled = true;
        addMessage(message, "user"); updateInput("");
        const pending = addMessage("Thinking…", "assistant");
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 20000);
        try {
            const response = await fetch(root.dataset.chatEndpoint, {
                method: "POST", credentials: "same-origin",
                headers: {"Content-Type": "application/json", "X-CSRFToken": csrf},
                body: JSON.stringify({message}), signal: controller.signal
            });
            const data = await response.json();
            pending.textContent = response.ok ? data.reply : (data.error || "The assistant is unavailable.");
            if (response.ok) speak(data.reply);
        } catch (error) {
            pending.textContent = error.name === "AbortError" ? "The request took too long. Please try again." : "Unable to reach the assistant. Check your connection and try again.";
        } finally {
            window.clearTimeout(timeout); inFlight = false; submit.disabled = false;
            micButton.disabled = false; input.disabled = false; input.focus();
        }
    });
})();
