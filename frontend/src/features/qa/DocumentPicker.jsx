// Question-set filter for the Q&A screen: search everywhere or one set only.

import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";

export default function DocumentPicker({
  documents,
  value,
  onChange,
  disabled,
  label = "Bộ đề",
}) {
  return (
    <label className="block min-w-0">
      <span className="mb-1 block text-[10.5px] text-faint">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className={`${FIELD_CLASS} w-full rounded-control px-2.5 py-2 ${FIELD_TEXT}`}
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
