import React, { useState, useEffect } from 'react';

/**
 * ResizableDivider Component
 * Direction: 'horizontal' (vertical separator bar, resizes left/right)
 *            'vertical' (horizontal separator bar, resizes top/bottom)
 */
export default function ResizableDivider({
  direction = 'horizontal',
  onResize,
  onReset,
  title = 'Drag to resize, double-click to reset'
}) {
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      onResize(e);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.body.classList.remove('is-resizing');
    };

    document.body.classList.add('is-resizing');
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.body.classList.remove('is-resizing');
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, onResize]);

  const isH = direction === 'horizontal';

  return (
    <div
      className={`resizer ${isH ? 'resizer-col' : 'resizer-row'} ${isDragging ? 'dragging' : ''}`}
      onMouseDown={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDoubleClick={(e) => {
        e.preventDefault();
        if (onReset) onReset();
      }}
      title={title}
      role="separator"
      tabIndex={0}
      aria-orientation={isH ? 'vertical' : 'horizontal'}
    >
      <div className="resizer-handle" />
    </div>
  );
}
