"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
  Settings, 
  Cpu, 
  ToyBrick, 
  Key, 
  Activity, 
  Palette, 
  LineChart, 
  HardDrive, 
  Info 
} from "lucide-react"

import { cn } from "@/lib/cn"

const SETTINGS_TABS = [
  // { name: "General", href: "/settings/general", icon: Settings },
  // { name: "AI Models", href: "/settings/models", icon: Cpu },
  // { name: "Integrations", href: "/settings/integrations", icon: ToyBrick },
  { name: "Secrets", href: "/settings/secrets", icon: Key },
  // { name: "Runtime", href: "/settings/runtime", icon: Activity },
  // { name: "Appearance", href: "/settings/appearance", icon: Palette },
  // { name: "Observability", href: "/settings/observability", icon: LineChart },
  // { name: "Backups", href: "/settings/backups", icon: HardDrive },
  // { name: "About", href: "/settings/about", icon: Info },
]

export function SettingsSidebar() {
  const pathname = usePathname()

  return (
    <nav className="flex flex-col gap-1 p-4">
      <div className="mb-4 px-2">
        <h2 className="text-lg font-semibold tracking-tight text-white/90">
          System
        </h2>
        <p className="text-xs text-white/50">Khonshu Cognitive OS</p>
      </div>

      {SETTINGS_TABS.map((tab) => {
        const isActive = pathname?.startsWith(tab.href)
        const Icon = tab.icon

        return (
          <Link
            key={tab.name}
            href={tab.href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-white/10 text-white"
                : "text-white/60 hover:bg-white/5 hover:text-white"
            )}
          >
            <Icon className="h-4 w-4" />
            {tab.name}
          </Link>
        )
      })}
    </nav>
  )
}
