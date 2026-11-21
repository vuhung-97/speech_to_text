import Button from "../../components/ui/Button";

export default function FaqEntryForm({ form, editing, busy, onChange, onSubmit, onCancel }) {
  const update = (key, value) => onChange({ [key]: value });

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-card border border-line bg-surface-2/60 p-4"
    >
      <div className="mb-2 flex items-center justify-between">
        <h2 className="m-0 text-[13.5px] font-semibold">
          {editing ? "Sửa câu hỏi" : "Thêm câu hỏi"}
        </h2>
        {editing && (
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Huỷ sửa
          </Button>
        )}
      </div>

      <label className="mb-2 block">
        <span className="mb-1 block text-[12px] text-dim">Câu hỏi</span>
        <input
          value={form.question}
          onChange={(event) => update("question", event.target.value)}
          placeholder="Thủ đô Việt Nam là gì?"
          className="w-full rounded-control border border-line bg-white/[0.04] px-3 py-2 text-[13px] text-white outline-none placeholder:text-faint focus:border-accent/60"
        />
      </label>

      <label className="mb-2 block">
        <span className="mb-1 block text-[12px] text-dim">Câu trả lời</span>
        <textarea
          value={form.answer}
          onChange={(event) => update("answer", event.target.value)}
          rows={3}
          placeholder="Câu trả lời nguyên văn sẽ được đọc lên."
          className="w-full resize-y rounded-control border border-line bg-white/[0.04] px-3 py-2 text-[13px] leading-relaxed text-white outline-none placeholder:text-faint focus:border-accent/60"
        />
      </label>

      <div className="flex flex-wrap items-end gap-2">
        <label className="min-w-[180px] flex-1">
          <span className="mb-1 block text-[12px] text-dim">Danh mục</span>
          <input
            value={form.category}
            onChange={(event) => update("category", event.target.value)}
            placeholder="địa lý, thủ tục, chung…"
            className="w-full rounded-control border border-line bg-white/[0.04] px-3 py-2 text-[13px] text-white outline-none placeholder:text-faint focus:border-accent/60"
          />
        </label>
        <Button type="submit" variant="primary" disabled={busy}>
          {editing ? "Lưu thay đổi" : "Thêm vào kho"}
        </Button>
      </div>
    </form>
  );
}
