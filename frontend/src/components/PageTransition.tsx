import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";

/** Keying on pathname remounts this div on every route change, re-triggering the
 * CSS fade-in — a cheap page-transition effect with no extra dependency. */
export default function PageTransition({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return (
    <div key={pathname} className="cc-page-enter">
      {children}
    </div>
  );
}
