// A router link that looks exactly like a Button.
// Navigation actions use this so the CTA classes live in one place.

import { Link } from "react-router-dom";

import { buttonClass } from "./Button";

export default function LinkButton({
  to,
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...rest
}) {
  return (
    <Link to={to} className={buttonClass({ variant, size, className })} {...rest}>
      {children}
    </Link>
  );
}
