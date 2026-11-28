import React from "react"
import { Navbar } from "./navbar"

interface AppShellProps {
  children: React.ReactNode
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground font-sans">
      <Navbar />
      <main className="flex-1 flex overflow-hidden">{children}</main>
    </div>
  )
}
