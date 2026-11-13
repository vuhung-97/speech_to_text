import PageShell from "../components/PageShell";

export default function SettingsPage() {
  return (
    <PageShell title="Cài đặt" subtitle="Model, micro, nhận dạng và giọng đọc">
      <div className="rounded-2xl border border-line bg-surface p-8 text-center">
        <p className="m-0 text-[14px] font-semibold">Cài đặt đang ở drawer</p>
        <p className="mx-auto mt-2 mb-0 max-w-[460px] text-[12.5px] leading-relaxed text-faint">
          Nhấn <kbd className="rounded border border-line bg-white/[0.04] px-1.5 py-px font-mono text-[11px]">Ctrl</kbd>
          {" + "}
          <kbd className="rounded border border-line bg-white/[0.04] px-1.5 py-px font-mono text-[11px]">,</kbd>
          {" "}ở trang Hỏi đáp. Giai đoạn P4 chuyển toàn bộ biểu mẫu sang trang này và
          thêm mục giọng đọc, tốc độ, tự động đọc.
        </p>
      </div>
    </PageShell>
  );
}
