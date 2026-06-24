async function getHealth() {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100"}/health`,
      { cache: "no-store" }
    );
    return res.ok ? res.json() : null;
  } catch {
    return null;
  }
}

export default async function Home() {
  const health = await getHealth();

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">PAIOS</h1>
        <p className="text-sm text-neutral-400 mt-2">Personal AI Operating System</p>
      </div>

      <div className="border border-neutral-800 rounded-lg p-6 w-full max-w-sm">
        <p className="text-xs text-neutral-500 uppercase tracking-widest mb-4">Status</p>
        {health ? (
          <ul className="space-y-2 text-sm">
            {Object.entries(health.services as Record<string, string>).map(([svc, status]) => (
              <li key={svc} className="flex justify-between">
                <span className="text-neutral-400">{svc}</span>
                <span className={status === "ok" ? "text-green-400" : "text-red-400"}>
                  {status}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-red-400">API indisponível</p>
        )}
      </div>
    </main>
  );
}
