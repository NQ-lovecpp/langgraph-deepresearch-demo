import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import {
  Loader2,
  TextSearch,
  Brain,
  Pen,
  ChevronDown,
  CheckCircle2,
  Globe,
  ChevronUp,
  FileText,
  ChevronRight,
} from "lucide-react";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

export interface ProcessedEvent {
  title: string;
  data: any;
}

interface ActivityTimelineProps {
  processedEvents: ProcessedEvent[];
  isLoading: boolean;
}

// Simple Markdown components for the timeline
const timelineMdComponents = {
  p: ({ className, children, ...props }: any) => (
    <p className={cn("mb-2 text-sm text-neutral-300 leading-relaxed", className)} {...props}>
      {children}
    </p>
  ),
  ul: ({ className, children, ...props }: any) => (
    <ul className={cn("list-disc pl-4 mb-2 text-sm text-neutral-300", className)} {...props}>
      {children}
    </ul>
  ),
  ol: ({ className, children, ...props }: any) => (
    <ol className={cn("list-decimal pl-4 mb-2 text-sm text-neutral-300", className)} {...props}>
      {children}
    </ol>
  ),
  li: ({ className, children, ...props }: any) => (
    <li className={cn("mb-1", className)} {...props}>
      {children}
    </li>
  ),
  a: ({ className, children, href, ...props }: any) => (
    <a
      className={cn("text-blue-400 hover:text-blue-300 underline", className)}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    >
      {children}
    </a>
  ),
  code: ({ className, children, ...props }: any) => (
    <code
      className={cn("bg-neutral-800 rounded px-1 py-0.5 font-mono text-xs text-amber-500", className)}
      {...props}
    >
      {children}
    </code>
  ),
};

const TimelineItem = ({ event, index, isLast, isLoading }: { event: ProcessedEvent, index: number, isLast: boolean, isLoading: boolean }) => {
    const [isItemExpanded, setIsItemExpanded] = useState(false);
    const hasData = !!event.data && (Array.isArray(event.data) ? event.data.length > 0 : true);

    const getEventIcon = (title: string) => {
        const iconClass = "h-4 w-4";
        if (isLoading && isLast) {
            return <Loader2 className={`${iconClass} animate-spin text-blue-400`} />;
        }
        
        const lowerTitle = title.toLowerCase();
        if (lowerTitle.includes("generating")) return <TextSearch className={`${iconClass} text-purple-400`} />;
        if (lowerTitle.includes("thinking")) return <Loader2 className={`${iconClass} animate-spin text-neutral-400`} />;
        if (lowerTitle.includes("reflection")) return <Brain className={`${iconClass} text-yellow-400`} />;
        if (lowerTitle.includes("research")) return <Globe className={`${iconClass} text-blue-400`} />;
        if (lowerTitle.includes("finalizing")) return <Pen className={`${iconClass} text-green-400`} />;
        
        return <CheckCircle2 className={`${iconClass} text-neutral-400`} />;
    };

    return (
        <div className="relative flex gap-3 group animate-in fade-in slide-in-from-left-2 duration-300 fill-mode-both" style={{ animationDelay: `${index * 50}ms` }}>
            <div className={`relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-800 ring-2 ring-neutral-700 group-hover:ring-neutral-600 transition-all`}>
                {getEventIcon(event.title)}
            </div>
            <div className="flex flex-col flex-1 gap-1 pb-4">
                <div 
                    className={cn(
                        "flex items-center gap-2 py-1 cursor-pointer select-none",
                        hasData ? "hover:text-neutral-200 text-neutral-300" : "text-neutral-400 cursor-default"
                    )}
                    onClick={() => hasData && setIsItemExpanded(!isItemExpanded)}
                >
                    <span className="text-sm font-medium leading-none">
                        {event.title}
                    </span>
                    {hasData && (
                        isItemExpanded ? <ChevronDown className="h-3 w-3 text-neutral-500" /> : <ChevronRight className="h-3 w-3 text-neutral-500" />
                    )}
                </div>
                
                {hasData && isItemExpanded && (
                    <div className="text-xs text-neutral-400 bg-neutral-900/50 rounded-md p-3 mt-1 border border-neutral-700/50 animate-in slide-in-from-top-1 duration-200">
                        {typeof event.data === "string" ? (
                            <ReactMarkdown components={timelineMdComponents}>
                                {event.data}
                            </ReactMarkdown>
                        ) : Array.isArray(event.data) ? (
                            <ul className="space-y-2">
                                {(event.data as any[]).map((item, i) => (
                                    <li key={i} className="flex flex-col gap-1">
                                        {typeof item === 'object' && item.label ? (
                                            <div className="flex flex-col">
                                                <a href={item.value} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 font-medium hover:underline flex items-center gap-1 w-fit">
                                                    <Globe className="h-3 w-3" />
                                                    {item.label}
                                                </a>
                                                <span className="text-neutral-500 truncate text-[10px]">{item.value}</span>
                                            </div>
                                        ) : (
                                            <ReactMarkdown components={timelineMdComponents}>
                                                {typeof item === 'string' ? item : JSON.stringify(item)}
                                            </ReactMarkdown>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        ) : (
                           <ReactMarkdown components={timelineMdComponents}>
                               {JSON.stringify(event.data, null, 2)}
                           </ReactMarkdown>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export function ActivityTimeline({
  processedEvents,
  isLoading,
}: ActivityTimelineProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  // Automatically expand if loading starts or new events come in initially
  useEffect(() => {
    // Keep it collapsed by default, user can expand to see details
  }, [isLoading, processedEvents]);

  const currentStatus = isLoading
    ? processedEvents.length > 0
      ? processedEvents[processedEvents.length - 1].title
      : "Thinking..."
    : "Research Completed";

  return (
    <Card className="border-none bg-neutral-800/50 rounded-xl overflow-hidden shadow-sm transition-all duration-300 w-full">
      <CardHeader className="p-0">
        <div
          className="flex items-center justify-between p-3 cursor-pointer hover:bg-neutral-700/50 transition-colors"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-center gap-3">
             <div className="flex items-center justify-center h-8 w-8 rounded-full bg-neutral-700/50">
                {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                ) : (
                    <CheckCircle2 className="h-4 w-4 text-green-400" />
                )}
             </div>
             <div className="flex flex-col">
                <span className="text-sm font-medium text-neutral-200">
                    {currentStatus}
                </span>
                <span className="text-xs text-neutral-400">
                    {processedEvents.length} steps processed
                </span>
             </div>
          </div>
          <div>
            {isExpanded ? (
                <ChevronUp className="h-4 w-4 text-neutral-400" />
            ) : (
                <ChevronDown className="h-4 w-4 text-neutral-400" />
            )}
          </div>
        </div>
      </CardHeader>
      
      {isExpanded && (
        <div className="animate-in slide-in-from-top-2 fade-in duration-300">
            <CardContent className="p-0">
                <div className="px-4 pb-2 pt-2 relative">
                    {/* Vertical Line */}
                    <div className="absolute left-[27px] top-2 bottom-6 w-0.5 bg-neutral-700/50" />

                    {processedEvents.map((event, index) => (
                        <TimelineItem 
                            key={index} 
                            event={event} 
                            index={index} 
                            isLast={index === processedEvents.length - 1} 
                            isLoading={isLoading} 
                        />
                    ))}
                </div>
            </CardContent>
        </div>
      )}
    </Card>
  );
}
