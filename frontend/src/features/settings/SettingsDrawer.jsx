import Drawer from "../../components/ui/Drawer";
import { useLive } from "../../shared/live/LiveProvider";
import SettingsActions from "./SettingsActions";
import SettingsForm from "./SettingsForm";

export default function SettingsDrawer({ open, onClose }) {
  const { engine } = useLive();
  const subtitle =
    engine.state === "loading"
      ? "đang nạp model…"
      : `${engine.model || "?"} · ${engine.cpu_threads ?? "?"} thread · ${
          engine.compute_type || "int8"
        }`;

  return (
    <Drawer
      open={open}
      onClose={onClose}
      label="Cài đặt"
      title="Cài đặt"
      subtitle={<span className="font-mono">{subtitle}</span>}
      headerClass="items-center px-5 py-3.5"
      contentClass="px-5 pt-3 pb-6"
      footer={<SettingsActions />}
    >
      <SettingsForm active={open} />
    </Drawer>
  );
}
