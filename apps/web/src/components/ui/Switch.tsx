import * as RadixSwitch from "@radix-ui/react-switch";
import { cn } from "@/lib/cn";

interface SwitchProps {
  checked?:        boolean;
  onCheckedChange?:(checked: boolean) => void;
  disabled?:       boolean;
  label?:          string;
  description?:    string;
  className?:      string;
  id?:             string;
}

export function Switch({
  checked,
  onCheckedChange,
  disabled,
  label,
  description,
  className,
  id,
}: SwitchProps) {
  const switchId = id ?? `switch-${Math.random().toString(36).slice(2)}`;

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <RadixSwitch.Root
        id={switchId}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        className={cn(
          "relative h-[20px] w-[36px] cursor-pointer rounded-full",
          "border border-[var(--border-default)]",
          "transition-colors duration-normal",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
          "disabled:cursor-not-allowed disabled:opacity-40",
          checked ? "bg-accent border-accent" : "bg-surface-subtle",
        )}
      >
        <RadixSwitch.Thumb
          className={cn(
            "block h-[14px] w-[14px] rounded-full",
            "bg-white shadow-sm",
            "transition-transform duration-normal ease-spring",
            "translate-x-[2px] data-[state=checked]:translate-x-[18px]",
          )}
        />
      </RadixSwitch.Root>

      {(label || description) && (
        <label htmlFor={switchId} className="cursor-pointer">
          {label && (
            <span className="block text-sm text-content-primary">{label}</span>
          )}
          {description && (
            <span className="block text-xs text-content-muted">{description}</span>
          )}
        </label>
      )}
    </div>
  );
}
