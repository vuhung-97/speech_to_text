export default function VoicePicker({ voices, voice, onChange }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[13px] text-white">Giọng đọc</span>
      <select
        value={voice}
        onChange={(event) => onChange(event.target.value)}
        disabled={!voices.length}
        className="w-full rounded-lg border border-line bg-white/[0.04] px-2.5 py-2 text-[13px] text-white outline-none focus:border-accent/60 disabled:opacity-50"
      >
        {!voices.length && <option value="">Chưa có giọng</option>}
        {voices.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  );
}
