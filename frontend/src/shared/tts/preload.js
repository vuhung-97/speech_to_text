// Old servers answered 404/405 before the preload endpoint existed. That is not
// a user-facing failure: the voice still warms up on the first real read.

const UNSUPPORTED_STATUS = new Set([404, 405]);

export function isPreloadUnsupported(error) {
  return UNSUPPORTED_STATUS.has(error?.status);
}
