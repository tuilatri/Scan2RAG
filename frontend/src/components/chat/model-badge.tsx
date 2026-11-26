import React from 'react';
import { Cpu, Cloud } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface ModelBadgeProps {
  provider?: string;
  model?: string;
}

const cloudProviderLabel = (provider?: string): string => {
  const value = (provider || '').toLowerCase();
  if (value.includes('groq')) return 'Groq';
  if (value.includes('openrouter')) return 'OpenRouter';
  if (value.includes('gemini')) return 'Gemini';
  if (value.includes('offline')) return 'Offline';
  return 'Cloud';
};

export const ModelBadge: React.FC<ModelBadgeProps> = ({ provider, model }) => {
  if (!provider && !model) return null;

  const isLocal = provider?.toLowerCase().includes('local') || provider?.toLowerCase().includes('lm_studio');

  return (
    <div className="inline-flex items-center space-x-1.5 text-xs text-muted-foreground bg-muted/60 px-2 py-0.5 rounded-full border">
      {isLocal ? (
        <>
          <Cpu className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          <span className="font-mono text-[11px]">Local: {model || 'Qwen2.5'}</span>
          <Badge variant="outline" className="text-[9px] py-0 px-1 border-emerald-500/30 text-emerald-600">
            Private
          </Badge>
        </>
      ) : (
        <>
          <Cloud className="h-3 w-3 text-blue-600 dark:text-blue-400" />
          <span className="font-mono text-[11px]">Cloud: {model || 'LLaMA-3.3-70B'}</span>
          <Badge variant="outline" className="text-[9px] py-0 px-1 border-blue-500/30 text-blue-600">
            {cloudProviderLabel(provider)}
          </Badge>
        </>
      )}
    </div>
  );
};
