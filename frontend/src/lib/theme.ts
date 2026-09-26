const DARK_QUERY = "(prefers-color-scheme: dark)";
const THEME_STORAGE_KEY = "project-start.theme";
const THEME_CHANGE_EVENT = "project-start:theme-change";

export type ThemeMode = "light" | "dark";

function applyTheme(dark: boolean) {
  document.documentElement.classList.toggle("dark", dark);
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", dark ? "#020617" : "#3563e9");
  window.dispatchEvent(new CustomEvent(THEME_CHANGE_EVENT, { detail: { dark } }));
}

function getSavedTheme(): ThemeMode | null {
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    return saved === "light" || saved === "dark" ? saved : null;
  } catch {
    return null;
  }
}

export function isDarkTheme(): boolean {
  return document.documentElement.classList.contains("dark");
}

export function toggleTheme(): ThemeMode {
  const next: ThemeMode = isDarkTheme() ? "light" : "dark";
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, next);
  } catch {
    // Some embedded webviews disable persistent storage; the live switch
    // still works for the current session.
  }
  applyTheme(next === "dark");
  return next;
}

export function subscribeToTheme(listener: (dark: boolean) => void): () => void {
  const handler = (event: Event) => {
    listener(Boolean((event as CustomEvent<{ dark: boolean }>).detail?.dark));
  };
  window.addEventListener(THEME_CHANGE_EVENT, handler);
  return () => window.removeEventListener(THEME_CHANGE_EVENT, handler);
}

/** Follow the device theme. MAX renders the Mini App in its system webview,
 * so the same media query also tracks the device appearance inside MAX. */
export function initializeTheme() {
  const media = window.matchMedia(DARK_QUERY);
  const saved = getSavedTheme();
  applyTheme(saved ? saved === "dark" : media.matches);
  const listener = (event: MediaQueryListEvent) => {
    if (getSavedTheme() === null) applyTheme(event.matches);
  };
  media.addEventListener?.("change", listener);
}
