import AppShell from "../app/AppShell";
import EmptyState from "../components/ui/EmptyState";
import LinkButton from "../components/ui/LinkButton";

export default function NotFoundPage() {
  return (
    <AppShell title="Không tìm thấy trang" subtitle="Đường dẫn không tồn tại">
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-10">
        <div className="mx-auto max-w-[620px]">
          <EmptyState
            title="404"
            hint="Có thể liên kết đã cũ hoặc bạn gõ nhầm địa chỉ."
            action={<LinkButton to="/">Về trang hỏi đáp</LinkButton>}
          />
        </div>
      </div>
    </AppShell>
  );
}
