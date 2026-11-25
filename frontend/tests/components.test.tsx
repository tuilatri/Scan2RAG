import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Navbar } from '@/components/layout/navbar';

describe('Atomic shadcn/ui components', () => {
  it('renders Button correctly with default variant', () => {
    render(<Button>Click me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary');
  });

  it('renders Badge with variants', () => {
    render(<Badge variant="secondary">TT 105/2023</Badge>);
    const badge = screen.getByText('TT 105/2023');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-secondary');
  });

  it('renders Card with header and content', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Legal Intelligence</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Scan2RAG System</p>
        </CardContent>
      </Card>
    );
    expect(screen.getByText('Legal Intelligence')).toBeInTheDocument();
    expect(screen.getByText('Scan2RAG System')).toBeInTheDocument();
  });
});

describe('Layout Components', () => {
  it('renders Navbar with title and view tabs', () => {
    render(
      <Navbar
        activeTab="chat"
        onTabChange={() => {}}
        backendStatus="connected"
      />
    );
    expect(screen.getByText('Scan2RAG')).toBeInTheDocument();
    expect(screen.getByText(/Trợ lý Tra cứu Văn bản Pháp luật/i)).toBeInTheDocument();
    expect(screen.getByText('Trợ lý Tra cứu RAG')).toBeInTheDocument();
    expect(screen.getByText('Đối soát OCR (HITL)')).toBeInTheDocument();
    expect(screen.getByText('Backend & Qdrant Sẵn sàng')).toBeInTheDocument();
  });
});
