import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
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
          borderRadius: "8px",
        }}
      >
        <span
          style={{
            color: "#6366f1",
            fontSize: 20,
            fontWeight: 800,
            letterSpacing: "-0.5px",
          }}
        >
          K
        </span>
      </div>
    ),
    { ...size },
  );
}
