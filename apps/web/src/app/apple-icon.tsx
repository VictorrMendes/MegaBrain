import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#08080c",
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "38px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 108,
            height: 108,
            background: "rgba(99,102,241,0.14)",
            borderRadius: "24px",
          }}
        >
          <span
            style={{
              color: "#6366f1",
              fontSize: 72,
              fontWeight: 800,
              letterSpacing: "-2px",
            }}
          >
            K
          </span>
        </div>
      </div>
    ),
    { ...size },
  );
}
