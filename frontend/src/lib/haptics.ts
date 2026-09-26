import { getMaxWebApp } from "@/max/webapp";

/**
 * Haptic feedback that no-ops outside MAX.
 *
 * Call it at the *start* of an interaction (onTap, not after the async work)
 * — the brain pairs the vibration with the finger lift, not with the result.
 */
export function haptic(style: "light" | "medium" | "heavy" = "light"): void {
  getMaxWebApp()?.HapticFeedback?.impactOccurred(style);
}

/** Selection-changed tick — for chip toggles, filters, role pickers. */
export function hapticSelect(): void {
  const feedback = getMaxWebApp()?.HapticFeedback;
  if (feedback?.selectionChanged) {
    feedback.selectionChanged();
    return;
  }
  haptic("light");
}

/** Confirmation kick — "application sent", "team formed". */
export function hapticSuccess(): void {
  const feedback = getMaxWebApp()?.HapticFeedback;
  if (feedback?.notificationOccurred) {
    feedback.notificationOccurred("success");
    return;
  }
  haptic("heavy");
}

export function hapticError(): void {
  const feedback = getMaxWebApp()?.HapticFeedback;
  if (feedback?.notificationOccurred) {
    feedback.notificationOccurred("error");
    return;
  }
  haptic("heavy");
}
