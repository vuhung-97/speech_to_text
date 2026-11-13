import { Link } from "react-router-dom";

import AppShell from "../app/AppShell";
import EmptyState from "../components/ui/EmptyState";

export default function NotFoundPage() {
  return (
    <AppShell title="Không tìm thấy trang" subtitle="Đường dẫn không tồn tại">
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-10">
        <div className="mx-auto max-w-[620px]">
          <EmptyState
            title="404"
            hint="Có thể liên kết đã cũ hoặc bạn gõ nhầm địa chỉ."
            action={
              <Link
                to="/"
                className="inline-flex rounded-control bg-gradient-to-br from-accent to-accent-2 px-4 py-2 text-[12.5px] font-semibold text-[#201505]"
              >
                Về trang hỏi đáp
              </Link>
            }
          />
        </div>
      </div>
    </AppShell>
  );
}
