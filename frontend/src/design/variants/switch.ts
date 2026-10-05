/** Dev-only: `?variant=<name>` loads that direction's CSS and sets `data-variant` on the root element. */
export async function applyVariantFromUrl(search: string = window.location.search): Promise<void> {
  const name = new URLSearchParams(search).get("variant");
  if (!name) {
    return;
  }
  const loaders = import.meta.glob("./*.css");
  const load = loaders[`./${name}.css`];
  if (!load) {
    return;
  }
  await load();
  document.documentElement.dataset.variant = name;
}
