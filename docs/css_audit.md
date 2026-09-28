# Frontend CSS Audit

**Date:** 2026-05-11

---

## 1. Inline Styles to Extract

### Admin.tsx

| Location | Inline Style | Suggested Class |
|----------|-------------|-----------------|
| Archive preview table | `style={{ marginBottom: '15px' }}` | `.mb-15` or `.archive-preview-table` |
| Payout preview table | `style={{ maxWidth: '300px' }}` | `.payout-preview-table` |
| Save/Reset button container | `style={{ display: 'flex', gap: '10px', marginTop: '15px' }}` | `.button-row` |

### Tournaments.tsx

| Location | Inline Style | Suggested Class |
|----------|-------------|-----------------|
| Tie modal `.modal-buttons` div | `style={{ marginTop: '15px' }}` | `.modal-buttons-spaced` or add `margin-top` to existing `.modal-buttons` |

### PlayerDetails.tsx

| Location | Inline Style | Suggested Class |
|----------|-------------|-----------------|
| Tournament modal Close button | `style={{ marginTop: '15px' }}` | `.mt-15` or `.modal-close-button` |

### Clean Files (no inline styles)

- Login.tsx ✓
- AcePotTracker.tsx ✓
- PlayerList.tsx ✓
- App.tsx ✓

---

## 2. App.css Organization Issues

### 2.1 Duplicate Selector: `.ace-pot-summary`

The class `.ace-pot-summary` is defined **twice** with conflicting styles:

- **Line ~280** (Ace Pot section): `display: flex; gap: 20px; margin-bottom: 20px;`
- **Line ~370** (Tournament Creation section): `margin-bottom: 10px; padding: 8px; background-color: #16213e; border-radius: 4px; color: #e94560; font-weight: bold;`

The second definition overrides the first. These serve different purposes and should be separate classes (e.g., `.ace-pot-balance-cards` vs `.ace-pot-buy-in-summary`).

### 2.2 Repeated Color Values — Use CSS Variables

The following colors appear many times and should be extracted to `:root` variables:

| Color | Usage Count | Suggested Variable |
|-------|-------------|-------------------|
| `#e94560` | 40+ | `--color-primary` |
| `#0f0f1a` | 10+ | `--color-bg-dark` |
| `#16213e` | 10+ | `--color-bg-card` |
| `#1a1a2e` | 1 | `--color-bg-body` |
| `#e0e0e0` | 10+ | `--color-text` |
| `#aaa` | 8+ | `--color-text-muted` |
| `#333` | 6+ | `--color-border` |
| `#2a2a3e` | 2 | `--color-border-subtle` |
| `#4caf50` | 3 | `--color-success` |
| `#ff6b6b` / `#ff4444` | 4 | `--color-danger` |
| `#c73652` | 2 | `--color-primary-hover` |
| `#ffd700` | 2 | `--color-gold` |

### 2.3 Repeated Spacing/Font Patterns

These patterns repeat and could be utility classes or variables:

- `font-family: 'Bebas Neue', cursive;` — used on 8+ selectors. Consider a `--font-heading` variable.
- `font-family: 'Roboto', sans-serif;` — could be `--font-body`.
- `border-radius: 4px` and `border-radius: 8px` — consider `--radius-sm` and `--radius-md`.
- `padding: 10px 20px` on buttons — repeated across `.action-button`, `.modal-buttons button`, `.create-tournament-button`.

### 2.4 Section Ordering / Mixed Concerns

The current file mixes component-specific styles with layout utilities. Suggested reorder:

1. **CSS Variables** (`:root`)
2. **Reset / Base** (`.App`, `main`)
3. **Typography** (headings, fonts)
4. **Layout Utilities** (`.page-content`, `.page-header`)
5. **Components — Shared** (`.data-table`, `.form-group`, `.action-button`, `.back-button`, `.modal-buttons`, `.status-badge`)
6. **Components — Specific** (grouped by feature: Auth/Login, Players, Tournaments, Ace Pot, Admin)
7. **Responsive overrides** (single `@media` block at the end)

Currently, responsive rules are split across two `@media` blocks (one general, one for tournament creation). These should be consolidated.

### 2.5 Unused / Potentially Dead CSS

The following classes exist in App.css but are not referenced in any component:

- `.tournament-cards`, `.tournament-card`, `.tournament-card-header` — appear to be from an older card-based layout replaced by the table.
- `.tournament-course`, `.tournament-teams` — not found in any component.
- `.player-selection` — not found in any component.
- `.mode-toggle` — not found in any component.
- `.ghost-toggle` — not found in any component.
- `.create-section` — not found in any component.

### 2.6 Specificity / `!important` Usage

The following use `!important` and could be refactored:

- `.login-button`, `.logout-button` — 4 `!important` declarations. These override `.App-header nav button` styles. A more specific selector or restructured HTML would eliminate the need.
- `.highlight-row` — uses `!important` to override table hover. Could use a more specific selector instead.

---

## 3. Action Items (Priority Order)

1. **Add CSS custom properties** — Extract repeated colors, fonts, and radii into `:root` variables.
2. **Resolve duplicate `.ace-pot-summary`** — Rename one to avoid the conflict.
3. **Extract inline styles** — Create 3–4 utility/component classes to replace the 5 inline style instances.
4. **Remove dead CSS** — Delete the ~6 unused class definitions.
5. **Consolidate `@media` blocks** — Merge the two responsive sections into one.
6. **Eliminate `!important`** — Refactor auth button and highlight-row selectors.
7. **Reorder file sections** — Group by concern (variables → base → shared → feature-specific → responsive).
