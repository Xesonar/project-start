import { useEffect, useState } from "react";

import { getMyApplications, type Application } from "@/api/applications";

const SEEN_KEY = "project-start.seen_applications";

function getSeenIds(): Set<number> {
  try {
    const raw = sessionStorage.getItem(SEEN_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

export function markApplicationsSeen(applications: Application[]): void {
  try {
    const decidedIds = applications
      .filter((a) => a.status === "accepted" || a.status === "rejected")
      .map((a) => a.id);
    sessionStorage.setItem(SEEN_KEY, JSON.stringify(decidedIds));
  } catch {
    // sessionStorage unavailable — badge just won't persist across reloads
  }
}

/** Count of applications whose status was resolved (accepted/rejected) since
 * the student last opened "Мои отклики" — a lightweight in-app notification,
 * no backend Notification model needed for the MVP. */
export function useUnseenDecidedApplicationsCount(): number {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getMyApplications()
      .then((applications) => {
        if (cancelled) return;
        const seen = getSeenIds();
        const unseen = applications.filter(
          (a) =>
            (a.status === "accepted" || a.status === "rejected") && !seen.has(a.id),
        );
        setCount(unseen.length);
      })
      .catch(() => setCount(0));
    return () => {
      cancelled = true;
    };
  }, []);

  return count;
}
