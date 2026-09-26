// Thin wrapper around MAX Bridge (window.WebApp), loaded via the <script> tag
// in index.html (https://st.max.ru/js/max-web-app.js). Only wraps methods
// confirmed in the official docs (dev.max.ru/docs/webapps/bridge) — verify
// against a real MAX client before relying on anything not listed here.

export interface MaxWebApp {
  initData: string;
  initDataUnsafe: unknown;
  platform: string;
  version: string;
  deviceName?: string;
  openLink(url: string): void;
  openMaxLink(url: string): void;
  shareContent?(params: { text?: string; link?: string }): void;
  shareMaxContent(params: { text?: string; link?: string } | { mid: string; chatType: "DIALOG" | "CHAT" }): void;
  BackButton: {
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
  };
  HapticFeedback?: {
    impactOccurred(style: "soft" | "light" | "medium" | "heavy" | "rigid"): void;
    notificationOccurred(type: "error" | "success" | "warning"): void;
    selectionChanged(): void;
  };
}

declare global {
  interface Window {
    WebApp?: MaxWebApp;
  }
}

export function getMaxWebApp(): MaxWebApp | null {
  if (typeof window === "undefined") return null;
  const webApp = window.WebApp;
  // The CDN script also exposes a stub in an ordinary browser. It has no
  // signed initData and no native transport, so treating it as MAX produces
  // noisy bridge errors and hides browser fallbacks.
  return webApp?.initData ? webApp : null;
}

export function getInitData(): string | null {
  return typeof window !== "undefined" ? window.WebApp?.initData || null : null;
}

export function isRunningInMax(): boolean {
  return getInitData() !== null && getInitData() !== "";
}

/** Open ordinary web content outside the MAX webview. Returns true when
 * MAX handled the click, so callers can prevent the anchor's default action. */
export function openExternalLink(url: string): boolean {
  const webApp = getMaxWebApp();
  if (!webApp) return false;
  webApp.openLink(url);
  return true;
}
