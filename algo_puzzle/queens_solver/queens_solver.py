#!/usr/bin/env python3
"""Queens autosolver (web).

Obiettivo: apri un sito con il gioco "Queens" (griglia NxN divisa in regioni/colori) e fai
clic automaticamente nelle celle che devono contenere le regine.

Regole usate (variante tipo LinkedIn Queens):
- Esattamente 1 regina per riga
- Esattamente 1 regina per colonna
- Esattamente 1 regina per regione/colore
- Nessuna regina può "toccarne" un'altra (adiacente anche in diagonale). Nota: con 1 per riga/colonna,
  l'unico conflitto possibile è la diagonale adiacente (riga +/-1 e colonna +/-1).

REQUISITI:
  pip install playwright
  python -m playwright install chromium

USO:
  python queens_autosolver.py --url https://www.linkedin.com/games/queens/

Flusso consigliato:
  1) Lo script apre Chromium con un profilo persistente (cartella ./pw_profile)
  2) Tu fai login (se serve) e arrivi alla schermata con la griglia
  3) Torni nel terminale e premi INVIO
  4) Lo script legge la griglia, risolve, e clicca le celle per mettere le regine

NOTE IMPORTANTI:
- Funziona se la griglia è composta da elementi HTML cliccabili (button/div). Se il gioco usa canvas puro,
  o DOM molto offuscato, potrebbe non riuscire a rilevare le celle.
- Non contiene trucchi "stealth" o bypass anti-bot. È una semplice automazione.
- Rispetta i Termini di Servizio del sito su cui lo usi.

"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


# -------------------------------
# Config di default (modificabili via CLI)
# -------------------------------
DEFAULT_URL = "https://www.linkedin.com/games/queens/"
PROFILE_DIR = Path(__file__).with_name("pw_profile")


# -------------------------------
# Tipi e strutture dati
# -------------------------------


@dataclass(frozen=True)
class Grid:
    n: int
    cell_id: List[List[int]]              # cell_id[r][c] => data-queens-solver-id
    region: List[List[int]]               # region[r][c] => region index 0..n-1
    region_key_by_idx: Dict[int, str]     # region index -> key (debug)
    state: List[List[str]]                # "empty" | "x" | "queen"


# -------------------------------
# JS helpers (eseguiti nel browser)
# -------------------------------

JS_COLLECT_CANDIDATES = r"""
() => {
  // Selettore ampio: ci pensiamo in Python a filtrare.
  const selector = 'button, [role="button"], [role="gridcell"], [role="cell"], [tabindex]';
  const els = Array.from(document.querySelectorAll(selector));

  function normalizeBg(bg) {
    if (!bg) return '';
    const s = String(bg).trim();
    if (!s) return '';
    if (s === 'transparent') return 'rgba(0, 0, 0, 0)';
    return s;
  }

  function regionKey(el) {
    // Prova a trovare un background non trasparente risalendo l'albero DOM.
    let cur = el;
    for (let i = 0; i < 5 && cur; i++) {
      const cs = window.getComputedStyle(cur);
      const bg = normalizeBg(cs.backgroundColor);
      if (bg && bg !== 'rgba(0, 0, 0, 0)') return bg;
      cur = cur.parentElement;
    }
    return '';
  }

  function cellState(el) {
    const txt = (el.innerText || '');
    const aria = (el.getAttribute('aria-label') || '');
    const cls = (el.className || '');

    // Heuristics: cerca icone/label comuni.
    const qNode = el.querySelector(
      '[aria-label*="queen" i], [aria-label*="regina" i], [data-testid*="queen" i], .queen, [data-queen], img[alt*="queen" i], svg[aria-label*="queen" i]'
    );
    if (qNode || /queen|regina|reina|dama|\uD83D\uDC51|\u265B/i.test(txt + ' ' + aria + ' ' + cls)) {
      return 'queen';
    }

    const xNode = el.querySelector(
      '[aria-label="X"], [aria-label*="cross" i], [data-testid*="x" i], .x, .cross, [data-x], [data-mark="x"]'
    );
    if (xNode) return 'x';

    const t = txt.trim();
    if (t === 'X' || t === 'x' || t === '×' || t === '✕') return 'x';

    return 'empty';
  }

  // Assegna id incrementali (se non già presenti) e restituisci info.
  let nextId = 0;
  for (const el of els) {
    const existing = el.getAttribute('data-queens-solver-id');
    if (existing != null) {
      const n = Number(existing);
      if (Number.isFinite(n)) nextId = Math.max(nextId, n + 1);
    }
  }

  const out = [];
  for (const el of els) {
    const rect = el.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    if (!w || !h) continue;

    if (el.getAttribute('data-queens-solver-id') == null) {
      el.setAttribute('data-queens-solver-id', String(nextId));
      nextId++;
    }

    const id = Number(el.getAttribute('data-queens-solver-id'));
    const cs = window.getComputedStyle(el);
    const disabled = el.hasAttribute('disabled') || cs.pointerEvents === 'none';

    out.push({
      id,
      x: rect.x,
      y: rect.y,
      w: rect.width,
      h: rect.height,
      cx: rect.x + rect.width / 2,
      cy: rect.y + rect.height / 2,
      regionKey: regionKey(el),
      state: cellState(el),
      disabled,
    });
  }
  return out;
}
"""

JS_CELL_STATE = r"""
(id) => {
  const el = document.querySelector(`[data-queens-solver-id="${id}"]`);
  if (!el) return null;
  const txt = (el.innerText || '');
  const aria = (el.getAttribute('aria-label') || '');
  const cls = (el.className || '');

  const qNode = el.querySelector(
    '[aria-label*="queen" i], [aria-label*="regina" i], [data-testid*="queen" i], .queen, [data-queen], img[alt*="queen" i], svg[aria-label*="queen" i]'
  );
  if (qNode || /queen|regina|reina|dama|\uD83D\uDC51|\u265B/i.test(txt + ' ' + aria + ' ' + cls)) {
    return 'queen';
  }

  const xNode = el.querySelector(
    '[aria-label="X"], [aria-label*="cross" i], [data-testid*="x" i], .x, .cross, [data-x], [data-mark="x"]'
  );
  if (xNode) return 'x';

  const t = txt.trim();
  if (t === 'X' || t === 'x' || t === '×' || t === '✕') return 'x';

  return 'empty';
}
"""


# -------------------------------
# Utility per clustering (riconoscimento griglia)
# -------------------------------

def _cluster_1d(values: Sequence[float], tol: float) -> List[float]:
    """Clusterizza valori 1D ordinati: inizia un nuovo cluster se distanza > tol.

    Ritorna la lista dei centroidi (media) di ciascun cluster.
    """
    if not values:
        return []
    vals = sorted(values)
    clusters: List[List[float]] = [[vals[0]]]
    means: List[float] = [vals[0]]
    for v in vals[1:]:
        if abs(v - means[-1]) > tol:
            clusters.append([v])
            means.append(v)
        else:
            clusters[-1].append(v)
            means[-1] = sum(clusters[-1]) / len(clusters[-1])
    return means


def _nearest_index(centers: Sequence[float], v: float, tol: float) -> Optional[int]:
    best_i: Optional[int] = None
    best_d = float("inf")
    for i, c in enumerate(centers):
        d = abs(v - c)
        if d < best_d:
            best_d = d
            best_i = i
    if best_i is None or best_d > tol:
        return None
    return best_i


def _try_infer_square_grid(items: List[dict], target_size: float, *, min_n: int, max_n: int) -> Optional[Grid]:
    # Filtra per dimensione (quadrati circa)
    keep: List[dict] = []
    for it in items:
        w = float(it["w"])
        h = float(it["h"])
        if w < 12 or h < 12:
            continue
        aspect = w / h if h else 999
        if aspect < 0.75 or aspect > 1.33:
            continue
        s = (w + h) / 2
        if abs(s - target_size) > target_size * 0.25:
            continue
        if it.get("disabled"):
            # Le celle di solito non sono disabilitate. Le teniamo comunque? Dipende dal sito.
            # Per sicurezza le escludiamo: spesso pulsanti UI secondari sono disabled.
            continue
        keep.append(it)

    if len(keep) < min_n * min_n:
        return None

    tol = target_size * 0.60
    row_centers = _cluster_1d([float(it["cy"]) for it in keep], tol)
    col_centers = _cluster_1d([float(it["cx"]) for it in keep], tol)

    if not row_centers or not col_centers:
        return None

    # La griglia deve essere NxN, con N ragionevole
    if len(row_centers) != len(col_centers):
        return None

    n = len(row_centers)
    if n < min_n or n > max_n:
        return None

    # Mappa (r,c) -> best item (quello più vicino al centro)
    mapping: Dict[Tuple[int, int], dict] = {}
    for it in keep:
        r = _nearest_index(row_centers, float(it["cy"]), tol)
        c = _nearest_index(col_centers, float(it["cx"]), tol)
        if r is None or c is None:
            continue
        key = (r, c)
        # se duplicato, scegli quello più vicino al centro della cella
        dist = abs(float(it["cy"]) - row_centers[r]) + abs(float(it["cx"]) - col_centers[c])
        if key not in mapping:
            mapping[key] = {**it, "_dist": dist}
        else:
            if dist < mapping[key]["_dist"]:
                mapping[key] = {**it, "_dist": dist}

    if len(mapping) < n * n:
        return None

    # Costruisci matrici
    cell_id: List[List[int]] = [[-1] * n for _ in range(n)]
    region_key_grid: List[List[str]] = [[""] * n for _ in range(n)]
    state: List[List[str]] = [["empty"] * n for _ in range(n)]

    for r in range(n):
        for c in range(n):
            it = mapping.get((r, c))
            if it is None:
                return None
            cell_id[r][c] = int(it["id"])
            region_key_grid[r][c] = str(it.get("regionKey") or "")
            state[r][c] = str(it.get("state") or "empty")

    # Mappa regioni: ci aspettiamo esattamente N regioni diverse
    keys = [region_key_grid[r][c] for r in range(n) for c in range(n)]
    # Filtra vuoti
    keys_nonempty = [k for k in keys if k]
    if len(keys_nonempty) < n * n * 0.8:
        # troppo "trasparente" => probabilmente non stiamo leggendo il colore giusto
        return None

    unique_keys = sorted(set(keys_nonempty))
    if len(unique_keys) != n:
        # In Queens, #regioni == N (altrimenti sarebbe impossibile avere 1 per riga/colonna/region)
        return None

    key_to_region = {k: i for i, k in enumerate(unique_keys)}
    region: List[List[int]] = [[-1] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            k = region_key_grid[r][c]
            if not k:
                return None
            region[r][c] = key_to_region[k]

    region_key_by_idx = {i: k for k, i in key_to_region.items()}

    return Grid(n=n, cell_id=cell_id, region=region, region_key_by_idx=region_key_by_idx, state=state)


def infer_grid_from_page_items(items: List[dict], *, min_n: int = 4, max_n: int = 12) -> Grid:
    if not items:
        raise RuntimeError("Nessun elemento candidato trovato nella pagina.")

    # Buckets di dimensione: scegliamo i più frequenti
    sizes = []
    for it in items:
        w = float(it.get("w", 0))
        h = float(it.get("h", 0))
        if w <= 0 or h <= 0:
            continue
        s = (w + h) / 2
        if s < 12 or s > 200:
            continue
        aspect = w / h if h else 999
        if 0.75 <= aspect <= 1.33:
            sizes.append(int(round(s)))

    if not sizes:
        raise RuntimeError("Impossibile stimare la dimensione delle celle (nessun quadrato candidato).")

    common = Counter(sizes).most_common(8)

    best: Optional[Grid] = None
    best_score = -1
    for size_bucket, count in common:
        grid = _try_infer_square_grid(items, float(size_bucket), min_n=min_n, max_n=max_n)
        if grid is None:
            continue
        score = grid.n * grid.n
        # Preferisci griglie più grandi se pari (tipico Queens 10x10)
        score += grid.n
        if score > best_score:
            best_score = score
            best = grid

    if best is None:
        # Suggerimento per debug
        counts_str = ", ".join([f"{s}px:{c}" for s, c in common[:6]])
        raise RuntimeError(
            "Non riesco a riconoscere una griglia NxN valida. "
            "Possibili cause: il gioco usa canvas, selettori diversi, o il colore regione non è sul background. "
            f"(cluster size candidati: {counts_str})"
        )

    return best


# -------------------------------
# Solver
# -------------------------------

def solve_queens(grid: Grid) -> Dict[int, int]:
    """Ritorna assignment: row -> col (posizione della regina per ogni riga)."""

    n = grid.n

    # Queens già presenti: le consideriamo vincoli fissi
    fixed: Dict[int, int] = {}
    for r in range(n):
        for c in range(n):
            if grid.state[r][c] == "queen":
                if r in fixed and fixed[r] != c:
                    raise RuntimeError(f"Trovate 2 regine nella stessa riga {r}. Usa --reset per pulire.")
                fixed[r] = c

    # Pre-check: vincoli base su fixed
    used_cols = set()
    used_regions = set()

    def reg_of(r: int, c: int) -> int:
        return grid.region[r][c]

    for r, c in fixed.items():
        if c in used_cols:
            raise RuntimeError("Ci sono regine in due righe diverse ma stessa colonna. Usa --reset per pulire.")
        reg = reg_of(r, c)
        if reg in used_regions:
            raise RuntimeError("Ci sono regine in due regioni uguali. Usa --reset per pulire.")
        used_cols.add(c)
        used_regions.add(reg)

    # Vincolo: non adiacenti diagonalmente (dato 1 per riga/colonna)
    for r, c in fixed.items():
        for rr in (r - 1, r + 1):
            if rr in fixed and abs(c - fixed[rr]) == 1:
                raise RuntimeError("Ci sono due regine già piazzate che si toccano in diagonale. Usa --reset.")

    assignment: Dict[int, int] = dict(fixed)

    def candidates_for_row(r: int) -> List[int]:
        out: List[int] = []
        for c in range(n):
            if c in used_cols:
                continue
            reg = reg_of(r, c)
            if reg in used_regions:
                continue
            # no diagonale adiacente con righe vicine già assegnate
            if (r - 1) in assignment and abs(c - assignment[r - 1]) == 1:
                continue
            if (r + 1) in assignment and abs(c - assignment[r + 1]) == 1:
                continue
            out.append(c)
        return out

    unassigned = [r for r in range(n) if r not in assignment]

    def backtrack(rows_left: List[int]) -> bool:
        if not rows_left:
            return True

        # MRV: scegli riga con meno candidati
        rows_left.sort(key=lambda rr: len(candidates_for_row(rr)))
        r = rows_left[0]
        cand = candidates_for_row(r)
        if not cand:
            return False

        # Ordina candidati: meno vincolante (preferisci colonne/regioni più rare nelle righe rimanenti)
        col_pressure = Counter()
        reg_pressure = Counter()
        for rr in rows_left[1:]:
            for cc in candidates_for_row(rr):
                col_pressure[cc] += 1
                reg_pressure[reg_of(rr, cc)] += 1

        def score_choice(c: int) -> Tuple[int, int]:
            return (col_pressure[c], reg_pressure[reg_of(r, c)])

        cand.sort(key=score_choice)

        # Prova
        for c in cand:
            reg = reg_of(r, c)
            assignment[r] = c
            used_cols.add(c)
            used_regions.add(reg)

            # Forward-check veloce
            ok = True
            for rr in rows_left[1:]:
                if rr in assignment:
                    continue
                if not candidates_for_row(rr):
                    ok = False
                    break

            if ok:
                if backtrack(rows_left[1:]):
                    return True

            # Undo
            del assignment[r]
            used_cols.remove(c)
            used_regions.remove(reg)

        return False

    if not backtrack(unassigned):
        raise RuntimeError(
            "Nessuna soluzione trovata con i vincoli rilevati. Prova --reset o verifica che la griglia sia corretta."
        )

    return assignment


# -------------------------------
# Automazione browser
# -------------------------------

def _import_playwright_or_die():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        return sync_playwright
    except Exception as e:  # pragma: no cover
        print("Errore: Playwright non è installato o non è importabile.", file=sys.stderr)
        print("Installa con:", file=sys.stderr)
        print("  pip install playwright", file=sys.stderr)
        print("  python -m playwright install chromium", file=sys.stderr)
        raise e


def reset_all_queens(page, grid: Grid, *, verbose: bool = False) -> None:
    """Rimuove tutte le regine attualmente presenti (cliccando fino a tornare 'empty')."""
    for r in range(grid.n):
        for c in range(grid.n):
            if grid.state[r][c] != "queen":
                continue
            cid = grid.cell_id[r][c]
            loc = page.locator(f'[data-queens-solver-id="{cid}"]')
            # clicca finché non è vuota (queen -> empty tipicamente in 1 click)
            for _ in range(3):
                st = page.evaluate(JS_CELL_STATE, cid)
                if st == "empty":
                    break
                loc.click()
                page.wait_for_timeout(60)
            if verbose:
                print(f"Reset cella ({r},{c}) id={cid}")


def place_queen(page, cell_id: int, *, verbose: bool = False) -> None:
    """Clicca la cella fino a far comparire una regina (gestisce ciclo Empty->X->Queen)."""
    loc = page.locator(f'[data-queens-solver-id="{cell_id}"]')
    for attempt in range(5):
        st = page.evaluate(JS_CELL_STATE, cell_id)
        if st == "queen":
            return
        loc.click()
        page.wait_for_timeout(70)
    # ultimo check
    st = page.evaluate(JS_CELL_STATE, cell_id)
    if st != "queen":
        raise RuntimeError(
            f"Non sono riuscito a impostare la regina sulla cella id={cell_id} (stato finale={st})."
        )
    if verbose:
        print(f"Regina piazzata su id={cell_id}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Autosolver per il puzzle Queens su web (Playwright)")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"URL del gioco (default: {DEFAULT_URL})")
    parser.add_argument("--headless", action="store_true", help="Esegui browser in headless (sconsigliato per debug)")
    parser.add_argument("--min-n", type=int, default=4, help="Dimensione minima griglia (default 4)")
    parser.add_argument("--max-n", type=int, default=12, help="Dimensione massima griglia (default 12)")
    parser.add_argument("--reset", action="store_true", help="Rimuovi regine già presenti prima di risolvere")
    parser.add_argument("--dry-run", action="store_true", help="Non cliccare: stampa solo soluzione")
    parser.add_argument("--verbose", action="store_true", help="Log dettagliato")

    args = parser.parse_args(list(argv) if argv is not None else None)

    sync_playwright = _import_playwright_or_die()

    with sync_playwright() as p:
        # Profilo persistente: utile per login
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(args.url, wait_until="domcontentloaded")

        print("\nBrowser aperto.")
        print("- Se serve, fai login e apri il puzzle finché vedi chiaramente la griglia.")
        print("- Poi torna qui e premi INVIO per avviare il solver.\n")
        input("Premi INVIO quando la griglia è visibile... ")

        # Raccolta candidati e inferenza griglia
        items = page.evaluate(JS_COLLECT_CANDIDATES)
        if args.verbose:
            print(f"Candidati trovati: {len(items)}")

        grid = infer_grid_from_page_items(items, min_n=args.min_n, max_n=args.max_n)

        if args.verbose:
            print(f"Griglia riconosciuta: {grid.n}x{grid.n}")
            print(f"#regioni: {len(grid.region_key_by_idx)}")

        if args.reset:
            if args.verbose:
                print("Reset regine esistenti...")
            reset_all_queens(page, grid, verbose=args.verbose)
            # Re-scan dopo reset (stati cambiati)
            items = page.evaluate(JS_COLLECT_CANDIDATES)
            grid = infer_grid_from_page_items(items, min_n=args.min_n, max_n=args.max_n)

        # Solve
        assignment = solve_queens(grid)

        # Trasforma in lista ordinata
        solution: List[Tuple[int, int]] = [(r, assignment[r]) for r in range(grid.n)]

        print("\nSoluzione (riga, colonna):")
        print(", ".join([f"({r},{c})" for r, c in solution]))

        if args.dry_run:
            print("\n--dry-run attivo: non clicco nulla.")
            print("Lascia il browser aperto; chiudi con Ctrl+C se vuoi.")
            input("Premi INVIO per chiudere... ")
            context.close()
            return 0

        # Click
        print("\nPiazzo le regine sulla pagina...")
        for r, c in solution:
            cid = grid.cell_id[r][c]
            place_queen(page, cid, verbose=args.verbose)

        print("\nFatto. Se qualcosa non torna:")
        print("- prova con --reset (se avevi già piazzato regine sbagliate)")
        print("- oppure fai uno screenshot/inspect del DOM: potrebbe essere un sito diverso o canvas.")
        input("Premi INVIO per chiudere il browser... ")
        context.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())