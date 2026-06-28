import { SettingsSidebar } from "@/components/settings/sidebar"
import { TopBar } from "@/components/layout/top-bar"

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex h-screen w-full flex-col">
      <TopBar title="System Settings" />
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-64 border-r border-border/10 bg-black/40">
          <SettingsSidebar />
        </aside>
        <main className="flex-1 overflow-auto bg-black">
          <div className="container mx-auto p-6 md:p-8 max-w-5xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
