"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { flushSync } from "react-dom";

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
    console.log("[print] 1/3 requestPrint — flushSync");
    flushSync(() => {
      setPrinting(true);
    });
    console.log("[print] 2/3 commit done — scheduling print");
    setTimeout(() => {
      console.log("[print] 3/3 calling window.print()");
      window.print();
    }, 80);
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
