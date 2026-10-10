// Minimal hash router: #/path/segments?query
function parse() {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  return { path, parts: path.split("/").filter(Boolean), query: new URLSearchParams(query) };
}

export const route = $state(parse());

window.addEventListener("hashchange", () => {
  Object.assign(route, parse());
  window.scrollTo(0, 0);
});

export function go(path) {
  location.hash = path;
}
