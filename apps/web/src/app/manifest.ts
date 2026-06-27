import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Khonshu — Sistema Operacional Cognitivo",
    short_name: "Khonshu",
    description: "Personal AI Operating System — Khonshu Cognitive Core",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#08080c",
    theme_color: "#08080c",
    orientation: "portrait-primary",
    categories: ["productivity", "utilities"],
    icons: [
      {
        src: "/icons/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
      {
        src: "/icons/icon-maskable.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "maskable",
      },
    ],
    shortcuts: [
      {
        name: "Chat",
        short_name: "Chat",
        url: "/chat",
        description: "Abrir o Chat Cognitivo",
      },
      {
        name: "Missões",
        short_name: "Missões",
        url: "/missions",
        description: "Ver missões ativas",
      },
    ],
  };
}
