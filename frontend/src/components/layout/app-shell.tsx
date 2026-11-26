import React from "react"
import { Navbar } from "./navbar"

interface AppShellProps {
  children: React.ReactNode
  activeTab: "chat" | "ocr" | "compare"
  onTabChange: (tab: "chat" | "ocr" | "compare") => void
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  activeTab,
  onTabChange,
}) => {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground font-sans">
      <Navbar activeTab={activeTab} onTabChange={onTabChange} />
      <main className="flex-1 flex overflow-hidden">{children}</main>
    </div>
  )
}
