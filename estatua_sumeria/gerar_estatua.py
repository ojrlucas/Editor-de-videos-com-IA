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
STEP = 0.3                       # resolução da grade (mm, no modelo de 150 mm)
FR = 37.0                        # altura da franja da saia

xs = np.arange(-30, 30, STEP, dtype=np.float32)
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

    def rbox(cx, cy, cz, hx, hy, hz, r):
        qx = np.abs(X-cx)-(hx-r); qy = np.abs(Y-cy)-(hy-r); qz = np.abs(Z-cz)-(hz-r)
        o = np.sqrt(np.maximum(qx,0)**2+np.maximum(qy,0)**2+np.maximum(qz,0)**2)
        return o + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - r

    def smin(a, b, k=1.5):
        h = np.clip(0.5 + 0.5*(b-a)/k, 0, 1)
        return b*(1-h) + a*h - k*h*(1-h)

    def carve(body, tool):          # subtrai 'tool' do corpo
        return np.maximum(body, -tool)

    # ================= SAIA: cone elíptico com franja canelada =============
    t = np.clip(Z, 0, 85) / 85.0
    a = 22.4 - 4.8*t**1.25
    b = 15.8 - 6.0*t**1.15
    flare = np.clip((FR + 1.0 - Z)/2.5, 0, 1) * 0.6
    bump = 0.85*np.exp(-((Z-FR)/1.0)**2)            # friso que separa a franja
    a = a + flare + bump
    b = b + 0.8*(flare + bump)
    theta = np.arctan2(Y/b, X/a)
    g = (0.5 + 0.5*np.cos(theta*52))**1.4           # caneluras em V arredondado
    depth = 1.05*g*np.clip((FR-0.8-Z)/2.0, 0, 1)
    q = np.sqrt((X/(a-depth))**2 + (Y/(b-0.8*depth))**2)
    skirt = np.maximum((q-1)*11.0, Z-92.0)
    skirt = np.maximum(skirt, -Z)

    # ================= TRONCO / OMBROS =====================================
    torso = ell(0, 0.4, 100, 15.8, 9.6, 20)
    torso = smin(torso, ell(0, 0.4, 112.5, 18.4, 8.8, 8.5), 3.0)
    body = smin(skirt, torso, 4.5)

    # ================= BRAÇOS E MÃOS =======================================
    for s in (-1, 1):
        sh = (s*20.6, 0.4, 112.0); el = (s*22.6, -0.6, 85.5); hd = (s*5.0, -12.6, 89.0)
        body = smin(body, capsule(sh, el, 4.5, 3.9), 2.0)
        body = smin(body, capsule(el, hd, 3.9, 3.2), 2.0)
    hands = ell(0, -13.3, 89.0, 8.6, 4.3, 4.7)
    body = smin(body, hands, 1.6)
    for s in (-1, 1):                               # dedos
        for k in range(4):
            zf = 87.2 + k*1.35
            body = carve(body, ell(s*3.6, -17.6, zf, 3.6, 1.0, 0.28))
        body = carve(body, ell(s*7.7, -16.0, 89.0, 0.4, 1.2, 3.3))
    body = carve(body, ell(0, -17.6, 89.0, 0.35, 1.0, 3.6))   # junção das mãos

    # ================= PESCOÇO E CABEÇA ====================================
    body = smin(body, capsule((0, 0.5, 117), (0, 0.2, 129), 6.2), 3.0)
    head = ell(0, 0.0, 138.5, 10.6, 10.2, 13.0)
    # cabelo: calota com mechas em chevron a partir da risca central
    hair = ell(0, 1.8, 139.0, 12.8, 11.9, 13.4)
    w = np.sin(2*np.pi*Z/2.7 + 0.55*np.abs(X) + 0.12*Y)
    hair = hair + 0.38*w*np.clip((150.0-Z)/5.0, 0, 1)
    hair = carve(hair, ell(0, -11.0, 136.5, 8.7, 9.2, 11.0))        # abre a face
    head = smin(head, hair, 1.2)
    body = smin(body, head, 2.2)
    # mechas laterais descendo ao lado da barba
    for s in (-1, 1):
        lock = ell(s*11.4, -1.5, 122.0, 3.1, 6.2, 12.5)
        lock = lock + 0.38*np.sin(2*np.pi*(Z + 0.9*s*X)/2.7)
        body = smin(body, lock, 1.5)
    # rosto
    body = smin(body, ell(0, -6.6, 136.5, 8.4, 4.3, 9.8), 1.8)     # plano da face
    nose = capsule((0, -9.5, 141.0), (0, -13.4, 133.6), 1.7, 2.3)
    body = smin(body, nose, 1.4)
    for s in (-1, 1):
        body = smin(body, ell(s*1.9, -12.6, 132.9, 1.6, 1.5, 1.2), 0.6)  # narinas
    # sobrancelha em arco
    for s in (-1, 1):
        arc = capsule((s*1.0, -9.6, 143.2), (s*5.0, -10.3, 144.2), 1.15)
        arc = smin(arc, capsule((s*5.0, -10.3, 144.2), (s*9.2, -8.0, 141.6), 1.15, 0.9), 0.8)
        body = smin(body, arc, 0.9)
    # olhos grandes, com aro e pupila rebaixada
    for s in (-1, 1):
        cx, cy, cz = s*4.9, -10.0, 139.3
        body = smin(body, ell(cx, cy, cz, 4.5, 3.1, 4.5), 0.7)
        rr = np.sqrt((X-cx)**2 + (Z-cz)**2)
        ring = np.maximum(np.abs(rr-2.9)-0.22, (Y-(cy-1.9)))       # sulco da íris
        body = carve(body, np.maximum(ring, -(Y-(cy-4.2))))
        body = carve(body, ell(cx, cy-3.2, cz, 1.9, 1.5, 1.9))     # pupila
    # bigode + boca
    mus = ell(0, -11.0, 130.4, 6.8, 2.2, 1.7) + 0.2*np.sin(X*1.6)
    body = smin(body, mus, 1.0)
    body = carve(body, ell(0, -13.0, 128.7, 2.3, 1.0, 0.4))

    # ================= BARBA: bloco com fiadas onduladas ===================
    beard = rbox(0, -9.0, 110.5, 10.1, 3.5, 18.5, 2.6)
    wave = np.sin(2*np.pi*Z/4.3 + 1.5*np.sin(X*0.62))
    beard = beard + 0.62*wave
    body = smin(body, beard, 1.0)

    return np.maximum(body, -Z)          # base plana


# ---------------------- avalia a grade em fatias ---------------------------
vol = np.empty((len(xs), len(ys), len(zs)), np.float32)
CH = 64
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
mesh = max(mesh.split(only_watertight=False), key=lambda m: len(m.faces))  # descarta ilhas soltas
mesh.merge_vertices(); mesh.remove_unreferenced_vertices(); mesh.fix_normals()
trimesh.smoothing.filter_taubin(mesh, iterations=10)
mesh.vertices[:, 2] -= mesh.vertices[:, 2].min()
mesh.apply_scale(H / mesh.extents[2])
mesh.export("estatua_sumeria.stl")
print("watertight:", mesh.is_watertight, "| dimensões (mm):", np.round(mesh.extents, 1),
      "| volume (cm³):", round(mesh.volume/1000, 1), "| triângulos:", len(mesh.faces))

# ---------------------- prévia (splat de vértices) -------------------------
import imageio.v2 as io
V = mesh.vertices - [0, 0, 0]; N = mesh.vertex_normals
def view(phi, ppm=5.0):
    c, s = np.cos(phi), np.sin(phi)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    P = V @ R.T; Nn = N @ R.T
    L = np.array([-0.5, -0.7, 0.6]); L /= np.linalg.norm(L)
    lam = np.clip(Nn @ L, 0, 1)
    rim = np.clip(-Nn[:, 1], 0, 1)**2
    shade = 0.28 + 0.62*lam + 0.1*rim
    W, Ht = 62, 156
    img = np.zeros((int(Ht*ppm), int(W*ppm), 3), np.float32)
    yy = np.linspace(0.30, 0.10, img.shape[0])[:, None]; img[:] = (yy*np.array([0.75, 0.85, 0.85]))[:, :, None].transpose(0,2,1) if False else np.stack([yy*0.8]*3, -1).repeat(img.shape[1], 1)
    u = ((P[:, 0] + W/2)*ppm).astype(int); v = ((Ht - 1 - P[:, 2])*ppm).astype(int)
    order = np.argsort(-P[:, 1])             # longe -> perto
    base = np.array([0.93, 0.87, 0.76])
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            uu = np.clip(u[order]+du, 0, img.shape[1]-1); vv = np.clip(v[order]+dv, 0, img.shape[0]-1)
            img[vv, uu] = shade[order, None]*base
    return (np.clip(img, 0, 1)*255).astype(np.uint8)

io.imwrite("previa.png", np.concatenate([view(0), view(np.radians(-35)), view(np.radians(-90)), view(np.radians(180))], 1))
