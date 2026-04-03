import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("font-semibold tracking-tight", className)}>
      Perception<sup className="text-[0.6em] ml-0.5 align-super">AI</sup>
    </span>
  );
}
