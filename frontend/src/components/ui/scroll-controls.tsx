import React from 'react';
import { ChevronLeft, ChevronRight, ChevronUp, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ScrollControlsProps {
  direction?: 'horizontal' | 'vertical';
  onPrev: () => void;
  onNext: () => void;
  prevDisabled?: boolean;
  nextDisabled?: boolean;
  label?: string;
}

export const ScrollControls: React.FC<ScrollControlsProps> = ({
  direction = 'horizontal',
  onPrev,
  onNext,
  prevDisabled = false,
  nextDisabled = false,
  label = 'Cuộn',
}) => {
  const PrevIcon = direction === 'horizontal' ? ChevronLeft : ChevronUp;
  const NextIcon = direction === 'horizontal' ? ChevronRight : ChevronDown;

  return (
    <div className="flex shrink-0 items-center space-x-1" role="group" aria-label={label}>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-7 w-7 rounded-lg"
        onClick={onPrev}
        disabled={prevDisabled}
        aria-label={`${label} về trước`}
      >
        <PrevIcon className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-7 w-7 rounded-lg"
        onClick={onNext}
        disabled={nextDisabled}
        aria-label={`${label} tiếp`}
      >
        <NextIcon className="h-4 w-4" />
      </Button>
    </div>
  );
};
