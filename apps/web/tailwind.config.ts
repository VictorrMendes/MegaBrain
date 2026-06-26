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
      // ── Colors ─────────────────────────────────────────────────
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",

        surface: {
          base:    "var(--surface-base)",
          raised:  "var(--surface-raised)",
          overlay: "var(--surface-overlay)",
          subtle:  "var(--surface-subtle)",
          inset:   "var(--surface-inset)",
        },

        "border-subtle":  "var(--border-subtle)",
        "border-default": "var(--border-default)",
        "border-strong":  "var(--border-strong)",
        "border-accent":  "var(--border-accent)",

        accent: {
          DEFAULT: "var(--accent)",
          hover:   "var(--accent-hover)",
          dim:     "var(--accent-dim)",
          subtle:  "var(--accent-subtle)",
          fg:      "var(--accent-fg)",
        },

        content: {
          primary:     "var(--text-primary)",
          secondary:   "var(--text-secondary)",
          muted:       "var(--text-muted)",
          placeholder: "var(--text-placeholder)",
        },

        "status-success": "var(--status-success)",
        "status-warning": "var(--status-warning)",
        "status-error":   "var(--status-error)",
        "status-info":    "var(--status-info)",
        "status-active":  "var(--status-active)",

        "status-success-dim": "var(--status-success-dim)",
        "status-warning-dim": "var(--status-warning-dim)",
        "status-error-dim":   "var(--status-error-dim)",
        "status-info-dim":    "var(--status-info-dim)",
        "status-active-dim":  "var(--status-active-dim)",
      },

      // ── Border Radius ────────────────────────────────────────────
      borderRadius: {
        xs:   "var(--radius-xs)",
        sm:   "var(--radius-sm)",
        md:   "var(--radius-md)",
        lg:   "var(--radius-lg)",
        xl:   "var(--radius-xl)",
        "2xl":"var(--radius-2xl)",
      },

      // ── Shadows ──────────────────────────────────────────────────
      boxShadow: {
        xs:       "var(--shadow-xs)",
        sm:       "var(--shadow-sm)",
        md:       "var(--shadow-md)",
        lg:       "var(--shadow-lg)",
        xl:       "var(--shadow-xl)",
        glow:     "var(--shadow-glow)",
        "glow-sm":"var(--shadow-glow-sm)",
      },

      // ── Font Size ────────────────────────────────────────────────
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
        "4xl": ["36px", { lineHeight: "1.05" }],
      },

      // ── Font Family ───────────────────────────────────────────────
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "-apple-system", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },

      // ── Font Weight ───────────────────────────────────────────────
      fontWeight: {
        regular:  "400",
        medium:   "500",
        semibold: "600",
        bold:     "700",
      },

      // ── Transition Duration ──────────────────────────────────────
      transitionDuration: {
        instant: "80ms",
        fast:    "120ms",
        normal:  "200ms",
        slow:    "320ms",
      },

      // ── Transition Timing ─────────────────────────────────────────
      transitionTimingFunction: {
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
        smooth: "cubic-bezier(0.4, 0, 0.2, 1)",
        bounce: "cubic-bezier(0.68, -0.55, 0.265, 1.55)",
      },

      // ── Z-index ───────────────────────────────────────────────────
      zIndex: {
        base:         "0",
        raised:       "10",
        sticky:       "100",
        topbar:       "200",
        statusbar:    "200",
        dropdown:     "300",
        overlay:      "400",
        modal:        "500",
        notification: "600",
        dock:         "700",
        tooltip:      "800",
      },

      // ── Spacing extras ────────────────────────────────────────────
      spacing: {
        "topbar":    "40px",
        "statusbar": "24px",
        "sidebar":   "220px",
      },

      // ── Animations ───────────────────────────────────────────────
      animation: {
        "fade-in":          "fade-in 320ms ease both",
        "fade-out":         "fade-out 200ms ease both",
        "slide-up":         "slide-up 320ms ease both",
        "slide-down":       "slide-down 200ms ease both",
        "slide-in-right":   "slide-in-right 320ms ease both",
        "slide-in-left":    "slide-in-left 320ms ease both",
        "scale-in":         "scale-in 200ms ease both",
        "scale-in-spring":  "scale-in-spring 320ms cubic-bezier(0.34,1.56,0.64,1) both",
        "shimmer":          "shimmer 1.6s infinite linear",
        "pulse-dot":        "pulse-dot 2s ease-in-out infinite",
        "glow-pulse":       "glow-pulse 2.5s ease-in-out infinite",
        "spin-fast":        "spin 0.7s linear infinite",
        "spin-slow":        "spin 1.4s linear infinite",
        "blink":            "blink 1.2s step-end infinite",
        "notification":     "notification-enter 320ms cubic-bezier(0.34,1.56,0.64,1) both",
      },

      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "fade-out": {
          from: { opacity: "1", transform: "translateY(0)" },
          to:   { opacity: "0", transform: "translateY(4px)" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "slide-down": {
          from: { opacity: "0", transform: "translateY(-8px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in-right": {
          from: { opacity: "0", transform: "translateX(16px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
        "slide-in-left": {
          from: { opacity: "0", transform: "translateX(-16px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.94)" },
          to:   { opacity: "1", transform: "scale(1)" },
        },
        "scale-in-spring": {
          "0%":   { opacity: "0", transform: "scale(0.88)" },
          "60%":  { opacity: "1", transform: "scale(1.02)" },
          "100%": { transform: "scale(1)" },
        },
        shimmer: {
          from: { backgroundPosition: "-400px 0" },
          to:   { backgroundPosition: "400px 0" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%":      { opacity: "0.35" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 8px rgba(99,102,241,0.2)" },
          "50%":      { boxShadow: "0 0 20px rgba(99,102,241,0.45)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%":      { opacity: "0" },
        },
        "notification-enter": {
          from: { opacity: "0", transform: "translateX(100%) scale(0.95)" },
          to:   { opacity: "1", transform: "translateX(0) scale(1)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
