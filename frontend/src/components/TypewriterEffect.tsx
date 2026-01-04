import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";

interface TypewriterEffectProps {
  content: string;
  className?: string;
  onComplete?: () => void;
  speed?: number;
  mdComponents?: any;
}

export function TypewriterEffect({
  content,
  className,
  onComplete,
  speed = 10,
  mdComponents,
}: TypewriterEffectProps) {
  const [displayedContent, setDisplayedContent] = useState("");
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    // If content is shorter than displayed (e.g. cleared), reset
    if (content.length < displayedContent.length) {
        setDisplayedContent("");
        setIsTyping(true);
    }
  }, [content]);

  useEffect(() => {
    if (!isTyping) {
        // If we finished typing but content grew, just show the full content immediately
        // or we could continue typing from where we left off.
        // For simplicity in streaming, if we are "done" but new tokens arrive, 
        // we usually want to just display them. 
        // But for a true typewriter effect on streaming, we need to handle the diff.
        // Given this is often used for the final block, let's keep it simple.
        if (content !== displayedContent) {
            setDisplayedContent(content);
        }
        return;
    }

    if (displayedContent.length < content.length) {
      const timeoutId = setTimeout(() => {
        setDisplayedContent(content.slice(0, displayedContent.length + 1));
      }, speed);

      return () => clearTimeout(timeoutId);
    } else {
      setIsTyping(false);
      onComplete?.();
    }
  }, [content, displayedContent, isTyping, speed, onComplete]);

  return (
    <div className={className}>
      <ReactMarkdown components={mdComponents}>{displayedContent}</ReactMarkdown>
    </div>
  );
}

