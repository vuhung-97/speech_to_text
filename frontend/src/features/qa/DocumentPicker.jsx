// Question-set filter for the Q&A screen: search everywhere or one set only.

import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";

export default function DocumentPicker({ documents, value, onChange, disabled }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-semibold tracking-[0.08em] text-faint uppercase">
        Bộ đề
      </span>
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
