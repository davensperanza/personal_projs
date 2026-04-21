import copy
N = 9

def val_values(grid, r, c, test): # gli passo riga e colonna dello 0 trovato
    # riga
    check_r = 0
    if test not in grid[r]:
        check_r = 1
    else:
        return False
    
    # colonna
    check_c = 1
    for i in range(N):
        if test == grid[i][c]:
            check_c = 0
    if check_c == 0:
        return False
        
    check_b = 1
    # 3x3
    b = localization2(r,c)
    for i in range(b[0],b[0]+3):
        for j in range(b[1],b[1]+3):
            if test == grid[i][j]:
                check_b = 0

    if check_b+check_c+check_r == 3:
        return True
    else:
        return False

def localization(r,c):
    primo = [0,1,2]
    sec = [3,4,5]
    v = [r,c]
    b = []
    for el in v:
        if el in primo:
            b.append(0)
        elif el in sec:
            b.append(3)
        else:
            b.append(6)

    return b

def localization2(r,c):
    b = [(r//3)*3,(c//3)*3]
    return b

def build_map(grid):
    g = copy.deepcopy(grid)
    for r in range(N):
        for c in range(N):
            if g[r][c] == 0:
                g[r][c] = [n for n in range(1,N+1) if val_values(grid, r, c, n)] # piazzo direttamente lista di valori plausibili
    return g

def findLeast(grid):
    minlen = N+1
    ris = None
    for r in range(N):
        for c in range(N):
            if isinstance(grid[r][c], list):
                l = len(grid[r][c])
                if l == 0:
                    return False
                if l < minlen:
                    minlen = l
                    ris = (r,c)
    return ris

def pick_cell_less_cand(grid, setgrid_r, setgrid_c, boxes):
    minlen = N+1
    ris = None
    for r in range(N):
        for c in range(N):
            if grid[r][c] == 0:
                candidate = val_values_all(setgrid_r,setgrid_c,boxes,r,c)
                l = len(candidate)
                if l == 0:
                    return False
                if l < minlen:
                    minlen = l
                    ris = [r,c]
                    cand = candidate
                    if l == 1:
                        return ris,cand
    if ris is None:
        return True
    return ris, cand
                

def find_0(grid):
    for r in range(N):
        for c in range(N):
            if grid[r][c] == 0:
                return r,c
    return None

# voglio costruire mappa con set per fare i confronti
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
    

# confronto tutto il set dei candidate con tutti i set di riga, col, box, avrò solo 1 match positivo al massimo
def val_values_all(setgrid_r,setgrid_c,boxes, r, c):
    candidate = set(range(1,10))
    # riga
    row_num = candidate - setgrid_r[r]
    if not row_num:
        return set()
    
    # colonna
    col_num = candidate - setgrid_c[c]
    if not col_num:
        return set()

    # 3x3
    b = tuple(localization2(r,c))
    box_num = candidate - boxes[b]
    if not box_num:
        return set()

    intersec = row_num&col_num&box_num
    return intersec


def solve(grid):
    mappa = build_map(grid)
    least = findLeast(mappa)

    if least is None:
        return True # completed
    if least is False:
        return False # errore

    r,c = least

    for i in mappa[r][c]:
        grid[r][c] = i
        
        if solve(grid):
            return True
        grid[r][c] = 0

    return False

def solveFast(grid, setgrid_r=None, setgrid_c=None, boxes=None):
    if setgrid_r == None:
        setgrid_r, setgrid_c, boxes = set_map_for_validation(grid)
    topcell = pick_cell_less_cand(grid, setgrid_r, setgrid_c, boxes)
    if topcell is True:
        return True # finito
    if topcell is False:
        return False
    
    ris, cand = topcell
    b = tuple(localization2(ris[0],ris[1]))

    for n in cand:
        grid[ris[0]][ris[1]] = n
        # aggiorno i set
        setgrid_r[ris[0]].add(n)
        setgrid_c[ris[1]].add(n)
        boxes[b].add(n)

        if solveFast(grid, setgrid_r, setgrid_c, boxes):
            return True
        grid[ris[0]][ris[1]] = 0
        setgrid_r[ris[0]].remove(n)
        setgrid_c[ris[1]].remove(n)
        boxes[b].remove(n)

    return False

def solveSlow(grid):
    zero = find_0(grid)
    if zero is None:
        return True
    else:
        r,c = zero

    for n in range(1,N+1):
        if val_values(grid,r,c,n):
            grid[r][c] = n
            if solveSlow(grid):
                return True
            grid[r][c] = 0

    return False

            