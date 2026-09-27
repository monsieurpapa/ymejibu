import { CircleAlert, CircleCheck, Info } from "lucide-react";
import { useApp } from "../state";

/** Short confirmation at the bottom of the screen (announced politely to screen readers). */
export default function ToastHost() {
  const { toast } = useApp();
  const Icon = toast?.tone === "green" ? CircleCheck : toast?.tone === "blue" ? Info : CircleAlert;
  return (
    <div className="toast-wrap" role="status" aria-live="polite">
      {toast && (
        <div key={toast.id} className={`toast tone-${toast.tone}`} data-testid="toast">
          <Icon size={20} aria-hidden="true" />
          <span>{toast.text}</span>
        </div>
      )}
    </div>
  );
}
