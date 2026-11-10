"""
Gera um STL imprimível 3D da estátua de orante sumério (Tell Asmar / Eshnunna).
Modelagem procedural por campo de distância (SDF) + marching cubes.
Unidades: mm. Z para cima, frente da estátua voltada para -Y. Base plana em Z=0.

Uso: python3 gerar_estatua.py [altura_mm]   (padrão 150)
"""
import sys
import numpy as np
from skimage import measure
import trimesh

H = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
S = H / 150.0            # fator de escala (modelo desenhado para 150 mm)
STEP = 0.4 * S           # resolução da grade

xs = np.arange(-34*S, 34*S, STEP, dtype=np.float32)
ys = np.arange(-26*S, 26*S, STEP, dtype=np.float32)
zs = np.arange(-1.5*S, 154*S, STEP, dtype=np.float32)
X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
X /= S; Y /= S; Z /= S   # trabalha em coordenadas de 150 mm

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
    out = np.sqrt(np.maximum(qx,0)**2+np.maximum(qy,0)**2+np.maximum(qz,0)**2)
    return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - r

def smin(a, b, k=1.5):
    h = np.clip(0.5 + 0.5*(b-a)/k, 0, 1)
    return b*(1-h) + a*h - k*h*(1-h)

# ---------------- SANTO: saia (cone elíptico) com franja canelada ----------
theta = np.arctan2(Y, X)
zc = np.clip(Z, 0, 84)
t = zc / 84.0
a = 22.0 - 4.5*t**1.3          # semi-eixo X  (base 22 -> topo 17.5)
b = 15.5 - 6.0*t**1.2          # semi-eixo Y
FR = 38.0                      # altura da franja
fringe = Z < FR
# leve degrau para fora na franja + caneluras verticais
a = a + np.where(fringe, 0.9, 0.0)
b = b + np.where(fringe, 0.7, 0.0)
groove = 0.5 + 0.5*np.cos(theta*44)
depth = np.where(fringe, 0.9*groove*np.clip((FR-Z)/3.0, 0, 1)**0.5 + 0.0, 0.0)
q = np.sqrt((X/(a-depth))**2 + (Y/(b-depth*0.8))**2)
skirt = (q-1) * 12.0
skirt = np.maximum(skirt, Z-86)        # topo da saia

# ---------------- TRONCO / OMBROS -----------------------------------------
torso = ell(0, 0.5, 100, 15.5, 9.2, 22)
torso = smin(torso, ell(0, 0.5, 112, 18.5, 9.0, 8), 3)
body = smin(skirt, torso, 3.0)

# ---------------- BRAÇOS (cotovelos ao lado, mãos unidas na frente) ------
for s in (-1, 1):
    shoulder = (s*21.5, 0.5, 113)
    elbow    = (s*22.5, -1.5, 84)
    hand     = (s*3.5, -11.5, 87)
    body = smin(body, capsule(shoulder, elbow, 4.6, 4.2), 2.0)
    body = smin(body, capsule(elbow, hand, 4.2, 3.6), 2.0)
body = smin(body, ell(0, -12.0, 87, 8.0, 4.2, 4.8), 1.5)      # mãos
body = np.maximum(body, -(ell(0, -16.2, 87.0, 5.5, 0.9, 0.35)))
body = np.maximum(body, -(ell(0, -16.0, 85.6, 5.0, 0.9, 0.3)))

# ---------------- PESCOÇO / CABEÇA ----------------------------------------
body = smin(body, capsule((0, 0, 118), (0, 0, 128), 6.3), 2.5)
head = ell(0, 0.0, 138.0, 10.5, 10.0, 12.8)
# cabelo: massa volumosa com anéis horizontais ondulados
hair = ell(0, 2.0, 138.5, 12.6, 11.8, 13.8)
hair = hair + 0.35*np.sin(2*np.pi*Z/2.6 + 0.25*X)
# recorte da face na frente do cabelo
face_cut = ell(0, -11.0, 136.0, 8.6, 9.0, 11.0)
hair = np.maximum(hair, -face_cut)
head = smin(head, hair, 1.2)
body = smin(body, head, 2.0)
# rosto: bochechas / nariz
body = smin(body, ell(0, -6.5, 136.0, 8.2, 4.2, 9.5), 1.5)
body = smin(body, ell(0, -11.0, 134.5, 2.0, 3.2, 4.6), 1.2)   # nariz
# sobrancelha contínua
body = smin(body, capsule((-8.2, -8.6, 142.6), (8.2, -8.6, 142.6), 1.2), 0.8)

# olhos enormes (globos salientes com pupila rebaixada)
for s in (-1, 1):
    body = smin(body, ell(s*4.7, -9.6, 139.2, 4.2, 3.0, 4.2), 0.6)
    body = np.maximum(body, -(ell(s*4.7, -12.9, 139.2, 1.8, 1.3, 1.8)))
# boca (traço fino sob o bigode)
body = np.maximum(body, -ell(0, -12.0, 128.6, 2.6, 1.0, 0.5))

# ---------------- BARBA: bloco largo com fiadas onduladas -----------------
beard = rbox(0, -8.8, 109.0, 10.4, 3.6, 19.0, 2.6)
beard = beard + 0.55*np.sin(2*np.pi*Z/4.4 + 0.9*np.sin(X*0.55))   # fiadas
# bigode / bochechas conectando à barba
beard = smin(beard, ell(0, -9.5, 130.2, 7.5, 2.8, 2.2), 1.2)
body = smin(body, beard, 1.2)

# ---------------- plano de base plana em Z = 0 ----------------------------
body = np.maximum(body, -Z)

# ---------------- malha ---------------------------------------------------
body[0, :, :] = 1; body[-1, :, :] = 1
body[:, 0, :] = 1; body[:, -1, :] = 1
body[:, :, 0] = 1; body[:, :, -1] = 1
verts, faces, normals, _ = measure.marching_cubes(body, 0.0, spacing=(STEP, STEP, STEP))
verts += np.array([xs[0], ys[0], zs[0]])
mesh = trimesh.Trimesh(verts, faces, process=True)
mesh.fix_normals()
# suaviza ligeiramente o serrilhado da grade preservando volume
trimesh.smoothing.filter_taubin(mesh, iterations=6)
mesh.vertices[:, 2] -= mesh.vertices[:, 2].min()
mesh.apply_scale(H / mesh.extents[2])   # altura final exata
mesh.export("estatua_sumeria.stl")

print("watertight:", mesh.is_watertight, "| volume ok:", mesh.is_volume)
print("dimensões (mm):", np.round(mesh.extents, 1))
print("volume (cm³):", round(mesh.volume/1000, 1), "| triângulos:", len(mesh.faces))
