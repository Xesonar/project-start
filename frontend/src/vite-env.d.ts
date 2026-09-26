/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_TEAM_CHAT_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
