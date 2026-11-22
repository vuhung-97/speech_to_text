// Voice selection + a sample reader shown in the settings drawer. Choosing a
// voice persists it and warms that voice in the server RAM in the background.

import { useEffect, useState } from "react";

import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";
import { useSpeechPlayer } from "../../shared/playback/useSpeechPlayer";
import { useVoice } from "../../shared/tts/VoiceProvider";
import VoicePicker from "./VoicePicker";

const SAMPLE_TEXT = "Xin chào, đây là giọng đọc thử nghiệm.";

export default function VoiceSettings({ active = true }) {
  const voice = useVoice();
  const speech = useSpeechPlayer();
  const [sample, setSample] = useState(SAMPLE_TEXT);
  const stopSpeech = speech.stop;

  useEffect(() => {
    if (!active) stopSpeech();
  }, [active, stopSpeech]);

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

  const toggleTest = () => {
    if (testing) {
      speech.stop();
      return;
    }
    const text = sample.trim();
    if (text) speech.start(text, voice.voice);
  };

  return (
    <section>
      <h3 className="mb-2 text-[12px] font-semibold tracking-[0.09em] text-faint uppercase">
        Giọng đọc
      </h3>

      {!voice.available ? (
        <div className="space-y-2">
          <Alert>{voice.reason || "TTS chưa sẵn sàng."}</Alert>
          <Button variant="secondary" size="sm" onClick={voice.load}>
            Thử lại
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          <VoicePicker
            label="Chọn giọng"
            voices={voice.voices}
            voice={voice.voice}
            onChange={chooseVoice}
            loading={loading}
          />

          {voice.preloading && (
            <p
              aria-live="polite"
              className="m-0 flex items-center gap-2 text-[12px] text-accent"
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

          <label className="block">
            <span className="mb-1 block text-[12px] text-faint">Nội dung thử</span>
            <textarea
              value={sample}
              onChange={(event) => setSample(event.target.value)}
              rows={2}
              className={`${FIELD_CLASS} w-full resize-none rounded-lg px-3 py-2 ${FIELD_TEXT}`}
            />
          </label>

          <Button
            variant={testing ? "danger" : "secondary"}
            className="w-full"
            onClick={toggleTest}
            disabled={!testing && (!sample.trim() || !voice.voice)}
          >
            {testing ? "Dừng" : "Test giọng"}
          </Button>

          {speech.error && <Alert size="sm">{speech.error}</Alert>}

          {needsDownload && (
            <Alert tone="note" size="sm">
              Thiếu model local — lần đọc đầu cần mạng.
            </Alert>
          )}
        </div>
      )}
    </section>
  );
}
