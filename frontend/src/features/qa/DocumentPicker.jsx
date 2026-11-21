// Question-set filter for the Q&A screen: search everywhere or one set only.

export default function DocumentPicker({ documents, value, onChange, disabled }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-semibold tracking-[0.08em] text-faint uppercase">
        Bộ đề
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className="w-full rounded-control border border-line bg-white/[0.03] px-2.5 py-2 text-[12.5px] text-white outline-none focus:border-accent/60"
      >
        <option value="">Tất cả bộ đề</option>
        {documents.map((document) => (
          <option key={document.id} value={document.id}>
            {document.name} ({document.entry_count})
          </option>
        ))}
      </select>
    </label>
  );
}
