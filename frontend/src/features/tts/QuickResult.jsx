export default function QuickResult({ audio }) {
  if (!audio) return null;

  return (
    <div className="rounded-xl border border-line bg-white/[0.03] p-3">
      <audio controls autoPlay src={audio.url} className="w-full" />
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
