import { cn } from "@/lib/utils";

/**
 * The mark is the supplied asset at /logo.svg — nothing is drawn in code, so
 * replacing the file is all it takes to rebrand.
 */
export function Logo({ className, size = 28 }: { className?: string; size?: number }) {
  return (
    <img
      src="/logo.svg"
      width={size}
      height={size}
      alt=""
      aria-hidden
      className={cn("shrink-0", className)}
    />
  );
}

export function Wordmark({
  className,
  size = 28,
  showText = true,
}: {
  className?: string;
  size?: number;
  showText?: boolean;
}) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <Logo size={size} />
      {showText ? (
        <span className="text-[15px] font-semibold tracking-tight">AskYourWallet</span>
      ) : null}
    </span>
  );
}
