// Settings route: the drawer opens by default, with a short map of what lives
// where. P6 moves the whole form in-page; until then the drawer is the form.

import { useState } from "react";

import AppShell from "../app/AppShell";
import SettingsDrawer from "../components/SettingsDrawer";

export default function SettingsPage() {
  const [open, setOpen] = useState(true);

  return (
    <AppShell title="Cài đặt" subtitle="Model, micro, nhận dạng và giọng đọc">
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-6">
        <div className="mx-auto max-w-[720px] space-y-3">
          <div className="rounded-card border border-line bg-surface-2/60 p-5">
            <h2 className="m-0 text-[14px] font-semibold">Bảng cài đặt</h2>
            <p className="mt-2 mb-3 text-[12.5px] leading-relaxed text-faint">
              Chọn model nhận dạng, thiết bị micro, chế độ chạy và các ngưỡng
              tách câu. Thay đổi có hiệu lực ngay hoặc sau khi nạp lại model tuỳ
              trường.
            </p>
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="rounded-control bg-gradient-to-br from-accent to-accent-2 px-3.5 py-2 text-[13px] font-semibold text-[#201505] transition hover:brightness-110"
            >
              Mở bảng cài đặt
            </button>
          </div>

          <div className="rounded-card border border-line bg-surface-2/60 p-5 text-[12.5px] leading-relaxed text-faint">
            <h2 className="m-0 mb-2 text-[14px] font-semibold text-white">
              Giọng đọc
            </h2>
            Chọn giọng và tốc độ trong bảng cài đặt; giọng đang dùng cũng được
            ghi nhớ cho lần đọc sau. Giới hạn đọc: 2000 từ mỗi lượt, audio ghi
            xuống đĩa và phát ngay khi tổng hợp.
          </div>
        </div>
      </div>

      <SettingsDrawer open={open} onClose={() => setOpen(false)} />
    </AppShell>
  );
}
