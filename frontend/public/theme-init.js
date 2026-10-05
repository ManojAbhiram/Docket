// Sets data-theme on <html> before the first paint, so a dark user never sees a light flash.
// It is a file, not an inline script: the Content-Security-Policy allows scripts from 'self' only.
// The choice is "light", "dark" or nothing (follow the system), stored by the theme toggle.
(function () {
  var stored = null;
  try {
    stored = localStorage.getItem("docket-theme");
  } catch (error) {
    stored = null;
  }
  var dark =
    stored === "dark" ||
    ((stored === null || stored === "system") &&
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
})();
