import React from "react"
import { ShieldCheck } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface NavbarProps {
  backendStatus?: "connected" | "connecting" | "offline"
}

export const Navbar: React.FC<NavbarProps> = ({
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
                v0.4.1
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground hidden sm:block">
              Trợ lý Tra cứu Văn bản Pháp luật & Tiêu chuẩn Sức khỏe Quân sự
            </p>
          </div>
        </div>

        {/* System Health Status */}
        <div className="flex items-center space-x-3" role="status" aria-live="polite">
          <div className="flex items-center space-x-1.5">
            <span
              role="img"
              aria-label={
                backendStatus === "connected"
                  ? "Hệ thống chạy"
                  : backendStatus === "connecting"
                  ? "Đang kết nối"
                  : "Hệ thống dừng"
              }
              className={`h-2 w-2 rounded-full ${
                backendStatus === "connected"
                  ? "bg-emerald-500"
                  : backendStatus === "connecting"
                  ? "bg-amber-500"
                  : "bg-destructive"
              }`}
            />
            <span className="text-xs text-muted-foreground hidden md:inline-block">
              {backendStatus === "connected"
                ? "Hệ thống chạy"
                : backendStatus === "connecting"
                ? "Đang kết nối"
                : "Mất kết nối"}
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}
