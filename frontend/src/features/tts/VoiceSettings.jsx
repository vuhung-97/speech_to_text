// Voice selection, reading speed and a sample reader shown in the Q&A tools
// panel. Choosing a voice persists it and warms that voice in server RAM in the
// background; the speed slider is read once when a read starts.

import { useState } from "react";

import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import { FIELD_CLASS } from "../../components/ui/fieldStyles";
import { useSpeechPlayer } from "../../shared/playback/useSpeechPlayer";
import {
  MAX_LOOKAHEAD,
  MAX_PREBUFFER,
  MAX_SPEED,
  MIN_LOOKAHEAD,
  MIN_PREBUFFER,
  MIN_SPEED,
  LOOKAHEAD_STEP,
  PREBUFFER_STEP,
  SPEED_STEP,
  readLookahead,
  readPrebuffer,
  saveLookahead,
  savePrebuffer,
} from "../../shared/tts/constants";
import { useVoice } from "../../shared/tts/VoiceProvider";
import VoicePicker from "./VoicePicker";

const SAMPLE_TEXT = "Xin chào, đây là giọng đọc thử nghiệm.";

function Chevron() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-3 w-3 transition-transform group-open:rotate-180"
      aria-hidden="true"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function PrefSlider({ label, value, min, max, step, unit, onChange }) {
  return (
    <div className="pt-1">
      <div className="mb-0.5 flex items-center justify-between text-[10.5px] text-faint">
        <span>{label}</span>
        <span className="font-mono text-dim">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-label={label}
        className="h-11 w-full accent-accent sm:h-6"
      />
    </div>
  );
}

export default function VoiceSettings({ embedded = false }) {
  const voice = useVoice();
  const speech = useSpeechPlayer();
  const [sample, setSample] = useState(SAMPLE_TEXT);
  const [prebuffer, setPrebuffer] = useState(readPrebuffer);
  const [lookahead, setLookahead] = useState(readLookahead);

  const loading = voice.loading && !voice.loaded;
  const testing = speech.busy;
  const needsDownload =
    Object.keys(voice.status || {}).length > 0 &&
    voice.available &&
    (voice.status.local_model === false || voice.status.offline === false);

  const chooseVoice = (value) => {
    speech.stop();
    voice.chooseVoice(value);
  };

  const changePrebuffer = (value) => setPrebuffer(savePrebuffer(value));
  const changeLookahead = (value) => setLookahead(saveLookahead(value));

  const toggleTest = () => {
    if (testing) {
      speech.stop();
      return;
    }
    const text = sample.trim();
    if (text) speech.start(text, voice.voice, voice.speed);
  };

  const body = !voice.available ? (
    <div className="space-y-2">
      <Alert>{voice.reason || "TTS chưa sẵn sàng."}</Alert>
      <Button variant="secondary" size="sm" onClick={voice.load}>
        Thử lại
      </Button>
    </div>
  ) : (
    <div className="space-y-2">
      <VoicePicker
        label="Giọng đọc"
        voices={voice.voices}
        voice={voice.voice}
        onChange={chooseVoice}
        loading={loading}
      />

      <div className="pt-1">
        <div className="mb-0.5 flex items-center justify-between text-[10.5px] text-faint">
          <span>Tốc độ đọc</span>
          <span className="font-mono text-dim">{voice.speed.toFixed(1)}×</span>
        </div>
        <input
          type="range"
          min={MIN_SPEED}
          max={MAX_SPEED}
          step={SPEED_STEP}
          value={voice.speed}
          onChange={(event) => voice.chooseSpeed(Number(event.target.value))}
          aria-label="Tốc độ đọc"
          aria-valuetext={`${voice.speed.toFixed(1)} lần`}
          className="h-11 w-full accent-accent sm:h-6"
        />
      </div>

      <details className="group border-t border-line pt-2">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 py-1 text-[10.5px] text-dim focus-ring sm:min-h-8">
          Chất lượng phát
          <Chevron />
        </summary>
        <div className="mt-2 space-y-1">
          <PrefSlider
            label="Đệm trước khi đọc"
            value={prebuffer}
            min={MIN_PREBUFFER}
            max={MAX_PREBUFFER}
            step={PREBUFFER_STEP}
            unit="s"
            onChange={changePrebuffer}
          />
          <PrefSlider
            label="Xem trước khi phát"
            value={lookahead}
            min={MIN_LOOKAHEAD}
            max={MAX_LOOKAHEAD}
            step={LOOKAHEAD_STEP}
            unit="s"
            onChange={changeLookahead}
          />
          <p className="m-0 text-[10px] leading-relaxed text-faint">
            Tăng nếu giọng bị vấp trên máy chậm; áp dụng ở lần đọc kế tiếp.
          </p>
        </div>
      </details>

      {voice.preloading && (
        <p
          aria-live="polite"
          className="m-0 flex items-center gap-2 text-[10.5px] text-accent"
        >
          <span
            className="h-3 w-3 animate-spin rounded-full border-2 border-accent/30 border-t-accent motion-reduce:animate-none"
            aria-hidden="true"
          />
          Đang nạp giọng vào RAM…
        </p>
      )}

      {voice.preloadError && (
        <div className="space-y-2">
          <Alert size="sm">{voice.preloadError}</Alert>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => voice.preload(voice.voice)}
          >
            Thử lại
          </Button>
        </div>
      )}

      <details className="group border-t border-line pt-2">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 py-1 text-[10.5px] text-dim focus-ring sm:min-h-8">
          Thử giọng
          <Chevron />
        </summary>
        <div className="mt-2 space-y-2">
          <label className="block">
            <span className="sr-only">Nội dung thử</span>
            <textarea
              value={sample}
              onChange={(event) => setSample(event.target.value)}
              rows={2}
              aria-label="Nội dung thử"
              className={`${FIELD_CLASS} w-full resize-none rounded-lg px-2.5 py-2 text-[11px]`}
            />
          </label>
          <Button
            variant={testing ? "danger" : "secondary"}
            size="sm"
            className="w-full"
            onClick={toggleTest}
            disabled={!testing && (!sample.trim() || !voice.voice)}
          >
            {testing ? "Dừng" : "Test giọng"}
          </Button>
        </div>
      </details>

      {speech.error && <Alert size="sm">{speech.error}</Alert>}

      {needsDownload && (
        <Alert tone="note" size="sm">
          Thiếu model local — lần đọc đầu cần mạng.
        </Alert>
      )}
    </div>
  );

  if (embedded) return body;

  return (
    <section className="rounded-xl border border-line bg-wash p-3">
      <h2 className="m-0 mb-2 text-[12px] font-semibold tracking-[0.08em] text-faint uppercase">
        Giọng đọc
      </h2>
      {body}
    </section>
  );
}
