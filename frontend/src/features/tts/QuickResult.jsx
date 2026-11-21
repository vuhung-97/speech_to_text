export default function QuickResult({ audio, audioRef }) {
  const keyRef = useRef(0);

  // Register the finished WAV with the playback channel: any other source
  // (or a new press) pauses it before playing.
  useEffect(() => {
    const element = audioRef?.current;
    if (!audio || !element) return undefined;
    const key = beginPlayback(() => {
      element.pause();
    });
    keyRef.current = key;
    return () => {
      endPlayback(key);
      keyRef.current = 0;
    };
  }, [audio, audioRef]);

  if (!audio) return null;

  return (
    <div className="rounded-xl border border-line bg-white/[0.03] p-3">
      <audio ref={audioRef} controls autoPlay src={audio.url} className="w-full" />
      <div className="mt-2 flex items-center justify-between text-[11.5px] text-faint">
        <span>
          {audio.seconds != null
            ? `${audio.seconds.toFixed(1)} giây`
            : "WAV 48 kHz"}
        </span>
        <a
          href={audio.url}
          download="vieneu-tts.wav"
          className="rounded-md px-2 py-1 text-accent transition hover:bg-accent/10"
        >
          Tải WAV
        </a>
      </div>
    </div>
  );
}
