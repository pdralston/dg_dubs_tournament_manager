/**
 * PostCSS plugin: scope each app's CSS under its `[data-app="<app>"]` host.
 *
 * The unified SPA mounts DG-Dubs / DG-Tags / DG-Putt in one DOM. Their ported
 * stylesheets were independent apps and freely reuse the same class names
 * (`.App`, `.App-header`, `.table-container`, `.modal-buttons`, …) and the same
 * `:root` CSS-variable names (`--accent`, `--color-page-bg`, …) with DIFFERENT
 * values. Left global, whichever loads last wins and the apps' styles collide.
 *
 * This plugin runs only on files under `src/apps/<app>/` and rewrites every
 * top-level rule so it only applies within that app's host subtree:
 *
 *   .App-header { … }      ->  [data-app="putt"] .App-header { … }
 *   :root { --accent: … }  ->  [data-app="putt"] { --accent: … }
 *   body { … }             ->  [data-app="putt"] { … }
 *   @media (...) { .x {} }  ->  @media (...) { [data-app="putt"] .x {} }
 *
 * Left untouched (must stay global / can't be nested under a selector):
 *   @import, @charset, @keyframes (and the frames inside), @font-face.
 *
 * The AppHost renders each app inside `<div class="dgr-app-host"
 * data-app="<app>">`, so the scope wraps the whole app subtree and its scoped
 * `:root` variables resolve for all descendants.
 */

const APP_RE = /[\\/]src[\\/]apps[\\/](dubs|tags|putt)[\\/]/;

// At-rules whose direct children are style rules that SHOULD be scoped.
const NESTED_RULE_ATRULES = new Set(['media', 'supports', 'container', 'layer']);
// At-rules to leave entirely alone.
const SKIP_ATRULES = new Set(['keyframes', '-webkit-keyframes', 'font-face', 'import', 'charset']);

function scopeSelector(selector, scope) {
  return selector
    .split(',')
    .map((s) => {
      const sel = s.trim();
      if (!sel) return sel;
      // :root / html / body apply to the app's host element itself.
      if (sel === ':root' || sel === 'html' || sel === 'body') return scope;
      // Already scoped (e.g. the shell-integration overrides we hand-wrote).
      if (sel.includes('[data-app=')) return sel;
      return `${scope} ${sel}`;
    })
    .join(', ');
}

export default function scopeAppCss() {
  return {
    postcssPlugin: 'scope-app-css',
    Once(root, { result }) {
      const file = result.opts.from || '';
      const m = file.match(APP_RE);
      if (!m) return;
      const scope = `[data-app="${m[1]}"]`;

      root.each((node) => {
        if (node.type === 'rule') {
          node.selector = scopeSelector(node.selector, scope);
        } else if (node.type === 'atrule' && NESTED_RULE_ATRULES.has(node.name.toLowerCase())) {
          node.each((child) => {
            if (child.type === 'rule') {
              child.selector = scopeSelector(child.selector, scope);
            }
          });
        }
        // SKIP_ATRULES and anything else: leave as-is.
      });
    },
  };
}
scopeAppCss.postcss = true;
