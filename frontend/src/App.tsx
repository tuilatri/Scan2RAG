import { useState } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Bot, FileText, CheckCircle2, ArrowRight } from "lucide-react"

export default function App() {
  const [activeTab, setActiveTab] = useState<"chat" | "ocr">("chat")

  return (
    <AppShell activeTab={activeTab} onTabChange={setActiveTab}>
      <div className="flex-1 p-6 md:p-8 max-w-6xl mx-auto flex flex-col justify-center items-center space-y-6">
        <div className="text-center space-y-2">
          <Badge variant="outline" className="text-xs px-2.5 py-0.5 border-primary/30 text-primary">
            Khung Giao diện Nền tảng Đã Sẵn sàng (Phase 1)
          </Badge>
          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Scan2RAG Document Intelligence
          </h1>
          <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
            Hệ thống hỏi đáp và đối soát tài liệu scan quy phạm pháp luật & tiêu chuẩn sức khỏe nghĩa vụ quân sự Việt Nam.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-4xl">
          {/* Card 1: Chatbot Preview */}
          <Card className={`transition-all border-2 ${activeTab === "chat" ? "border-primary shadow-md" : "hover:border-border"}`}>
            <CardHeader>
              <div className="flex items-center space-x-2">
                <div className="p-2 rounded-md bg-primary/10 text-primary">
                  <Bot className="h-5 w-5" />
                </div>
                <CardTitle>Màn hình 1: Trợ lý Tra cứu RAG</CardTitle>
              </div>
              <CardDescription>
                Hỏi đáp điều khoản pháp luật, bảng phân loại sức khỏe cận thị, thị lực với trích dẫn trang PDF scan gốc.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-xs space-y-1.5 text-muted-foreground">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span>Server-Sent Events (SSE) Streaming thời gian thực (TTFB ~0.9s)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span>Dual-Pane Interactive PDF Viewer trỏ đúng số trang</span>
                </div>
              </div>
              <Button
                className="w-full mt-4"
                variant={activeTab === "chat" ? "default" : "outline"}
                onClick={() => setActiveTab("chat")}
              >
                <span>Xem Màn hình Tra cứu (Phase 2)</span>
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </CardContent>
          </Card>

          {/* Card 2: HITL Review Preview */}
          <Card className={`transition-all border-2 ${activeTab === "ocr" ? "border-primary shadow-md" : "hover:border-border"}`}>
            <CardHeader>
              <div className="flex items-center space-x-2">
                <div className="p-2 rounded-md bg-secondary text-foreground">
                  <FileText className="h-5 w-5" />
                </div>
                <CardTitle>Màn hình 2: Đối soát OCR (HITL)</CardTitle>
              </div>
              <CardDescription>
                Đối chiếu ảnh scan gốc bên trái và cấu trúc bảng biểu Markdown bên phải để người quản trị duyệt dữ liệu.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-xs space-y-1.5 text-muted-foreground">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span>So sánh ảnh gốc vs OCR Markdown</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span>Hiệu chỉnh trực tiếp ô bảng và lưu bản phê duyệt</span>
                </div>
              </div>
              <Button
                className="w-full mt-4"
                variant={activeTab === "ocr" ? "default" : "outline"}
                onClick={() => setActiveTab("ocr")}
              >
                <span>Xem Màn hình Đối soát (Phase 3)</span>
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
