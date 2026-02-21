import React from "react";

export function BlinkingDot({ addMargin = false }: { addMargin?: boolean }) {
  return (
    <span
      className={`virtualai-typing-cursor inline-block w-[2px] h-[14px] bg-text-04 rounded-[1px] flex-none align-text-bottom ${
        addMargin ? "ml-2" : ""
      }`}
      aria-hidden="true"
    />
  );
}
