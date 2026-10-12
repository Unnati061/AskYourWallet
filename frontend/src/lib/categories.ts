import {
  ArrowLeftRight,
  Car,
  CircleDot,
  Film,
  Gift,
  GraduationCap,
  HeartPulse,
  Home,
  Plane,
  Repeat,
  Scissors,
  Shield,
  ShoppingBag,
  ShoppingCart,
  Utensils,
  Wallet,
  Zap,
  type LucideIcon,
} from "lucide-react";

/**
 * The backend owns the canonical category list and hands the frontend a Lucide
 * icon name per category (GET /api/categories). This maps those kebab-case
 * names to components explicitly, so only the icons actually used get bundled
 * and an unknown name degrades to a neutral dot rather than crashing.
 *
 * Every icon is a literal object — no robot, sparkle or "AI" glyphs anywhere.
 */
const ICONS_BY_NAME: Record<string, LucideIcon> = {
  "shopping-cart": ShoppingCart,
  utensils: Utensils,
  car: Car,
  home: Home,
  zap: Zap,
  film: Film,
  "shopping-bag": ShoppingBag,
  "heart-pulse": HeartPulse,
  "graduation-cap": GraduationCap,
  plane: Plane,
  repeat: Repeat,
  shield: Shield,
  scissors: Scissors,
  gift: Gift,
  wallet: Wallet,
  "arrow-left-right": ArrowLeftRight,
  "circle-dot": CircleDot,
};

/** Fallback map for when a category name arrives without its icon name. */
const ICONS_BY_CATEGORY: Record<string, string> = {
  Groceries: "shopping-cart",
  Dining: "utensils",
  Transport: "car",
  Housing: "home",
  Utilities: "zap",
  Entertainment: "film",
  Shopping: "shopping-bag",
  Healthcare: "heart-pulse",
  Education: "graduation-cap",
  Travel: "plane",
  Subscriptions: "repeat",
  Insurance: "shield",
  "Personal Care": "scissors",
  "Gifts & Donations": "gift",
  Income: "wallet",
  Transfer: "arrow-left-right",
  Other: "circle-dot",
};

export function iconFor(category: string | null | undefined, iconName?: string): LucideIcon {
  const key = iconName ?? (category ? ICONS_BY_CATEGORY[category] : undefined);
  return (key && ICONS_BY_NAME[key]) || CircleDot;
}

/**
 * Chart series colours, read from the CSS variables so they follow the theme.
 * Recharts accepts any CSS colour string, including var().
 */
export const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--chart-6))",
  "hsl(var(--chart-7))",
  "hsl(var(--chart-8))",
];

export function chartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}
