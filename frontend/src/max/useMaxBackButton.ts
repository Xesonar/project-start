import { useEffect } from "react";

import { getMaxWebApp } from "@/max/webapp";

/** Connects nested screens to MAX's native header back button. */
export function useMaxBackButton(onBack: () => void, visible = true): void {
  useEffect(() => {
    const backButton = getMaxWebApp()?.BackButton;
    if (!backButton || !visible) return;

    backButton.show();
    backButton.onClick(onBack);
    return () => {
      backButton.offClick(onBack);
      backButton.hide();
    };
  }, [onBack, visible]);
}
