import { Link } from "react-router-dom";

import PageShell from "../components/PageShell";

export default function NotFoundPage() {
  return (
    <PageShell title="Không tìm thấy trang" subtitle="Đường dẫn không tồn tại trong ứng dụng">
      <div className="rounded-2xl border border-line bg-surface p-8 text-center">
        <p className="m-0 text-[14px] font-semibold">404</p>
        <p className="mx-auto mt-2 mb-4 max-w-[420px] text-[12.5px] leading-relaxed text-faint">
          Có thể liên kết đã cũ hoặc bạn gõ nhầm địa chỉ.
        </p>
        <Link
          to="/"
          className="inline-flex rounded-lg bg-gradient-to-br from-accent to-accent-2 px-4 py-2 text-[12.5px] font-semibold text-[#201505] transition hover:brightness-110"
        >
          Về trang hỏi đáp
        </Link>
      </div>
    </PageShell>
  );
}
