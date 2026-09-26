function createTokenStore(storageKey: string) {
  let inMemoryToken: string | null = null;

  return {
    get(): string | null {
      if (inMemoryToken) return inMemoryToken;
      try {
        inMemoryToken = sessionStorage.getItem(storageKey);
      } catch {
        inMemoryToken = null;
      }
      return inMemoryToken;
    },
    set(token: string): void {
      inMemoryToken = token;
      try {
        sessionStorage.setItem(storageKey, token);
      } catch {
        // sessionStorage unavailable (e.g. private mode) — token stays in memory only
      }
    },
    clear(): void {
      inMemoryToken = null;
      try {
        sessionStorage.removeItem(storageKey);
      } catch {
        // ignore
      }
    },
  };
}

const studentTokenStore = createTokenStore("project-start.token");
const adminTokenStore = createTokenStore("project-start.admin_token");

export const getToken = studentTokenStore.get;
export const setToken = studentTokenStore.set;
export const clearToken = studentTokenStore.clear;

export const getAdminToken = adminTokenStore.get;
export const setAdminToken = adminTokenStore.set;
export const clearAdminToken = adminTokenStore.clear;
