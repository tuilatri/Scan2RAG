import * as React from 'react';
import * as ScrollAreaPrimitive from '@radix-ui/react-scroll-area';
import { cn } from '@/lib/utils';

type ThinScrollAreaProps = React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root> & {
  orientation?: 'vertical' | 'horizontal' | 'both';
  viewportClassName?: string;
};

export const ThinScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  ThinScrollAreaProps
>(({ className, viewportClassName, orientation = 'vertical', children, ...props }, ref) => {
  const showVertical = orientation === 'vertical' || orientation === 'both';
  const showHorizontal = orientation === 'horizontal' || orientation === 'both';

  return (
    <ScrollAreaPrimitive.Root
      ref={ref}
      className={cn('relative overflow-hidden', className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        className={cn('h-full w-full rounded-[inherit]', viewportClassName)}
      >
        {children}
      </ScrollAreaPrimitive.Viewport>
      {showVertical && (
        <ScrollAreaPrimitive.ScrollAreaScrollbar
          orientation="vertical"
          className="flex w-1.5 touch-none select-none p-0.5 transition-colors"
        >
          <ScrollAreaPrimitive.ScrollAreaThumb className="relative flex-1 rounded-full bg-border/70 hover:bg-border" />
        </ScrollAreaPrimitive.ScrollAreaScrollbar>
      )}
      {showHorizontal && (
        <ScrollAreaPrimitive.ScrollAreaScrollbar
          orientation="horizontal"
          className="flex h-1.5 flex-col touch-none select-none p-0.5 transition-colors"
        >
          <ScrollAreaPrimitive.ScrollAreaThumb className="relative flex-1 rounded-full bg-border/70 hover:bg-border" />
        </ScrollAreaPrimitive.ScrollAreaScrollbar>
      )}
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  );
});
ThinScrollArea.displayName = 'ThinScrollArea';
