import { CircleAlert, CornerDownLeft, Eraser, MessageSquareText, ShieldCheck } from "lucide-react";
import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { AnswerText } from "@/features/chat/AnswerText";
import { fetchChatStatus, sendChatMessage } from "@/features/chat/api";
import { ToolTrail } from "@/features/chat/ToolTrail";
import { errorMessage } from "@/lib/api";
import type { ChatHistoryMessage, ChatResponse, ChatStatus, ToolCallRecord } from "@/lib/types";

/** Openers that all four backend tools can actually answer. */
const STARTERS = [
  "What did I spend the most on this month?",
  "Am I over budget anywhere?",
  "How has my spending changed over the last 6 months?",
  "Which merchants did I spend the most at this month?",
];

interface Turn {
  id: number;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCallRecord[];
  /** False on an assistant turn that came back without a database lookup. */
  grounded?: boolean;
}

let nextId = 1;

export function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [turns, setTurns] = React.useState<Turn[]>([]);
  const [draft, setDraft] = React.useState("");
  const [pending, setPending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [suggestions, setSuggestions] = React.useState<string[]>([]);
  const [status, setStatus] = React.useState<ChatStatus | null>(null);

  const endRef = React.useRef<HTMLDivElement>(null);
  // Sending reads the transcript, so it is mirrored into a ref: that lets the
  // send function stay stable enough to call from an effect without re-firing.
  const turnsRef = React.useRef<Turn[]>([]);
  React.useEffect(() => {
    turnsRef.current = turns;
  }, [turns]);

  React.useEffect(() => {
    fetchChatStatus().then(setStatus, () => setStatus(null));
  }, []);

  const send = React.useCallback(async (message: string) => {
    const text = message.trim();
    if (!text) return;

    // Only completed turns are replayed as history; the backend caps it at 8.
    // Read before appending, so the message being sent is not duplicated.
    const history: ChatHistoryMessage[] = turnsRef.current.map((turn) => ({
      role: turn.role,
      content: turn.content,
    }));

    setError(null);
    setSuggestions([]);
    setDraft("");
    setTurns((previous) => [...previous, { id: nextId++, role: "user", content: text }]);
    setPending(true);

    try {
      const answer: ChatResponse = await sendChatMessage(text, history);
      setTurns((previous) => [
        ...previous,
        {
          id: nextId++,
          role: "assistant",
          content: answer.response,
          toolCalls: answer.tool_calls,
          grounded: answer.grounded,
        },
      ]);
      setSuggestions(answer.suggested_actions);
    } catch (caught) {
      setError(errorMessage(caught, "The assistant could not answer that."));
    } finally {
      setPending(false);
    }
  }, []);

  // A question deep-linked from "Ask about this" is sent once, then dropped from
  // the URL so a refresh does not ask it again. The ref is what makes "once"
  // true under StrictMode, which mounts effects twice in development.
  const deepLink = searchParams.get("q");
  const askedRef = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (!deepLink || askedRef.current === deepLink) return;
    askedRef.current = deepLink;
    setSearchParams({}, { replace: true });
    void send(deepLink);
  }, [deepLink, setSearchParams, send]);

  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, pending]);

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends, Shift+Enter breaks the line.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!pending) void send(draft);
    }
  };

  const disabled = pending || (status ? !status.enabled : false);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Chat"
        description="Ask about your own numbers. Every figure is looked up in your ledger before it is quoted."
        actions={
          turns.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setTurns([]);
                setSuggestions([]);
                setError(null);
              }}
            >
              <Eraser />
              New conversation
            </Button>
          ) : null
        }
      />

      {status && !status.enabled ? (
        <div className="flex items-start gap-2.5 rounded-lg border border-warning/30 bg-warning/5 p-3">
          <CircleAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
          <div className="space-y-0.5 text-xs">
            <p className="font-medium">The assistant is not configured</p>
            <p className="text-muted-foreground">{status.detail}</p>
          </div>
        </div>
      ) : null}

      <div className="space-y-3">
        {turns.length === 0 && !pending ? (
          <div className="rounded-lg border border-border bg-card p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Try asking
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Answers come from your transactions, budgets and monthly totals — never from
              guesswork. If there is no data for a period, it will say so.
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {STARTERS.map((question) => (
                <Button
                  key={question}
                  variant="outline"
                  size="sm"
                  className="h-auto whitespace-normal py-1.5 text-left text-[11px]"
                  disabled={disabled}
                  onClick={() => void send(question)}
                >
                  {question}
                </Button>
              ))}
            </div>
          </div>
        ) : null}

        {turns.map((turn) =>
          turn.role === "user" ? (
            <div key={turn.id} className="flex justify-end">
              <p className="max-w-[85%] rounded-lg rounded-br-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
                {turn.content}
              </p>
            </div>
          ) : (
            <div key={turn.id} className="max-w-[92%] rounded-lg border border-border bg-card p-3">
              <div className="mb-1.5 flex items-center gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                  AskYourWallet
                </span>
                {turn.grounded ? (
                  <Badge variant="positive">
                    <ShieldCheck className="size-3" aria-hidden />
                    From your ledger
                  </Badge>
                ) : (
                  <Badge variant="warning">No lookup</Badge>
                )}
              </div>
              <AnswerText text={turn.content} />
              <ToolTrail calls={turn.toolCalls ?? []} />
            </div>
          ),
        )}

        {pending ? (
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2.5">
            <span className="flex gap-1" aria-hidden>
              {[0, 1, 2].map((dot) => (
                <span
                  key={dot}
                  className="size-1.5 animate-pulse rounded-full bg-muted-foreground"
                  style={{ animationDelay: `${dot * 150}ms` }}
                />
              ))}
            </span>
            <p className="text-xs text-muted-foreground" role="status">
              Looking it up in your ledger…
            </p>
          </div>
        ) : null}

        {error ? <ErrorState message={error} /> : null}

        {suggestions.length > 0 && !pending ? (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-muted-foreground">Follow up:</span>
            {suggestions.map((suggestion) => (
              <Button
                key={suggestion}
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-[11px]"
                disabled={disabled}
                onClick={() => void send(suggestion)}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        ) : null}

        <div ref={endRef} />
      </div>

      {/* Solid, not blurred: the brief rules out glassmorphism. */}
      <div className="sticky bottom-0 -mx-4 border-t border-border bg-background px-4 pb-2 pt-3 lg:-mx-6 lg:px-6">
        <div className="flex items-end gap-2">
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            maxLength={2000}
            disabled={status ? !status.enabled : false}
            aria-label="Ask a question about your finances"
            placeholder="How much did I spend on Groceries this month?"
            className="min-h-[52px] resize-none"
          />
          <Button size="sm" className="h-9" disabled={disabled || !draft.trim()} onClick={() => void send(draft)}>
            <MessageSquareText />
            Ask
          </Button>
        </div>
        <p className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground">
          <CornerDownLeft className="size-3" aria-hidden />
          Enter sends · Shift+Enter adds a line
          {status?.enabled ? <span className="ml-1">· model {status.model}</span> : null}
        </p>
      </div>
    </div>
  );
}
