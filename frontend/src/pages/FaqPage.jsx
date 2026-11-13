import PageShell from "../components/PageShell";

export default function FaqPage() {
  return (
    <PageShell
      title="Kho câu hỏi"
      subtitle="Cặp câu hỏi – câu trả lời soạn sẵn, khớp bằng embedding"
    >
      <div className="rounded-2xl border border-line bg-surface p-8 text-center">
        <p className="m-0 text-[14px] font-semibold">Kho đang trống</p>
        <p className="mx-auto mt-2 mb-0 max-w-[460px] text-[12.5px] leading-relaxed text-faint">
          Giai đoạn P5 thêm bảng quản trị, nhập CSV, chống trùng và chỉ số khớp.
          Giai đoạn P4 dựng giao diện; hiện tại trang này giữ chỗ cho deep link
          <code className="mx-1 rounded bg-white/[0.06] px-1.5 py-px font-mono text-[11px]">/faq</code>.
        </p>
      </div>
    </PageShell>
  );
}
