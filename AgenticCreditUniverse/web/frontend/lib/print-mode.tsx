"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface PrintModeValue {
  printing: boolean;
  requestPrint: () => void;
}

const PrintModeContext = createContext<PrintModeValue | null>(null);

export function PrintModeProvider({ children }: { children: ReactNode }) {
  const [printing, setPrinting] = useState(false);

  useEffect(() => {
    const onAfter = () => setPrinting(false);
    window.addEventListener("afterprint", onAfter);
    return () => window.removeEventListener("afterprint", onAfter);
  }, []);

  function requestPrint() {
    setPrinting(true);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        window.print();
      });
    });
  }

  return (
    <PrintModeContext.Provider value={{ printing, requestPrint }}>
      {children}
    </PrintModeContext.Provider>
  );
}

export function usePrintMode(): PrintModeValue {
  const ctx = useContext(PrintModeContext);
  if (!ctx) throw new Error("usePrintMode must be used within PrintModeProvider");
  return ctx;
}
