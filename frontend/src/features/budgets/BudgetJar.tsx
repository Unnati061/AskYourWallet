import { useId } from "react";

import { cn } from "@/lib/utils";

export type JarSize = "sm" | "md" | "lg";

const DIMENSIONS: Record<JarSize, { width: number; height: number }> = {
  sm: { width: 40, height: 52 },
  md: { width: 56, height: 72 },
  lg: { width: 76, height: 98 },
};

/** Under 80% is fine, 80-100% is a warning, over 100% is critical. */
export function jarTone(percentUsed: number): "positive" | "warning" | "critical" {
  if (percentUsed > 100) return "critical";
  if (percentUsed >= 80) return "warning";
  return "positive";
}

const FILL_CLASS = {
  positive: "fill-positive",
  warning: "fill-warning",
  critical: "fill-critical",
} as const;

/**
 * A budget as a jar that fills up, not a horizontal progress bar.
 *
 * The jar is drawn as SVG so the fill can be clipped to the jar's rounded
 * silhouette; it grows from the bottom on mount. Over 100% the jar is full and
 * turns critical — the overspend is reported in the figure beside it rather than
 * by overflowing the shape.
 */
export function BudgetJar({
  percentUsed,
  size = "md",
  className,
  animate = true,
}: {
  percentUsed: number;
  size?: JarSize;
  className?: string;
  animate?: boolean;
}) {
  const { width, height } = DIMENSIONS[size];
  const tone = jarTone(percentUsed);
  const clamped = Math.max(0, Math.min(100, Number.isFinite(percentUsed) ? percentUsed : 0));

  // Geometry: a lid strip on top, then the body the fill is clipped into.
  const lidHeight = Math.round(height * 0.08);
  const bodyTop = lidHeight + Math.round(height * 0.05);
  const bodyHeight = height - bodyTop - 1;
  const inset = Math.round(width * 0.1);
  const bodyWidth = width - inset * 2;
  const radius = Math.round(width * 0.18);
  const fillHeight = (bodyHeight * clamped) / 100;
  // useId can contain colons; strip them so the id is safe inside url(#...).
  const clipId = `jar-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${Math.round(percentUsed)}% of the budget used`}
      className={cn("shrink-0", className)}
    >
      <defs>
        <clipPath id={clipId}>
          <rect
            x={inset}
            y={bodyTop}
            width={bodyWidth}
            height={bodyHeight}
            rx={radius}
            ry={radius}
          />
        </clipPath>
      </defs>

      {/* Lid */}
      <rect
        x={inset + bodyWidth * 0.22}
        y={1}
        width={bodyWidth * 0.56}
        height={lidHeight}
        rx={2}
        className="fill-border"
      />

      {/* Empty body */}
      <rect
        x={inset}
        y={bodyTop}
        width={bodyWidth}
        height={bodyHeight}
        rx={radius}
        ry={radius}
        className="fill-muted"
      />

      {/* Fill, clipped to the jar silhouette so it keeps the rounded base */}
      <g clipPath={`url(#${clipId})`}>
        <rect
          x={inset}
          y={bodyTop + bodyHeight - fillHeight}
          width={bodyWidth}
          height={fillHeight}
          className={cn(
            FILL_CLASS[tone],
            animate && "origin-bottom animate-jar-fill [transform-box:fill-box]",
          )}
        />
      </g>

      {/* Quarter marks, so the level is readable without the label */}
      {[0.25, 0.5, 0.75].map((mark) => (
        <line
          key={mark}
          x1={inset + bodyWidth * 0.62}
          x2={inset + bodyWidth * 0.86}
          y1={bodyTop + bodyHeight * (1 - mark)}
          y2={bodyTop + bodyHeight * (1 - mark)}
          strokeWidth={1}
          className="stroke-background/60"
        />
      ))}

      {/* Outline last, so it sits above the fill */}
      <rect
        x={inset}
        y={bodyTop}
        width={bodyWidth}
        height={bodyHeight}
        rx={radius}
        ry={radius}
        fill="none"
        strokeWidth={1}
        className="stroke-border"
      />
    </svg>
  );
}
