import * as React from "react";

/**
 * Renders an assistant answer as text.
 *
 * Two jobs, both driven by the brief rather than by markdown support:
 *   1. every figure in an answer is wrapped in `.figure`, so amounts the model
 *      quotes back sit in JetBrains Mono like the rest of the app's numbers;
 *   2. the "- " bullets the system prompt asks for become a real list.
 *
 * Everything is assembled as React nodes — the model's output is never handed to
 * dangerouslySetInnerHTML.
 */

// A money-ish token: 1,240.50 / 97% / 2026-08 stays intact as one unit.
const FIGURE = /(\d[\d,]*(?:\.\d+)?%?|\d{4}-\d{2}(?:-\d{2})?)/g;

// The model likes narrow/non-breaking spaces around amounts, which read as odd
// gaps next to Inter's regular spacing. Flattened to ordinary spaces.
const EXOTIC_SPACE = /[\u00a0\u2007\u2009\u202f]/g;

function withFigures(text: string, keyPrefix: string): React.ReactNode[] {
  return text.split(FIGURE).map((part, index) =>
    index % 2 === 1 ? (
      <span key={`${keyPrefix}-f${index}`} className="figure">
        {part}
      </span>
    ) : (
      <React.Fragment key={`${keyPrefix}-t${index}`}>{part}</React.Fragment>
    ),
  );
}

/** Handles the **bold** the model occasionally emits, then the figures inside. */
function inline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  text.split(/\*\*(.+?)\*\*/g).forEach((part, index) => {
    if (index % 2 === 1) {
      nodes.push(
        <strong key={`${keyPrefix}-b${index}`} className="font-semibold">
          {withFigures(part, `${keyPrefix}-b${index}`)}
        </strong>,
      );
    } else {
      nodes.push(...withFigures(part, `${keyPrefix}-${index}`));
    }
  });
  return nodes;
}

export function AnswerText({ text }: { text: string }) {
  const blocks: React.ReactNode[] = [];
  let bullets: string[] = [];

  const flushBullets = () => {
    if (!bullets.length) return;
    const items = bullets;
    bullets = [];
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="ml-4 list-disc space-y-1">
        {items.map((item, index) => (
          <li key={index}>{inline(item, `li-${blocks.length}-${index}`)}</li>
        ))}
      </ul>,
    );
  };

  for (const rawLine of text.replace(EXOTIC_SPACE, " ").split("\n")) {
    const line = rawLine.trim();
    const bullet = /^[-*•]\s+(.*)$/.exec(line);
    if (bullet) {
      bullets.push(bullet[1]);
      continue;
    }
    flushBullets();
    if (!line) continue;
    blocks.push(
      <p key={`p-${blocks.length}`} className="whitespace-pre-wrap">
        {inline(line, `p-${blocks.length}`)}
      </p>,
    );
  }
  flushBullets();

  return <div className="space-y-2 text-sm leading-relaxed">{blocks}</div>;
}
