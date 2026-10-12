import { MessageSquareText } from "lucide-react";
import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";

/**
 * Deep-links a pre-scoped question into the chat page, so the assistant is
 * reachable from the data it would answer about rather than only from the nav.
 * The chat page reads ?q= and sends it as the first message.
 */
export function AskAboutThis({
  question,
  label = "Ask about this",
  className,
}: {
  question: string;
  label?: string;
  className?: string;
}) {
  return (
    <Link
      to={`/chat?q=${encodeURIComponent(question)}`}
      title={question}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
        className,
      )}
    >
      <MessageSquareText className="size-3.5" aria-hidden />
      {label}
    </Link>
  );
}
