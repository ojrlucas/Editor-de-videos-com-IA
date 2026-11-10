"""
Estátua de orante sumério (estilo Tell Asmar / Eshnunna, c. 2900-2600 a.C.)
Modelagem procedural por campo de distância (SDF) + marching cubes -> STL imprimível.
Unidades: mm. Z para cima, frente voltada para -Y, base plana em Z=0.

Uso: python3 gerar_estatua.py [altura_mm]   (padrão 150)
"""
import sys
import numpy as np
from skimage import measure
import trimesh

H = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
STEP = 0.25                      # resolução da grade (mm, no modelo de 150 mm)
FR = 38.0                        # altura da franja da saia
BELT = 88.3                      # altura do cinto

xs = np.arange(-29, 29, STEP, dtype=np.float32)
ys = np.arange(-19, 19, STEP, dtype=np.float32)
zs = np.arange(-1.5, 154, STEP, dtype=np.float32)


def field(X, Y, Z):
    def ell(cx, cy, cz, a, b, c):
        q = np.sqrt(((X-cx)/a)**2 + ((Y-cy)/b)**2 + ((Z-cz)/c)**2)
        return (q - 1) * min(a, b, c)

    def capsule(p0, p1, r0, r1=None):
        r1 = r0 if r1 is None else r1
        p0 = np.array(p0, np.float32); p1 = np.array(p1, np.float32)
        d = p1 - p0
        px, py, pz = X-p0[0], Y-p0[1], Z-p0[2]
        t = np.clip((px*d[0]+py*d[1]+pz*d[2]) / float(d @ d), 0, 1)
        dx, dy, dz = px-t*d[0], py-t*d[1], pz-t*d[2]
        return np.sqrt(dx*dx+dy*dy+dz*dz) - (r0 + (r1-r0)*t)

    def chain(pts, r0, r1):
        n = len(pts)-1; out = None
        for i in range(n):
            c = capsule(pts[i], pts[i+1], r0+(r1-r0)*i/n, r0+(r1-r0)*(i+1)/n)
            out = c if out is None else np.minimum(out, c)
        return out

    def rbox(cx, cy, cz, hx, hy, hz, r):
        qx = np.abs(X-cx)-(hx-r); qy = np.abs(Y-cy)-(hy-r); qz = np.abs(Z-cz)-(hz-r)
        o = np.sqrt(np.maximum(qx,0)**2+np.maximum(qy,0)**2+np.maximum(qz,0)**2)
        return o + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - r

    def smin(a, b, k=1.5):
        h = np.clip(0.5 + 0.5*(b-a)/k, 0, 1)
        return b*(1-h) + a*h - k*h*(1-h)

    def carve(body, tool):
        return np.maximum(body, -tool)

    def tiers(arg, period, amp):
        """Mechas em camadas: cristas arredondadas e vales estreitos."""
        h = np.abs(np.sin(np.pi*arg/period))**0.55
        return amp*(0.6 - h)

    # ===================== SAIA: sino elíptico + franja ====================
    t = np.clip(Z, 0, 86) / 86.0
    a = 22.6 - 4.9*t**1.25
    b = 16.0 - 6.2*t**1.15
    flare = np.clip((FR + 1.0 - Z)/2.5, 0, 1) * 0.6
    bump = 0.9*np.exp(-((Z-FR)/1.0)**2)              # friso entre saia e franja
    a = a + flare + bump
    b = b + 0.8*(flare + bump)
    theta = np.arctan2(Y/b, X/a)
    g = (0.5 + 0.5*np.cos(theta*56))**1.5            # caneluras da franja
    depth = 1.2*g*np.clip((FR-0.8-Z)/2.0, 0, 1)
    q = np.sqrt((X/(a-depth))**2 + (Y/(b-0.8*depth))**2)
    skirt = np.maximum((q-1)*11.0, Z-87.0)
    skirt = np.maximum(skirt, 0.07-Z)

    # ---- cinto trançado (corda) ----
    at, bt = 17.7 + 0.9, 9.9 + 0.8
    qb = np.sqrt((X/at)**2 + (Y/bt)**2)
    th_b = np.arctan2(Y/bt, X/at)
    d1 = (qb-1)*10.0 + 0.22*np.sin(th_b*40 + Z*1.8)   # corda diagonal
    d2 = np.abs(Z-BELT) - 3.0
    r = 1.1
    belt = np.sqrt(np.maximum(d1+r, 0)**2 + np.maximum(d2+r, 0)**2) + np.minimum(np.maximum(d1+r, d2+r), 0) - r
    body = smin(skirt, belt, 0.5)

    # ===================== TRONCO ==========================================
    torso = ell(0, 0.4, 104, 15.2, 9.2, 19.5)
    torso = smin(torso, ell(0, 0.4, 113.0, 18.6, 8.8, 8.0), 3.2)
    torso = smin(torso, ell(0, 0.4, 94.5, 17.0, 9.8, 10.5), 3.5)
    body = smin(body, torso, 1.0)
    for s in (-1, 1):                                  # clavículas
        body = smin(body, ell(s*7.5, 8.3, 108, 6.0, 1.6, 8.5), 2.5)   # omoplatas
    body = carve(body, capsule((0, 10.4, 100), (0, 10.2, 119), 0.5))      # coluna

    # ===================== BRAÇOS E MÃOS ===================================
    for s in (-1, 1):
        sh = (s*20.3, 0.4, 112.0); el = (s*22.3, -0.8, 86.0); hd = (s*5.0, -12.6, 89.5)
        body = smin(body, capsule(sh, el, 5.0, 4.2), 2.2)
        body = smin(body, capsule(el, hd, 4.2, 3.4), 2.2)
    body = smin(body, ell(0, -13.3, 89.5, 8.8, 4.4, 4.8), 1.6)           # mãos juntas
    for s in (-1, 1):
        body = smin(body, ell(s*2.4, -15.6, 92.4, 2.4, 1.4, 1.1), 0.7)   # polegares
        for k in range(4):
            body = carve(body, ell(s*3.8, -17.7, 87.4 + k*1.35, 3.7, 1.0, 0.27))   # dedos
        body = carve(body, ell(s*7.9, -16.2, 89.5, 0.4, 1.2, 3.4))
    body = carve(body, ell(0, -17.7, 89.5, 0.35, 1.0, 3.7))

    # ===================== PESCOÇO E CABEÇA ================================
    body = smin(body, capsule((0, 0.5, 117), (0, 0.2, 129), 6.0), 3.0)
    head = ell(0, 0.0, 138.6, 9.8, 10.0, 13.0)
    hair = ell(0, 1.8, 139.2, 10.9, 11.5, 13.3)
    fade = np.clip((150.0-Z)/5.0, 0, 1)
    hair = hair + tiers(Z + 1.5*np.abs(X) + 0.3*Y, 2.8, 0.6)*fade
    hair = carve(hair, ell(0, -11.0, 136.6, 8.4, 9.2, 10.8))             # abre a face
    hair = carve(hair, chain([(0, -9.5, 146.0), (0, -6.0, 150.2), (0, 0.5, 152.2),
                              (0, 7.5, 150.0), (0, 11.0, 144.0)], 0.5, 0.5))   # risca
    head = smin(head, hair, 1.2)
    body = smin(body, head, 2.2)

    # mechas laterais (cabelo ao lado da barba)
    for s in (-1, 1):
        lock = ell(s*9.4, -2.2, 126.0, 2.0, 6.0, 11.2)
        lock = lock + tiers(Z + 1.5*np.abs(X), 2.8, 0.6)
        body = smin(body, lock, 1.4)
    # cabelo caindo nas costas, em camadas
    back = rbox(0, 8.8, 120.0, 8.0, 3.0, 16.5, 1.8)
    back = back + tiers(Z + 0.9*np.abs(X), 3.0, 0.55)
    body = smin(body, back, 2.0)

    # --- rosto ---
    body = smin(body, ell(0, -6.4, 136.8, 7.6, 4.5, 9.8), 1.8)            # plano da face
    for s in (-1, 1):
        body = smin(body, ell(s*5.3, -8.3, 133.6, 3.3, 2.3, 3.1), 1.6)    # maçãs do rosto
    nose = capsule((0, -9.6, 141.6), (0, -13.4, 133.4), 1.5, 2.1)
    body = smin(body, nose, 1.4)
    for s in (-1, 1):
        body = smin(body, ell(s*2.2, -12.6, 132.7, 1.7, 1.5, 1.3), 0.6)   # asas do nariz
        body = carve(body, ell(s*3.5, -11.3, 133.2, 0.35, 1.2, 1.8))      # prega nasolabial
        body = carve(body, ell(s*1.4, -14.0, 132.0, 0.7, 0.9, 0.6))       # narina
    # sobrancelha contínua e grossa
    for s in (-1, 1):
        arc = chain([(s*9.0, -7.9, 141.2), (s*5.4, -10.4, 144.0), (s*1.4, -9.8, 143.0), (0, -9.7, 142.7)], 1.0, 1.3)
        body = smin(body, arc, 1.0)
    # olhos
    for s in (-1, 1):
        cx, cy, cz = s*4.8, -9.5, 139.0
        body = smin(body, ell(cx, cy, cz, 4.0, 2.7, 4.0), 0.9)
        rr = np.sqrt((X-cx)**2 + (Z-cz)**2)
        rim = np.sqrt((rr-4.1)**2 + (Y-(cy-1.5))**2) - 0.5                # pálpebras
        body = smin(body, rim, 0.5)
        ring = np.maximum(np.abs(rr-2.9)-0.2, (Y-(cy-1.9)))
        body = carve(body, np.maximum(ring, -(Y-(cy-4.3))))                 # íris
        body = carve(body, ell(cx, cy-3.1, cz, 2.0, 1.5, 2.0))              # pupila
    # bigode, lábios e boca
    for s in (-1, 1):
        body = smin(body, ell(s*3.3, -11.7, 130.6, 3.8, 2.0, 1.5) + 0.12*np.sin(X*2.2), 0.9)
    body = carve(body, ell(0, -13.2, 130.9, 0.35, 0.9, 1.2))                # filtro
    body = smin(body, ell(0, -12.0, 127.9, 2.5, 1.4, 0.9), 0.7)             # lábio inferior
    body = carve(body, ell(0, -12.9, 128.9, 2.5, 1.0, 0.33))                # boca

    # ===================== BARBA ===========================================
    beard = rbox(0, -9.0, 109.8, 7.8, 3.5, 18.8, 2.4)
    beard = beard + tiers(Z + 1.2*np.sin(0.8*X), 4.0, 0.7)
    body = smin(body, beard, 1.0)

    return np.maximum(body, 0.07-Z)


# ---------------------- avalia a grade em fatias ---------------------------
vol = np.empty((len(xs), len(ys), len(zs)), np.float32)
CH = 48
for k in range(0, len(zs), CH):
    X, Y, Z = np.meshgrid(xs, ys, zs[k:k+CH], indexing="ij")
    vol[:, :, k:k+CH] = field(X, Y, Z)
vol[0] = vol[-1] = 1
vol[:, 0] = vol[:, -1] = 1
vol[:, :, 0] = vol[:, :, -1] = 1

verts, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(STEP, STEP, STEP))
verts += np.array([xs[0], ys[0], zs[0]])
mesh = trimesh.Trimesh(verts, faces, process=True)
mesh.fix_normals()
mesh = max(mesh.split(only_watertight=False), key=lambda m: len(m.faces))   # descarta ilhas soltas
mesh.merge_vertices(); mesh.remove_unreferenced_vertices(); mesh.fix_normals()
trimesh.repair.fill_holes(mesh)
trimesh.smoothing.filter_taubin(mesh, iterations=10)
mesh.vertices[:, 2] -= mesh.vertices[:, 2].min()
mesh.apply_scale(H / mesh.extents[2])
mesh.export("estatua_sumeria.stl")
print("watertight:", mesh.is_watertight, "| dimensões (mm):", np.round(mesh.extents, 1),
      "| volume (cm³):", round(mesh.volume/1000, 1), "| triângulos:", len(mesh.faces))

# ---------------------- prévia (z-buffer por vértices) ---------------------
import imageio.v2 as io
V = np.asarray(mesh.vertices); N = np.asarray(mesh.vertex_normals)
def view(phi, ppm=6.0, W=60, Ht=154):
    c, s = np.cos(phi), np.sin(phi)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    P = V @ R.T; Nn = N @ R.T
    L = np.array([-0.5, -0.7, 0.6]); L /= np.linalg.norm(L)
    shade = 0.26 + 0.64*np.clip(Nn @ L, 0, 1) + 0.10*np.clip(-Nn[:, 1], 0, 1)**2
    h, w = int(Ht*ppm), int(W*ppm)
    u = ((P[:, 0] + W/2)*ppm).astype(int); v = ((Ht - 1 - P[:, 2])*ppm).astype(int)
    ok = (u > 1) & (u < w-2) & (v > 1) & (v < h-2)
    u, v, d, sh = u[ok], v[ok], P[ok, 1], shade[ok]
    zbuf = np.full((h, w), 1e9, np.float32)
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            np.minimum.at(zbuf, (v+dv, u+du), d)
    img = np.zeros((h, w), np.float32); cnt = np.zeros((h, w), np.float32)
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            vis = d <= zbuf[v+dv, u+du] + 0.35
            np.add.at(img, (v[vis]+dv, u[vis]+du), sh[vis]); np.add.at(cnt, (v[vis]+dv, u[vis]+du), 1)
    m = cnt > 0
    img[m] /= cnt[m]
    bg = np.linspace(0.30, 0.10, h)[:, None]*np.ones((1, w))
    col = np.where(m[..., None], img[..., None]*np.array([0.95, 0.89, 0.77]), bg[..., None]*np.array([0.8, 0.9, 0.9]))
    return (np.clip(col, 0, 1)*255).astype(np.uint8)

io.imwrite("previa.png", np.concatenate([view(0), view(np.radians(-35)), view(np.radians(-90)), view(np.radians(180))], 1))
# detalhe do rosto
io.imwrite("previa_rosto.png", view(np.radians(-20), ppm=14)[: int(154*14*0.42), :])
