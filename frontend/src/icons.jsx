import React from "react";

const PATHS = {
  menu: "M3 6h18M3 12h18M3 18h18",
  chevronLeft: "M15 6l-6 6 6 6",
  chevronRight: "M9 6l6 6-6 6",
  chevronDown: "M6 9l6 6 6-6",
  plus: "M12 5v14M5 12h14",
  minus: "M5 12h14",
  search: "M10.5 4a6.5 6.5 0 104.6 11.1L20 20M17 10.5a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z",
  close: "M6 6l12 12M18 6L6 18",
  check: "M4.5 12.5l5 5L20 7",
  settings:
    "M12 15.5a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM19 12c0-.6 0-1.1-.1-1.6l2-1.5-2-3.5-2.4.9a7.6 7.6 0 00-2.8-1.6L13.4 2h-4l-.4 2.7a7.6 7.6 0 00-2.8 1.6L3.8 5.4l-2 3.5 2 1.5a9 9 0 000 3.2l-2 1.5 2 3.5 2.4-.9a7.6 7.6 0 002.8 1.6L9.4 22h4l.4-2.7a7.6 7.6 0 002.8-1.6l2.4.9 2-3.5-2-1.5c.1-.5.1-1 .1-1.6z",
  sparkles:
    "M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9L12 3zM18.5 15l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9.9-2.1zM5 15l.7 1.6L7.3 17.3l-1.6.7L5 19.6l-.7-1.6L2.7 17.3l1.6-.7L5 15z",
  calendar:
    "M7 2v3M17 2v3M3.5 8.5h17M4 5.5h16a1.5 1.5 0 011.5 1.5v13A1.5 1.5 0 0120 21.5H4A1.5 1.5 0 012.5 20V7A1.5 1.5 0 014 5.5z",
  clock: "M12 7v5l3.5 2M12 21a9 9 0 100-18 9 9 0 000 18z",
  trash: "M4 7h16M9 7V4h6v3M6.5 7l1 13h9l1-13M10 11v6M14 11v6",
  refresh: "M20 12a8 8 0 11-2.34-5.66M20 4v5h-5",
  chart: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  user: "M12 12a4 4 0 100-8 4 4 0 000 8zM4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5",
  book: "M4 5.5A2.5 2.5 0 016.5 3H20v15H6.5A2.5 2.5 0 004 20.5V5.5zM20 18v3H6.5A2.5 2.5 0 014 18.5",
  moon: "M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z",
  zap: "M13 2L4 14h6l-1 8 9-12h-6l1-8z",
  info: "M12 21a9 9 0 100-18 9 9 0 000 18zM12 11v6M12 7.5v.5",
  more: "M12 7a1 1 0 100-2 1 1 0 000 2zM12 13a1 1 0 100-2 1 1 0 000 2zM12 19a1 1 0 100-2 1 1 0 000 2z",
  external: "M14 4h6v6M20 4L10 14M9 4H4v16h16v-5",
  play: "M8 5v14l11-7L8 5z",
};

export default function Icon({ name, size = 22, strokeWidth = 1.8, style, className, fill = "none" }) {
  const d = PATHS[name] || PATHS.info;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill}
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
      className={className}
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
