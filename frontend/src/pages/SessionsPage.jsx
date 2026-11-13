import PageShell from "../components/PageShell";

export default function SessionsPage() {
  return (
    <PageShell title="Phiên hội thoại" subtitle="Lịch sử hỏi đáp, lưu trên máy của bạn">
      <div className="rounded-2xl border border-line bg-surface p-8 text-center">
        <p className="m-0 text-[14px] font-semibold">Chưa có phiên nào</p>
        <p className="mx-auto mt-2 mb-0 max-w-[420px] text-[12.5px] leading-relaxed text-faint">
          Mỗi lần bạn hỏi, hệ thống tạo một phiên gồm câu hỏi, câu trả lời khớp và
          phần giọng đọc. Danh sách phiên sẽ xuất hiện ở đây ở giai đoạn P3.
        </p>
      </div>
    </PageShell>
  );
}
