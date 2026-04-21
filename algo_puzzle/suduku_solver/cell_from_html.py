import asyncio
import base64
from playwright.async_api import async_playwright
import cv2
import numpy as np
import os
import copy
import time
import pyautogui

start = time.time()
N = 9

URL = "https://sudoku.com/extreme/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")

        # Prendi il contesto esistente
        context = browser.contexts[0]

        # Aspetta finché esiste una pagina "sudoku.com"
        page = None
        for _ in range(60):  # fino a ~6 secondi (60*100ms)
            pages = context.pages
            for pg in pages:
                url = pg.url or ""
                if "sudoku.com" in url:
                    page = pg
                    break
            if page:
                break
            await asyncio.sleep(0.1)

        # Se non trovi la tab, aprila tu nello stesso contesto (stessa sessione)
        if page is None:
            page = await context.new_page()
            await page.goto(URL, wait_until="domcontentloaded")

        # Porta davanti (aiuta anche PyAutoGUI)
        await page.bring_to_front()

        # NON chiudere browser/context qui (è il tuo browser reale!)
        page.set_default_navigation_timeout(120_000)
        page.set_default_timeout(120_000)

        # Wait robusto: non assumere canvas[1], cerca il canvas più grande
        await page.wait_for_function("""
            () => {
                const cs = [...document.querySelectorAll('canvas')];
                if (cs.length === 0) return false;
                const big = cs.reduce((a,b)=> (a.width*a.height > b.width*b.height ? a : b));
                return big.width >= 300 && big.height >= 300;
            }
        """)

        await page.wait_for_timeout(500)

        data_url = await page.evaluate("""
            () => {
                const cs = [...document.querySelectorAll('canvas')];
                const big = cs.reduce((a,b)=> (a.width*a.height > b.width*b.height ? a : b));
                return big.toDataURL("image/png");
            }
        """)

        _, encoded = data_url.split(",", 1)
        img_bytes = base64.b64decode(encoded)

        with open("board.png", "wb") as f:
            f.write(img_bytes)

        print("Saved board.png (from the connected Chrome/Edge tab)")

def divide_cell(img_dir="board.png", margin = 0.1):
    out_dir = "cells"
    os.makedirs(out_dir, exist_ok=True)
    img = cv2.imread(img_dir, cv2.IMREAD_GRAYSCALE)
    _, img = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)
    a,l = img.shape
    ys = np.round(np.linspace(0, a, 10)).astype(int)
    xs = np.round(np.linspace(0, l, 10)).astype(int)

    for r in range(9):
        for c in range(9):
            y1,y2 = ys[int(r)], ys[int(r+1)]
            x1,x2 = xs[int(c)], xs[int(c+1)]
            cella = img[y1:y2,x1:x2]

            m = int((cella.shape)[0]*margin)
            final_cell = cella[m:-m,m:-m]

            cv2.imwrite(f"{out_dir}/r{r}_c{c}.png", final_cell)


def preprocess(path, out_size=28):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

    # binarizza: cifra bianca su nero
    _, bw = cv2.threshold(img, 0, 255,
                          cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    h, w = bw.shape

    # rimuovi bordi (griglia)
    pad = int(min(h, w) * 0.08)
    bw[:pad, :] = 0
    bw[-pad:, :] = 0
    bw[:, :pad] = 0
    bw[:, -pad:] = 0

    # trova contorni
    contours, _ = cv2.findContours(bw,
                                   cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None  # cella vuota

    cnt = max(contours, key=cv2.contourArea)

    # scarta roba troppo piccola
    if cv2.contourArea(cnt) < 0.02 * (h*w):
        return None

    x, y, ww, hh = cv2.boundingRect(cnt)
    digit = bw[y:y+hh, x:x+ww]

    # metti in quadrato
    s = max(ww, hh)
    canvas = np.zeros((s, s), dtype=np.uint8)

    y0 = (s - hh) // 2
    x0 = (s - ww) // 2
    canvas[y0:y0+hh, x0:x0+ww] = digit

    # resize finale
    resized = cv2.resize(canvas, (out_size, out_size),
                         interpolation=cv2.INTER_AREA)

    return resized

def load_templates(folder="templates"):
    templates = {}
    for d in range(1, 10):  # niente 0
        path = os.path.join(folder, f"{d}.png")
        templates[d] = preprocess(path)
    return templates

def match_digit(cell_img, templates, min_score=0.2):
    cell = preprocess(cell_img)

    # se quasi vuota → None
    if cv2.countNonZero(cell) < 10:
        return None

    best_digit = None
    best_score = -1

    cell_f = cell.astype(np.float32)/255.0
    cell_f = (cell_f - cell_f.mean()) / (cell_f.std() + 1e-6)

    for d, tmpl in templates.items():
        t = tmpl.astype(np.float32)/255.0
        t = (t - t.mean()) / (t.std() + 1e-6)

        score = float((cell_f * t).mean())

        if score > best_score:
            best_score = score
            best_digit = d

    if best_score < min_score:
        return None

    return best_digit

def val_values_set(setgrid_r,setgrid_c,boxes, r, c, test): # gli passo riga e colonna dello 0 trovato
    # riga
    check_r = 0
    if test not in setgrid_r[r]:
        check_r = 1
    else:
        return False
    
    # colonna
    check_c = 0
    if test not in setgrid_c[c]:
        check_c = 1
    else: 
        return False
        
    check_b = 0
    # 3x3
    b = tuple(localization2(r,c))
    if test not in boxes[b]:
            check_b = 1
    else:
        return False

    if check_b+check_c+check_r == 3:
        return True
    else:
        return False
    
def localization2(r,c):
    b = [(r//3)*3,(c//3)*3]
    return b

def set_map_for_validation(grid):
    setgrid_r = []
    for r in grid:
        row = set(r)
        setgrid_r.append(row)
    
    setgrid_c = []
    for c in range(N):
        col = []
        for r in range(N):
            col.append(grid[r][c])
        setgrid_c.append(set(col))

    boxes = {}
    for r in range(N):
        for c in range(N):
            b = localization2(r,c)

            boxes.setdefault(tuple(b),set()).add(grid[r][c])

    return setgrid_r,setgrid_c,boxes

def pick_cell_less_cand(grid, setgrid_r, setgrid_c, boxes):
    minlen = N+1
    ris = None
    for r in range(N):
        for c in range(N):
            if grid[r][c] == 0:
                candidate = {n for n in range(1,N+1) if val_values_set(setgrid_r, setgrid_c, boxes, r, c, n)}
                l = len(candidate)
                if l < minlen:
                    minlen = l
                    ris = [r,c]
                    cand = candidate
                    if l == 1:
                        return ris,cand
    if ris is None:
        return True
    return ris, cand

def solveFast(grid):
    setgrid_r, setgrid_c, boxes = set_map_for_validation(grid)
    topcell = pick_cell_less_cand(grid, setgrid_r, setgrid_c, boxes)
    if topcell is True:
        return True # finito
    else:
        ris, cand = topcell

    for n in cand:
        grid[ris[0]][ris[1]] = n
        if solveFast(grid):
            return True
        grid[ris[0]][ris[1]] = 0

    return False

if __name__ == "__main__":
    asyncio.run(main())

    divide_cell()

    templates = load_templates()

    grid = []

    for r in range(N):
        grid.append([])
        for c in range(N):
            img_dir = f"cells/r{r}_c{c}.png"
            best_match = match_digit(img_dir, templates)
            if best_match is None:
                grid[r].append(0)
            else:
                grid[r].append(best_match)

    M = 1
    b = np.zeros(M)

    for i in range(M):
        tre = time.perf_counter()
        g = copy.deepcopy(grid)
        solveFast(g)
        quattro = time.perf_counter()
        # a[i] = tre-due
        b[i] = quattro-tre

    print("To be Solved grid:")
    for r in grid:
        print(r)

    print("tempo",b.mean())
    print("Solved grid:")

    for r in g:
        print(r)

    print("Total time: ", time.time()-start)

    # time.sleep(5)

    for i in range(N):
        for j in range(N):
            if i%2 == 0:
                #if grid[i][j] == 0:
                pyautogui.write(str(g[i][j]))
                pyautogui.press('right')
            else:
                #if grid[i][j] == 0:
                pyautogui.write(str(g[i][8-j]))
                pyautogui.press('left')
        pyautogui.press('down')