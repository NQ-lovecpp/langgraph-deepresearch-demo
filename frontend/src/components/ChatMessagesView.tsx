import type React from "react";
import type { Message } from "@langchain/langgraph-sdk";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Copy, CopyCheck } from "lucide-react";
import { InputForm } from "@/components/InputForm";
import { Button } from "@/components/ui/button";
import { useState, ReactNode, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  ActivityTimeline,
  ProcessedEvent,
} from "@/components/ActivityTimeline";
import { TypewriterEffect } from "@/components/TypewriterEffect";

// Markdown component props type from former ReportView
type MdComponentProps = {
  className?: string;
  children?: ReactNode;
  [key: string]: any;
};

// Markdown components (from former ReportView.tsx)
const mdComponents = {
  h1: ({ className, children, ...props }: MdComponentProps) => (
    <h1 className={cn("text-2xl font-bold mt-4 mb-2", className)} {...props}>
      {children}
    </h1>
  ),
  h2: ({ className, children, ...props }: MdComponentProps) => (
    <h2 className={cn("text-xl font-bold mt-3 mb-2", className)} {...props}>
      {children}
    </h2>
  ),
  h3: ({ className, children, ...props }: MdComponentProps) => (
    <h3 className={cn("text-lg font-bold mt-3 mb-1", className)} {...props}>
      {children}
    </h3>
  ),
  p: ({ className, children, ...props }: MdComponentProps) => (
    <p className={cn("mb-3 leading-7", className)} {...props}>
      {children}
    </p>
  ),
  a: ({ className, children, href, ...props }: MdComponentProps) => (
    <Badge className="text-xs mx-0.5 px-1 py-0 bg-neutral-800 hover:bg-neutral-700 border-neutral-600">
      <a
        className={cn("text-blue-400 hover:text-blue-300 text-xs no-underline", className)}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    </Badge>
  ),
  ul: ({ className, children, ...props }: MdComponentProps) => (
    <ul className={cn("list-disc pl-6 mb-3", className)} {...props}>
      {children}
    </ul>
  ),
  ol: ({ className, children, ...props }: MdComponentProps) => (
    <ol className={cn("list-decimal pl-6 mb-3", className)} {...props}>
      {children}
    </ol>
  ),
  li: ({ className, children, ...props }: MdComponentProps) => (
    <li className={cn("mb-1", className)} {...props}>
      {children}
    </li>
  ),
  blockquote: ({ className, children, ...props }: MdComponentProps) => (
    <blockquote
      className={cn(
        "border-l-4 border-neutral-600 pl-4 italic my-3 text-sm text-neutral-400",
        className
      )}
      {...props}
    >
      {children}
    </blockquote>
  ),
  code: ({ className, children, ...props }: MdComponentProps) => (
    <code
      className={cn(
        "bg-neutral-900 rounded px-1 py-0.5 font-mono text-xs text-amber-500",
        className
      )}
      {...props}
    >
      {children}
    </code>
  ),
  pre: ({ className, children, ...props }: MdComponentProps) => (
    <pre
      className={cn(
        "bg-neutral-900 p-3 rounded-lg overflow-x-auto font-mono text-xs my-3 border border-neutral-800",
        className
      )}
      {...props}
    >
      {children}
    </pre>
  ),
  hr: ({ className, ...props }: MdComponentProps) => (
    <hr className={cn("border-neutral-700 my-4", className)} {...props} />
  ),
  table: ({ className, children, ...props }: MdComponentProps) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-neutral-700">
      <table className={cn("border-collapse w-full", className)} {...props}>
        {children}
      </table>
    </div>
  ),
  th: ({ className, children, ...props }: MdComponentProps) => (
    <th
      className={cn(
        "bg-neutral-800 border-b border-neutral-700 px-3 py-2 text-left font-bold text-sm",
        className
      )}
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ className, children, ...props }: MdComponentProps) => (
    <td
      className={cn("border-b border-neutral-700 px-3 py-2 text-sm last:border-0", className)}
      {...props}
    >
      {children}
    </td>
  ),
};

// Props for HumanMessageBubble
interface HumanMessageBubbleProps {
  message: Message;
  mdComponents: typeof mdComponents;
}

// HumanMessageBubble Component
const HumanMessageBubble: React.FC<HumanMessageBubbleProps> = ({
  message,
  mdComponents,
}) => {
  return (
    <div
      className={`text-white rounded-3xl break-words min-h-7 bg-neutral-700/80 backdrop-blur-sm max-w-[100%] sm:max-w-[90%] px-5 pt-3 pb-3 rounded-br-sm shadow-md`}
    >
      <ReactMarkdown components={mdComponents}>
        {typeof message.content === "string"
          ? message.content
          : JSON.stringify(message.content)}
      </ReactMarkdown>
    </div>
  );
};

// Props for AiMessageBubble
interface AiMessageBubbleProps {
  message: Message;
  historicalActivity: ProcessedEvent[] | undefined;
  liveActivity: ProcessedEvent[] | undefined;
  isLastMessage: boolean;
  isOverallLoading: boolean;
  mdComponents: typeof mdComponents;
  handleCopy: (text: string, messageId: string) => void;
  copiedMessageId: string | null;
}

// AiMessageBubble Component
const AiMessageBubble: React.FC<AiMessageBubbleProps> = ({
  message,
  historicalActivity,
  liveActivity,
  isLastMessage,
  isOverallLoading,
  mdComponents,
  handleCopy,
  copiedMessageId,
}) => {
  // Determine which activity events to show and if it's for a live loading message
  const activityForThisBubble =
    isLastMessage && isOverallLoading ? liveActivity : historicalActivity;
  const isLiveActivityForThisBubble = isLastMessage && isOverallLoading;

  // For the last AI message, if it's NOT loading, we can use the typewriter effect.
  // But usually, LangGraph streams the final answer token by token or as a final chunk.
  // Since we receive the full message content updates, TypewriterEffect can smooth it out.
  // However, if we just want to animate the *final* answer appearance, we can do that.
  
  // Let's use TypewriterEffect for the last message if it has content.
  const shouldUseTypewriter = isLastMessage && message.content && message.content.length > 0;

  return (
    <div className={`relative break-words flex flex-col w-full max-w-[100%] sm:max-w-[95%]`}>
      {activityForThisBubble && activityForThisBubble.length > 0 && (
        <div className="mb-4">
          <ActivityTimeline
            processedEvents={activityForThisBubble}
            isLoading={isLiveActivityForThisBubble}
          />
        </div>
      )}
      
      {message.content && (
        <div className="bg-transparent text-neutral-100 rounded-lg">
            {shouldUseTypewriter ? (
                <TypewriterEffect 
                    content={typeof message.content === "string" ? message.content : JSON.stringify(message.content)}
                    mdComponents={mdComponents}
                    speed={2} // Very fast typing for better UX
                />
            ) : (
                <ReactMarkdown components={mdComponents}>
                    {typeof message.content === "string"
                    ? message.content
                    : JSON.stringify(message.content)}
                </ReactMarkdown>
            )}
        </div>
      )}

      {message.content && message.content.length > 0 && (
        <div className="mt-2 flex justify-end">
            <Button
                variant="ghost"
                size="sm"
                className={`cursor-pointer hover:bg-neutral-700/50 text-neutral-400 hover:text-neutral-200 h-8 px-2`}
                onClick={() =>
                handleCopy(
                    typeof message.content === "string"
                    ? message.content
                    : JSON.stringify(message.content),
                    message.id!
                )
                }
            >
                <span className="text-xs mr-2">{copiedMessageId === message.id ? "Copied" : "Copy"}</span>
                {copiedMessageId === message.id ? <CopyCheck className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            </Button>
        </div>
      )}
    </div>
  );
};

interface ChatMessagesViewProps {
  messages: Message[];
  isLoading: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  onSubmit: (inputValue: string, effort: string, model: string) => void;
  onCancel: () => void;
  liveActivityEvents: ProcessedEvent[];
  historicalActivities: Record<string, ProcessedEvent[]>;
}

export function ChatMessagesView({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  liveActivityEvents,
  historicalActivities,
}: ChatMessagesViewProps) {
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  const handleCopy = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000); // Reset after 2 seconds
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };
  return (
    <div className="flex flex-col h-full bg-neutral-900">
      <ScrollArea className="flex-1 overflow-y-auto" ref={scrollAreaRef}>
        <div className="w-full max-w-4xl mx-auto px-4 py-8 space-y-6">
          {messages.map((message, index) => {
            const isLast = index === messages.length - 1;
            return (
              <div key={message.id || `msg-${index}`} className="w-full">
                <div
                  className={`flex items-start gap-4 ${
                    message.type === "human" ? "justify-end" : "justify-start"
                  }`}
                >
                  {message.type === "human" ? (
                    <HumanMessageBubble
                      message={message}
                      mdComponents={mdComponents}
                    />
                  ) : (
                    <AiMessageBubble
                      message={message}
                      historicalActivity={historicalActivities[message.id!]}
                      liveActivity={liveActivityEvents} // Pass global live events
                      isLastMessage={isLast}
                      isOverallLoading={isLoading} // Pass global loading state
                      mdComponents={mdComponents}
                      handleCopy={handleCopy}
                      copiedMessageId={copiedMessageId}
                    />
                  )}
                </div>
              </div>
            );
          })}
          
          {/* Show loader only if we are loading AND the last message is NOT from AI yet (e.g. initial connection) 
              OR if the last AI message has no content yet but has activity.
          */}
          {isLoading &&
            (messages.length === 0 ||
              messages[messages.length - 1].type === "human") && (
              <div className="w-full max-w-4xl mx-auto">
                <div className="max-w-[100%] sm:max-w-[95%]">
                  {liveActivityEvents.length > 0 ? (
                    <ActivityTimeline
                        processedEvents={liveActivityEvents}
                        isLoading={true}
                    />
                  ) : (
                    <div className="flex items-center gap-2 p-4 text-neutral-400 animate-pulse">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      <span>Initializing agent...</span>
                    </div>
                  )}
                </div>
              </div>
            )}
        </div>
      </ScrollArea>
      <div className="w-full border-t border-neutral-800 bg-neutral-900/95 backdrop-blur supports-[backdrop-filter]:bg-neutral-900/60">
        <div className="max-w-4xl mx-auto">
            <InputForm
                onSubmit={onSubmit}
                isLoading={isLoading}
                onCancel={onCancel}
                hasHistory={messages.length > 0}
            />
        </div>
      </div>
    </div>
  );
}
