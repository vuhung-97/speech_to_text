// Shared visual rules for text inputs, textareas and selects.
// Callers add their own layout (width/radius/padding) but never repeat the
// border, background, focus ring or disabled state.

export const FIELD_CLASS =
  "min-h-11 border border-line bg-wash-strong text-content outline-none transition sm:min-h-0 " +
  "placeholder:text-faint focus:border-accent/60 " +
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent " +
  "disabled:opacity-50";

// Mobile inputs stay at 14px (avoids iOS zoom); desktop keeps the compact 13px.
export const FIELD_TEXT = "text-[14px] sm:text-[13px]";
