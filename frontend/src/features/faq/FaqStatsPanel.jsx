import Button from "../../components/ui/Button";

export default function FaqStatsPanel({ stats, unanswered, audit, onReindex, busy }) {
  return (
    <>
      <section className="mb-4 rounded-xl border border-line bg-wash p-3">
        <h2 className="m-0 mb-2 text-[12px] font-semibold tracking-[0.08em] text-faint uppercase">
          Kho câu hỏi
        </h2>
        <dl className="m-0 grid grid-cols-2 gap-y-1.5 text-[12px]">
          <dt className="text-faint">Câu hỏi</dt>
          <dd className="m-0 text-right text-content">{stats.entries ?? 0}</dd>
          <dt className="text-faint">Đang bật</dt>
          <dd className="m-0 text-right text-content">{stats.active ?? 0}</dd>
          <dt className="text-faint">Đã embedding</dt>
          <dd className="m-0 text-right text-content">{stats.embedded ?? 0}</dd>
          <dt className="text-faint">Ngưỡng khớp</dt>
          <dd className="m-0 text-right text-content">
            {stats.threshold != null ? `${Math.round(stats.threshold * 100)}%` : "—"}
          </dd>
          <dt className="text-faint">Model</dt>
          <dd className="m-0 truncate text-right font-mono text-[12px] text-dim">
            {stats.model || "—"}
          </dd>
        </dl>
        {stats.embed_note && (
          <p className="mt-2 mb-0 rounded-lg border border-accent/30 bg-accent/[0.08] px-2 py-1.5 text-[12px] leading-relaxed text-accent">
            {stats.embed_note}
          </p>
        )}
        <Button
          variant="secondary"
          size="sm"
          className="mt-2 w-full"
          onClick={onReindex}
          disabled={busy}
        >
          Embedding lại
        </Button>
      </section>

      <section className="mb-4 rounded-xl border border-line bg-wash p-3">
        <h2 className="m-0 mb-2 text-[12px] font-semibold tracking-[0.08em] text-faint uppercase">
          Chưa có đáp án
        </h2>
        {unanswered.length === 0 ? (
          <p className="m-0 text-[12px] text-faint">Chưa có câu nào bị bỏ trống.</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
            {unanswered.slice(0, 6).map((item) => (
              <li key={item.question_norm} className="text-[12px] text-dim">
                <span className="text-content">{item.sample || item.question_norm}</span>
                <span className="ml-1 font-mono text-[12px] text-faint">
                  ×{item.asks}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-line bg-wash p-3">
        <h2 className="m-0 mb-2 text-[12px] font-semibold tracking-[0.08em] text-faint uppercase">
          Hoạt động gần đây
        </h2>
        {audit.length === 0 ? (
          <p className="m-0 text-[12px] text-faint">Chưa có thao tác nào.</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {audit.slice(0, 6).map((item) => (
              <li key={item.id} className="flex items-baseline gap-1.5 text-[12px]">
                <span className="font-mono text-faint">{item.action}</span>
                <span className="truncate text-dim">{item.target || item.detail}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
