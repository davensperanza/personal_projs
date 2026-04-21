import pyautogui
import time
import numpy as np

for _ in range(100):
    start = time.time()
    N = 8
    tasto = pyautogui.screenshot(region=(2272,774,10,10)).convert("RGB")
    ricerca_blu = tasto.getpixel((5,5))
    if ricerca_blu == (53, 116, 237):
        pyautogui.doubleClick(2272,774)
    else:
        pyautogui.doubleClick(2272,868)
    time.sleep(1)
    x1,y1 = 2215,381
    x2,y2 = 2734,895

    """
    for i in range(5):
        time.sleep(1)
        print(i+1, "s")
    print("lettura 1...")
    x1,y1 = pyautogui.position()
    print("...OK")
    print("lettura 2...")
    time.sleep(2)
    x2,y2 = pyautogui.position()
    print("...OK")
    """
    """
    # non funziona
    def create_grid(x1,y1,x2,y2):
        grid_x = np.linspace(x1,x2,N)
        grid_y = np.linspace(y1,y2,N)
        grid = []
        for r in range(N):
            r = set()
            for c in range(N):
                r.add(tuple(grid_x[r],grid_y[c]))
            grid.append(r)
        return grid
    """
    grid_x = np.linspace(x1,x2,N)
    grid_y = np.linspace(y1,y2,N)

    def find_position(r,c):
        return round(grid_x[c]), round(grid_y[r])

    # x,y = find_position(0,0)
    # img = pyautogui.screenshot(region=(x,y,10,10)).convert("RGB")
    # colore = img.getpixel((5,5))
    def pos_grid(x1,y1,x2,y2):
        final_grid = [[0 for _ in range(N)] for _ in range(N)]
        for r in range(N):
            for c in range(N):
                x,y = find_position(r,c)
                final_grid[r][c] = [x,y]

        return final_grid

    def color_grid(x1,y1,x2,y2):
        final_grid = [[0 for _ in range(N)] for _ in range(N)]
        for r in range(N):
            for c in range(N):
                x,y = find_position(r,c)
                # pyautogui.moveTo(x,y) # check
                img = pyautogui.screenshot(region=(x,y,10,10)).convert("RGB")
                colore = img.getpixel((5,5))
                final_grid[r][c] = colore

        return final_grid

    def find_empty(x_grid):
        for n in range(N):
            for m in range(N):
                if x_grid[n][m] is None:
                    return n,m

        return None

    def possibile_val(r,c,x_grid):
        vals = []
        for candidate in [True,False]:
            x_grid[r][c] = candidate
            if point_val(r,c,x_grid):
                vals.append(candidate)
            x_grid[r][c] = None
        return vals

    def possibile_val2(r,c,x_grid):
        vals = []
        for candinate in [True,False]:
            assign(r,c,candinate,x_grid)
            if point_val2(r,c,candinate,x_grid):
                vals.append(candinate)
            unassign(r,c,candinate,x_grid)
        return vals

    def choose_best(x_grid):
        best_pos = None
        best_vals = None
        
        for r in range(N):
            for c in range(N):
                if x_grid[r][c] is None:
                    vals = possibile_val2(r,c,x_grid)

                    if len(vals) == 0:
                        return (r,c), []
                    
                    if best_vals is None or len(vals) < len(best_vals):
                        best_pos = (r,c)
                        best_vals = vals
                        if len(best_vals) == 1:
                            return best_pos, best_vals
        return best_pos, best_vals

    def assign(r, c, val, x_grid):
        x_grid[r][c] = val
        if val is True:
            row_true[r] += 1
            col_true[c] += 1
            color_true[col_grid[r][c]] += 1

    def unassign(r, c, val, x_grid):
        if val is True:
            row_true[r] -= 1
            col_true[c] -= 1
            color_true[col_grid[r][c]] -= 1
        x_grid[r][c] = None


    def point_val(r,c, x_grid):

        if x_grid[r][c] is False:
            return True

        #row
        for i in range(N):
            if i != c and x_grid[r][i] is True:
                return False
        
        #col
        for j in range(N):
            if j!= r and x_grid[j][c] is True:
                return False
        
        #color
        for i in range(N):
            for j in range(N):
                if (i,j) != (r,c) and col_grid[r][c] == col_grid[i][j]:
                    if x_grid[i][j] is True:
                        return False

        #box
        for i in range(3):
            for j in range(3):
                rr = r+i-1
                cc = c+j-1
                if (i,j) != (1,1) and 0 <= rr < N and 0 <= cc < N and x_grid[rr][cc] is True:
                    return False

        return True

    def point_val2(r,c,val,x_grid):
        if x_grid[r][c] is False:
                return True

        #row
        if row_true[r] > 1:
            return False
        
        #col
        if col_true[c] > 1:
            return False
        
        #color
        if color_true[col_grid[r][c]] > 1:
            return False

        #box
        for i in range(3):
            for j in range(3):
                rr = r+i-1
                cc = c+j-1
                if (i,j) != (1,1) and 0 <= rr < N and 0 <= cc < N and x_grid[rr][cc] is True:
                    return False

        return True

    def final_check(x_grid):

        # riga
        for r in range(N):
            if sum(x_grid[r][c] is True for c in range(N)) != 1:
                return False

        # colonna
        for c in range(N):
            if sum(x_grid[r][c] is True for r in range(N)) != 1:
                return False

        # colore
        colori = set(col_grid[r][c] for r in range(N) for c in range(N))

        for colore in colori:
            count = 0
            for r in range(N):
                for c in range(N):
                    if col_grid[r][c] == colore and x_grid[r][c] is True:
                        count += 1

            if count != 1:
                return False

        return True
    # color grid to be created before

    def solver(x_grid):
        pos, vals = choose_best(x_grid)
        if pos is None:
            return final_check(x_grid)

        r, c = pos

        if len(vals) == 0:
            return False

        for candidate in vals:
            assign(r,c,candidate,x_grid)

            if point_val2(r,c,candidate,x_grid):
                if solver(x_grid):
                    return True
            unassign(r,c,candidate, x_grid)

        return False
        
    col_grid = color_grid(x1,y1,x2,y2)
    x_grid = [[None for _ in range(N)]for _ in range(N)]

    row_true = [0] * N
    col_true = [0] * N
    colori = set(col_grid[r][c] for r in range(N) for c in range(N))
    color_true = {colore: 0 for colore in colori}
    s2 = time.time()
    solver(x_grid)
    print("solving time: ", time.time()-s2)
    x_grid
    position_grid = pos_grid(x1,y1,x2,y2)
    count = -1
    for r in range(N):
        for c in range(N):
            if x_grid[r][c]:
                count += 1
                if count == 0:
                    # pyautogui.moveTo(position_grid[r][c][0],position_grid[r][c][1])
                    pyautogui.doubleClick(position_grid[r][c])
                    # pyautogui.tripleClick()

                else:
                    # pyautogui.moveTo(position_grid[r][c][0],position_grid[r][c][1])
                    pyautogui.doubleClick(position_grid[r][c])
                    # pyautogui.doubleClick()

    print("total: ",time.time()-start)