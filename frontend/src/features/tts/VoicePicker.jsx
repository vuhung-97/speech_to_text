import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";

export default function VoicePicker({
  voices,
  voice,
  onChange,
  loading = false,
  label = "Giọng đọc",
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[13px] text-white">{label}</span>
      <select
        value={voice}
        onChange={(event) => onChange(event.target.value)}
        disabled={loading || !voices.length}
        className={`${FIELD_CLASS} w-full rounded-lg px-2.5 py-2 ${FIELD_TEXT}`}
      >
        {loading && <option value="">Đang tải…</option>}
        {!loading && !voices.length && <option value="">Chưa có giọng</option>}
        {voices.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  );
}
