export default function PanelSection({ title, children }) {
  return (
    <section className="mb-4 rounded-xl border border-line bg-white/[0.02] p-3">
      <h2 className="m-0 mb-2 text-[11px] font-semibold tracking-[0.08em] text-faint uppercase">
        {title}
      </h2>
      {children}
    </section>
  );
}
