import PanelSection from "./PanelSection";

export default function ReadingPanel({ speech, audioPlaying }) {
  const active = speech.busy || audioPlaying;
  return (
    <PanelSection title="Đang đọc">
      {active ? (
        <div className="space-y-1.5">
          <p className="m-0 text-[12px] text-white">
            {speech.status === "loading" ? "Đang tổng hợp…" : "Đang đọc câu trả lời"}
          </p>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2"
              style={{ width: `${Math.round(speech.progress * 100)}%` }}
            />
          </div>
          <p className="m-0 font-mono text-[12px] text-faint">
            {speech.seconds.toFixed(1)} s
            {speech.estimated ? ` / ~${Math.round(speech.estimated)} s` : ""}
          </p>
        </div>
      ) : (
        <p className="m-0 text-[12px] text-faint">
          Bấm “Đọc” ở câu trả lời để nghe. Audio được tạo theo luồng, không chờ
          hết văn bản.
        </p>
      )}
    </PanelSection>
  );
}
