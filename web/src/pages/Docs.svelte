<script>
  import { marked } from "marked";

  let { slug = "" } = $props();

  // all markdown files from /docs/<lang>/NN-name.md, bundled at build time
  const files = import.meta.glob("../../../docs/*/*.md", { query: "?raw", import: "default", eager: true });
  const PROD_URL = "https://poker.example.com";

  const pages = { en: [], de: [] };
  for (const [path, text] of Object.entries(files)) {
    const m = path.match(/docs\/(\w+)\/(\d+)-([\w-]+)\.md$/);
    if (!m || !pages[m[1]]) continue;
    const title = text.match(/^#\s+(.+)$/m)?.[1] ?? m[3];
    pages[m[1]].push({ order: +m[2], slug: m[3], title, text });
  }
  for (const list of Object.values(pages)) list.sort((a, b) => a.order - b.order);

  const slugify = (s) =>
    s
      .replace(/<[^>]+>/g, "")
      .toLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, "-")
      .replace(/^-|-$/g, "");

  marked.use({
    renderer: {
      heading({ tokens, depth }) {
        const text = this.parser.parseInline(tokens);
        return `<h${depth} id="${slugify(text)}">${text}</h${depth}>\n`;
      },
      link({ href, title, tokens }) {
        const text = this.parser.parseInline(tokens);
        const external = /^https?:\/\//.test(href) && !href.startsWith(location.origin);
        return `<a href="${href}"${title ? ` title="${title}"` : ""}${external ? ' target="_blank" rel="noopener"' : ""}>${text}</a>`;
      },
    },
  });

  const stored = (() => {
    try {
      return localStorage.getItem("docs-lang");
    } catch {
      return null;
    }
  })();
  let lang = $state(stored ?? (navigator.language?.startsWith("de") ? "de" : "en"));
  $effect(() => {
    try {
      localStorage.setItem("docs-lang", lang);
    } catch {}
  });

  const list = $derived(pages[lang]);
  const page = $derived(list.find((p) => p.slug === slug) ?? list[0]);
  const index = $derived(list.indexOf(page));
  const origin = location.origin;
  const html = $derived(page ? marked.parse(page.text.replaceAll(PROD_URL, origin)) : "");
  const outline = $derived(
    page ? [...page.text.matchAll(/^##\s+(.+)$/gm)].map((m) => ({ text: m[1].replace(/`/g, ""), id: slugify(marked.parseInline(m[1])) })) : [],
  );

  let content = $state();
  $effect(() => {
    html;
    if (!content) return;
    for (const pre of content.querySelectorAll("pre")) {
      if (pre.querySelector(".copy")) continue;
      const btn = document.createElement("button");
      btn.className = "copy";
      btn.textContent = lang === "de" ? "Kopieren" : "Copy";
      btn.onclick = async () => {
        try {
          await navigator.clipboard.writeText(pre.querySelector("code")?.innerText ?? pre.innerText);
          btn.textContent = "✓";
        } catch {
          btn.textContent = "✗";
        }
        setTimeout(() => (btn.textContent = lang === "de" ? "Kopieren" : "Copy"), 1500);
      };
      pre.appendChild(btn);
    }
  });

  const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
</script>

<div class="docs">
  <aside class="side">
    <div class="lang" role="group" aria-label="Language">
      <button class:on={lang === "en"} onclick={() => (lang = "en")}>English</button>
      <button class:on={lang === "de"} onclick={() => (lang = "de")}>Deutsch</button>
    </div>
    <nav>
      {#each list as p (p.slug)}
        <a href="#/docs/{p.slug}" class:active={p === page}>{p.title}</a>
      {/each}
      <a href="/docs" target="_blank" rel="noopener">Swagger UI ↗</a>
      <a href="/openapi.yaml" target="_blank" rel="noopener">openapi.yaml ↗</a>
    </nav>
  </aside>

  <article class="md" bind:this={content}>
    {@html html}
    <div class="pager">
      {#if index > 0}<a class="btn" href="#/docs/{list[index - 1].slug}">← {list[index - 1].title}</a>{:else}<span></span>{/if}
      {#if index < list.length - 1}<a class="btn" href="#/docs/{list[index + 1].slug}">{list[index + 1].title} →</a>{/if}
    </div>
  </article>

  {#if outline.length > 2}
    <aside class="outline">
      <div class="muted label">{lang === "de" ? "Auf dieser Seite" : "On this page"}</div>
      {#each outline as h (h.id)}
        <button class="link" onclick={() => scrollTo(h.id)}>{h.text}</button>
      {/each}
    </aside>
  {/if}
</div>

<style>
  .docs { display: grid; grid-template-columns: 220px minmax(0, 1fr) 200px; gap: 2rem; align-items: start; }
  .side, .outline { position: sticky; top: 4.4rem; }
  .lang { display: flex; margin-bottom: 1rem; }
  .lang button { flex: 1; border-radius: 0; font-size: 0.85rem; }
  .lang button:first-child { border-radius: 8px 0 0 8px; }
  .lang button:last-child { border-radius: 0 8px 8px 0; border-left: 0; }
  .lang button.on { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); font-weight: 700; }
  nav { display: flex; flex-direction: column; gap: 0.1rem; }
  nav a { color: var(--muted); padding: 0.35rem 0.6rem; border-radius: 6px; font-size: 0.92rem; }
  nav a:hover { color: var(--text); background: var(--surface-2); text-decoration: none; }
  nav a.active { color: var(--text); background: var(--surface-2); font-weight: 700; border-left: 3px solid var(--accent); }
  .outline { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.85rem; }
  .outline .label { text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.06em; margin-bottom: 0.3rem; }
  .link { background: none; border: 0; padding: 0.15rem 0; text-align: left; color: var(--muted); }
  .link:hover { color: var(--link); }
  .pager { display: flex; justify-content: space-between; gap: 1rem; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); flex-wrap: wrap; }

  .md { max-width: 52rem; min-width: 0; }
  .md :global(h1) { font-size: 2rem; }
  .md :global(h2) { font-size: 1.35rem; margin-top: 2.2em; padding-top: 0.6em; border-top: 1px solid var(--border); scroll-margin-top: 4.5rem; }
  .md :global(h3) { font-size: 1.08rem; margin-top: 1.6em; scroll-margin-top: 4.5rem; }
  .md :global(p), .md :global(li) { line-height: 1.7; }
  .md :global(code) { background: var(--surface-2); padding: 0.1em 0.35em; border-radius: 4px; border: 1px solid var(--border); }
  .md :global(pre) { position: relative; background: var(--code-bg); border: 1px solid var(--border); border-radius: 10px; padding: 0.9rem 1rem; overflow-x: auto; line-height: 1.5; }
  .md :global(pre code) { background: none; border: 0; padding: 0; font-size: 0.86rem; }
  .md :global(.copy) { position: absolute; top: 0.4rem; right: 0.4rem; font-size: 0.75rem; padding: 0.15rem 0.5rem; opacity: 0.7; }
  .md :global(.copy:hover) { opacity: 1; }
  .md :global(table) { border-collapse: collapse; width: 100%; font-size: 0.92rem; display: block; overflow-x: auto; }
  .md :global(th), .md :global(td) { border: 1px solid var(--border); padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }
  .md :global(th) { background: var(--surface-2); }
  .md :global(blockquote) { margin: 1rem 0; padding: 0.6rem 1rem; border-left: 4px solid var(--accent); background: var(--surface); border-radius: 0 8px 8px 0; }
  .md :global(blockquote p) { margin: 0.3rem 0; }
  .md :global(details) { margin: 1rem 0; border: 1px solid var(--border); border-radius: 10px; background: var(--surface); }
  .md :global(details > summary) { cursor: pointer; padding: 0.7rem 1rem; font-weight: 700; list-style: none; display: flex; gap: 0.5rem; align-items: center; }
  .md :global(details > summary::-webkit-details-marker) { display: none; }
  .md :global(details > summary::before) { content: "▸"; display: inline-block; color: var(--accent); transition: transform 0.2s; }
  .md :global(details[open] > summary::before) { transform: rotate(90deg); }
  .md :global(details[open] > summary) { border-bottom: 1px solid var(--border); }
  .md :global(details > :not(summary)) { margin-inline: 1rem; }
  .md :global(details > :last-child) { margin-bottom: 1rem; }
  .md :global(hr) { border: 0; border-top: 1px solid var(--border); margin: 2rem 0; }
  .md :global(img) { max-width: 100%; }

  @media (max-width: 1100px) {
    .docs { grid-template-columns: 200px minmax(0, 1fr); }
    .outline { display: none; }
  }
  @media (max-width: 760px) {
    .docs { grid-template-columns: minmax(0, 1fr); gap: 1rem; }
    .side { position: static; }
    nav { flex-direction: row; flex-wrap: wrap; }
  }
</style>
