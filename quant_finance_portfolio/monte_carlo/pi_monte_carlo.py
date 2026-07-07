import time
from matplotlib import pyplot as plt
import numpy as np

n_sim = 100000

xc, yc, r = 0.5, 0.5, 0.5

# Generate all points up front (vectorized)
rng = np.random.default_rng()
xs = rng.random(n_sim)
ys = rng.random(n_sim)
inside_mask = (xs - xc) ** 2 + (ys - yc) ** 2 <= r ** 2

# Running pi estimate for every k, computed once).
cum_inside = np.cumsum(inside_mask)
n_points   = np.arange(1, n_sim + 1)
pi_running = 4 * cum_inside / n_points

# Adaptive params interpolated on a log10(n) scale so dots stay visible
# whether n_sim is 100 or 100,000+.
log_n = np.log10(n_sim)
dot_size   = float(np.interp(log_n, [2, 3, 4, 5, 6], [18, 9, 3.5, 1.6, 0.8]))
alpha      = float(np.interp(log_n, [2, 3, 4, 5, 6], [0.9, 0.7, 0.5, 0.4, 0.3]))
batch_size = max(1, n_sim // 100)

fig1, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 6))

# filling of the circle
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect("equal")
ax.set_facecolor("white")
theta = np.linspace(0, 2 * np.pi, 300)
# ax.plot(xc + r * np.cos(theta), yc + r * np.sin(theta), color="#1a1a2e", linewidth=1.5)
title = ax.set_title("")

# convergence of the estimate
ax2.set_xscale("log")
ax2.set_xlim(1, n_sim)
ax2.set_ylim(np.pi - 0.5, np.pi + 0.5)
ax2.axhline(np.pi, color="#1a1a2e", linewidth=1, linestyle="--", label="π")
# Exact +/-1 standard error band: SE = 4*sqrt(p(1-p))/sqrt(N), with p = pi/4.
# p(1-p) is the Bernoulli variance of one point (inside/outside, prob p);
# pi_hat = 4*X/N, so Var(pi_hat) = 16*p(1-p)/N and SE = 4*sqrt(p(1-p))/sqrt(N).
# 4*sqrt(p(1-p)) ~= 1.642 is a standard deviation coefficient, NOT a variance.
band_n = n_points
p = np.pi / 4
se = 4 * np.sqrt(p * (1 - p))  # 1.642
ax2.fill_between(band_n, np.pi - se / np.sqrt(band_n), np.pi + se / np.sqrt(band_n),
                 color="#95a5a6", alpha=0.2, label="±1σ (≈1.64/√N)")
(conv_line,) = ax2.plot([], [], color="#2980b9", linewidth=1.2, label="estimate")
ax2.set_xlabel("number of points")
ax2.set_ylabel("π estimate")
ax2.set_title("Convergence")
ax2.legend(loc="upper right")

plt.ion()
start = time.time()

for i in range(0, n_sim, batch_size):
    j = min(i + batch_size, n_sim)
    mask = inside_mask[i:j]

    ax.scatter(xs[i:j][mask],  ys[i:j][mask],  s=dot_size, color="#27ae60", alpha=alpha, linewidths=0)
    ax.scatter(xs[i:j][~mask], ys[i:j][~mask], s=dot_size, color="#e74c3c", alpha=alpha, linewidths=0)

    # update convergence curve in place (fast: no re-plot)
    conv_line.set_data(n_points[:j], pi_running[:j])

    title.set_text(f"π ≈ {pi_running[j-1]:.5f}  |  {j:,} / {n_sim:,} points")
    plt.pause(0.0001)

plt.ioff()
pi = pi_running[-1]
elapsed = round(time.time() - start, 4)
print(f"Pi estimation: {pi:.6f}  (error: {abs(pi - np.pi):.6f})")
print(f"{n_sim:,} points in {elapsed}s")
plt.show()
