import { useCallback, useEffect, useRef } from "react";

import { beginPlayback, endPlayback, isCurrentPlayback } from "../../shared/playback/playbackChannel";

export default function QuickResult({ audio, audioRef }) {
  const keyRef = useRef(0);

  const claim = useCallback(() => {
    const element = audioRef?.current;
    if (!element) return 0;
    const key = beginPlayback(() => element.pause());
    keyRef.current = key;
    return key;
  }, [audioRef]);

  // Claim before starting: `autoPlay` would begin before the effect ran and
  // could overlap whatever was already playing.
  useEffect(() => {
    const element = audioRef?.current;
    if (!audio || !element) return undefined;

    claim();
    const started = element.play();
    started?.catch?.(() => {
      /* autoplay blocked: controls remain available */
    });

    return () => {
      element.pause();
      endPlayback(keyRef.current);
      keyRef.current = 0;
    };
  }, [audio, audioRef, claim]);

  const handlePlay = () => {
    // Manual play after another source took the channel: claim it back and
    // stop the other source instead of layering two audios.
    if (isCurrentPlayback(keyRef.current)) return;
    claim();
  };

  if (!audio) return null;

  return (
    <div className="rounded-xl border border-line bg-white/[0.03] p-3">
      <audio
        ref={audioRef}
        controls
        src={audio.url}
        className="w-full"
        onPlay={handlePlay}
      />
      <div className="mt-2 flex items-center justify-between text-[12px] text-faint">
        <span>
          {audio.seconds != null
            ? `${audio.seconds.toFixed(1)} giây`
            : "WAV 48 kHz"}
        </span>
        <a
          href={audio.url}
          download="vieneu-tts.wav"
          className="inline-flex min-h-11 items-center rounded-md px-2 py-1 text-accent transition hover:bg-accent/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
        >
          Tải WAV
        </a>
      </div>
    </div>
  );
}
