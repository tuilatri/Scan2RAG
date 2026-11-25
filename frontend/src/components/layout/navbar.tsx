import React from "react"
import { ShieldCheck, FileText, Bot, RefreshCw } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

interface NavbarProps {
  activeTab: "chat" | "ocr"
  onTabChange: (tab: "chat" | "ocr") => void
  backendStatus?: "connected" | "connecting" | "offline"
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  backendStatus = "connected",
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-4 sm:px-6">
        {/* Brand Logo & Name */}
        <div className="flex items-center space-x-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold shadow-sm">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold tracking-tight text-foreground">
                Scan2RAG
              </span>
              <Badge variant="outline" className="text-[10px] font-mono px-1.5 py-0 h-4">
                v0.2.0 (Milestone 3)
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground hidden sm:block">
              Trợ lý Tra cứu Văn bản Pháp luật & Tiêu chuẩn Sức khỏe Quân sự
            </p>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center space-x-1 bg-muted p-0.5 rounded-lg border">
          <Button
            size="sm"
            variant={activeTab === "chat" ? "default" : "ghost"}
            className="h-8 text-xs font-medium px-3"
            onClick={() => onTabChange("chat")}
          >
            <Bot className="h-3.5 w-3.5 mr-1.5" />
            Trợ lý Tra cứu RAG
          </Button>
          <Button
            size="sm"
            variant={activeTab === "ocr" ? "default" : "ghost"}
            className="h-8 text-xs font-medium px-3"
            onClick={() => onTabChange("ocr")}
          >
            <FileText className="h-3.5 w-3.5 mr-1.5" />
            Đối soát OCR (HITL)
          </Button>
        </div>

        {/* System Health Status */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5">
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus === "connected"
                  ? "bg-emerald-500 animate-pulse"
                  : backendStatus === "connecting"
                  ? "bg-amber-500"
                  : "bg-destructive"
              }`}
            />
            <span className="text-xs text-muted-foreground hidden md:inline-block">
              {backendStatus === "connected"
                ? "Backend & Qdrant Sẵn sàng"
                : backendStatus === "connecting"
                ? "Đang kết nối..."
                : "Mất kết nối"}
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}
