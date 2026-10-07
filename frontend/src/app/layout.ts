const COMPARE_PATH = /^\/applications\/[^/]+\/?$/;

/** The compare screen holds a five-column table beside the page image, so it gets the wide column. */
export function mainWidthClass(pathname: string): string {
  return COMPARE_PATH.test(pathname) ? "max-w-7xl" : "max-w-5xl";
}
