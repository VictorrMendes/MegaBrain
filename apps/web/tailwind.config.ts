import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/context/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Legacy compat
        background: "var(--background)",
        foreground: "var(--foreground)",

        // Surfaces
        surface: {
          base:    "var(--surface-base)",
          raised:  "var(--surface-raised)",
          overlay: "var(--surface-overlay)",
          subtle:  "var(--surface-subtle)",
          inset:   "var(--surface-inset)",
        },

        // Borders
        "border-subtle":  "var(--border-subtle)",
        "border-default": "var(--border-default)",
        "border-strong":  "var(--border-strong)",
        "border-accent":  "var(--border-accent)",

        // Accent
        accent: {
          DEFAULT: "var(--accent)",
          hover:   "var(--accent-hover)",
          dim:     "var(--accent-dim)",
          subtle:  "var(--accent-subtle)",
          fg:      "var(--accent-fg)",
        },

        // Content
        content: {
          primary:     "var(--text-primary)",
          secondary:   "var(--text-secondary)",
          muted:       "var(--text-muted)",
          placeholder: "var(--text-placeholder)",
        },

        // Status
        "status-success": "var(--status-success)",
        "status-warning": "var(--status-warning)",
        "status-error":   "var(--status-error)",
        "status-info":    "var(--status-info)",
        "status-active":  "var(--status-active)",
      },

      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },

      transitionDuration: {
        fast: "100ms",
        base: "180ms",
        slow: "280ms",
      },

      fontSize: {
        "2xs": ["10px", { lineHeight: "1.4" }],
        xs:    ["11px", { lineHeight: "1.5" }],
        sm:    ["12px", { lineHeight: "1.5" }],
        base:  ["13px", { lineHeight: "1.6" }],
        md:    ["14px", { lineHeight: "1.5" }],
        lg:    ["16px", { lineHeight: "1.5" }],
        xl:    ["20px", { lineHeight: "1.3" }],
        "2xl": ["24px", { lineHeight: "1.2" }],
        "3xl": ["30px", { lineHeight: "1.1" }],
      },

      animation: {
        "fade-in":   "fade-in 280ms ease both",
        "shimmer":   "shimmer 1.6s infinite linear",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
        "spin-slow": "spin 1.2s linear infinite",
      },

      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          from: { backgroundPosition: "-400px 0" },
          to:   { backgroundPosition: "400px 0" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%":       { opacity: "0.35" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
