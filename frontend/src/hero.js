// Scène 3D du bandeau : les deux vraies offres d'exemple (rendues depuis les PDF) flottent comme des feuilles de papier éclairées ;
// un fil jaune relie la ligne modifiée de l'une à celle de l'autre.
// Le canvas est posé DERRIÈRE le titre et la fenêtre en verre : les feuilles passent sous la vitre, qui les réfracte.
// Chorégraphie : entrée en vol au chargement, puis les feuilles suivent le défilement (elles se rapprochent, se font face quand le bandeau est au centre
// de l'écran — le fil s'allume — puis se tournent et s'écartent). Le papier ondule, d'autant plus que le défilement est rapide.
import { Scene, PerspectiveCamera, WebGLRenderer, PlaneGeometry, CircleGeometry, RingGeometry, MeshStandardMaterial, MeshBasicMaterial, Mesh, TextureLoader, SRGBColorSpace,
  Group, BufferGeometry, Float32BufferAttribute, Line, LineBasicMaterial, Points, PointsMaterial, Color, DoubleSide, Vector3, AdditiveBlending,
  AmbientLight, DirectionalLight, CanvasTexture } from 'three';

const SW = 3.0, SH = SW * 841.89 / 595.28;                      // feuille A4
const bend = (x, y) => 0.10 * (x / SW) ** 2 * 4 + 0.05 * Math.sin(y * 1.1 + x * 0.6);   // légère courbure du papier au repos
// ligne modifiée (fractions de la page, mesurées dans les PDF) : [x gauche, x droite, y]
const ROW = { original: { x: 0.9143, v: 0.2390 }, revised: { x: 0.0857, v: 0.2241 } };

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const sm = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;
const outBack = (t) => { const c = 1.45; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
const outCubic = (t) => 1 - Math.pow(1 - t, 3);

function shadowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d'), r = g.createRadialGradient(64, 64, 8, 64, 64, 62);
  r.addColorStop(0, 'rgba(0,0,0,.55)'); r.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = r; g.fillRect(0, 0, 128, 128); return new CanvasTexture(c);
}

function init(canvas) {
  let renderer;
  try { renderer = new WebGLRenderer({ canvas, antialias: true, alpha: true }); } catch { return; }   // sans WebGL : le bandeau reste lisible sans scène
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const scene = new Scene();
  const cam = new PerspectiveCamera(32, 1, 0.1, 50); cam.position.set(0, 0, 11);
  const world = new Group(); scene.add(world);

  scene.add(new AmbientLight('#ffffff', 1.9));
  const sun = new DirectionalLight('#ffffff', 1.4); sun.position.set(-3, 5, 6); scene.add(sun);
  const rim = new DirectionalLight('#8E9BFF', 0.5); rim.position.set(5, -2, 3); scene.add(rim);

  const loader = new TextureLoader(), shadowTex = shadowTexture();
  const mk = (file, side, phase) => {
    const geo = new PlaneGeometry(SW, SH, 28, 40);                 // une géométrie par feuille : chacune ondule à son rythme
    const base = Float32Array.from(geo.attributes.position.array);
    const map = loader.load(file, () => frame(performance.now())); map.colorSpace = SRGBColorSpace; map.anisotropy = 8;
    const mat = new MeshStandardMaterial({ map, roughness: 0.92, metalness: 0, side: DoubleSide, color: '#ffffff', transparent: true });
    const sheet = new Mesh(geo, mat);
    const shadow = new Mesh(new PlaneGeometry(SW * 1.25, SH * 0.32), new MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false, opacity: 0.8 }));
    const holder = new Group(); holder.add(sheet); world.add(holder);
    shadow.position.set(0, -SH * 0.62, -1.2); shadow.rotation.x = -1.2; holder.add(shadow);
    return { sheet, shadow, holder, geo, base, mat, side, phase, amp: 0 };
  };
  const A = mk('assets/sheet-original.jpg', -1, 0.0), B = mk('assets/sheet-revised.jpg', 1, 2.1);

  // altitude du papier en un point (x, y) à l'instant s : courbure + ondulation (vent)
  const zAt = (S, x, y, s) => bend(x, y) + S.amp * (0.4 + 0.6 * (y / SH + 0.5)) * (0.6 * Math.sin(y * 1.7 + s * 1.5 + S.phase) + 0.4 * Math.sin(x * 2.3 - s * 1.1 + S.phase * 1.7));
  function flutter(S, s) {
    const p = S.geo.attributes.position, b = S.base;
    for (let i = 0; i < p.count; i++) p.setZ(i, zAt(S, b[i * 3], b[i * 3 + 1], s));
    p.needsUpdate = true; S.geo.computeVertexNormals();
  }

  const wire = new Line(new BufferGeometry(), new LineBasicMaterial({ color: new Color('#FFD23F'), transparent: true }));
  world.add(wire);
  // points lumineux aux deux extrémités du fil (la ligne modifiée) : un halo qui pulse
  const glowMat = () => new MeshBasicMaterial({ color: '#FFD23F', transparent: true, blending: AdditiveBlending, depthWrite: false, side: DoubleSide });
  const dots = [0, 1].map(() => { const m = new Mesh(new CircleGeometry(0.075, 20), glowMat()); const r = new Mesh(new RingGeometry(0.1, 0.125, 28), glowMat()); m.add(r); m.userData.ring = r; world.add(m); return m; });

  const N = 110, p = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { p[i * 3] = (Math.random() - .5) * 13; p[i * 3 + 1] = (Math.random() - .5) * 7; p[i * 3 + 2] = (Math.random() - .5) * 7 - 1; }
  const dust = new Points(new BufferGeometry(), new PointsMaterial({ color: '#8E9BFF', size: 0.035, transparent: true, opacity: .6 }));
  dust.geometry.setAttribute('position', new Float32BufferAttribute(p, 3)); scene.add(dust);

  const mouse = { x: 0, y: 0 }, cur = { x: 0, y: 0 };
  addEventListener('pointermove', (e) => { mouse.x = e.clientX / innerWidth - .5; mouse.y = e.clientY / innerHeight - .5; }, { passive: true });

  let small = false;
  function size() {
    const w = canvas.clientWidth, h = canvas.clientHeight; small = w < 640;
    renderer.setSize(w, h, false); cam.aspect = w / h; cam.position.z = small ? 17 : 12.4; cam.updateProjectionMatrix();
  }
  size(); addEventListener('resize', size);

  const onSheet = (S, f, s) => {
    const x = (f.x - .5) * SW, y = (.5 - f.v) * SH;
    return world.worldToLocal(S.sheet.localToWorld(new Vector3(x, y, zAt(S, x, y, s) + 0.01)));
  };

  let t0 = 0, lastY = scrollY, vel = 0, dir = 0;
  function frame(t) {
    if (!t0) t0 = t;
    const s = t / 1000, still = reduce.matches;
    const r = canvas.getBoundingClientRect();
    // progression du bandeau dans l'écran : 0 = il entre par le bas, 0.5 = centré, 1 = il sort par le haut
    const k = still ? 0.5 : clamp((innerHeight - r.top) / (innerHeight + r.height));
    const mid = sm(0, 0.5, k) * (1 - sm(0.5, 1, k));                // 1 quand le bandeau est centré
    const dy = scrollY - lastY; lastY = scrollY; vel += (Math.min(Math.abs(dy), 90) - vel) * 0.12; if (dy) dir += (Math.sign(dy) - dir) * 0.2;
    cur.x += (mouse.x - cur.x) * 0.05; cur.y += (mouse.y - cur.y) * 0.05;

    for (const S of [A, B]) {
      const d = S.side;                                              // -1 : feuille de gauche, +1 : feuille de droite
      const delay = d < 0 ? 0.05 : 0.3;
      const ent = still ? 1 : clamp((s - t0 / 1000 - delay) / 1.5);
      const eb = outBack(ent), ec = outCubic(ent);
      const spread = lerp(small ? 1.9 : 2.9, small ? 1.45 : 2.15, sm(0, 0.5, k)) + (small ? 1.2 : 1.8) * sm(0.5, 1, k);
      const spin = lerp(0.78, 0.14, sm(0, 0.5, k)) + 1.0 * sm(0.5, 1, k);   // les feuilles se font face au centre, se détournent ensuite
      S.holder.position.x = d * (spread + (1 - eb) * 6.5);           // arrivée en vol depuis les côtés
      S.holder.position.y = (d < 0 ? 0.1 : -0.1) + (k - 0.5) * (d < 0 ? 1.5 : -0.9) - (1 - ec) * 2.6 + (still ? 0 : Math.sin(s * 0.9 + (d < 0 ? 0 : 1.7)) * 0.12);
      S.holder.position.z = (d < 0 ? -0.4 : 0.3) + mid * 0.7 - (1 - ec) * 1.5;
      S.holder.rotation.y = -d * (spin + (1 - eb) * 1.5) + cur.x * d * -0.12;
      S.holder.rotation.x = (d < 0 ? 0.05 : -0.04) + (1 - ec) * 0.5 + cur.y * 0.12 + (k - 0.5) * -0.18;
      S.holder.rotation.z = (d < 0 ? 0.06 : -0.07) + (1 - ec) * -d * 0.7 + (still ? 0 : Math.sin(s * 0.5 + S.phase) * 0.02) + dir * vel * 0.0016 * d;
      const sc = (0.86 + 0.2 * mid) * lerp(0.7, 1, ec); S.holder.scale.setScalar(sc);
      S.mat.opacity = ec * (1 - 0.65 * sm(0.78, 1, k));
      S.shadow.material.opacity = 0.8 * ec;
      S.amp = still ? 0 : 0.035 + vel * 0.0034 + (1 - ec) * 0.12;   // plus on défile vite, plus le papier claque
      if (!still || !S.flat) { flutter(S, s); S.flat = still; }
    }
    world.rotation.y = cur.x * 0.3; world.rotation.x = cur.y * 0.14;
    dust.position.y = (k - 0.5) * 2.2; dust.rotation.y = still ? 0 : s * 0.02;

    world.updateMatrixWorld(true);
    const pa = onSheet(A, ROW.original, s), pb = onSheet(B, ROW.revised, s);
    const lit = still ? 1 : sm(0.12, 0.42, k) * (1 - sm(0.62, 0.92, k)) * clamp((s - t0 / 1000 - 1.2) / 0.8);   // le fil s'allume quand les feuilles se font face
    const m = pa.clone().lerp(pb, .5); m.z += 0.7; m.y += 0.4 + Math.sin(s * 1.4) * 0.05;
    const total = 29, shown = Math.max(2, Math.round(total * lit)), pts = [];
    for (let i = 0; i < shown; i++) { const u = i / 28, v = 1 - u; pts.push(v * v * pa.x + 2 * u * v * m.x + u * u * pb.x, v * v * pa.y + 2 * u * v * m.y + u * u * pb.y, v * v * pa.z + 2 * u * v * m.z + u * u * pb.z); }
    wire.geometry.setAttribute('position', new Float32BufferAttribute(pts, 3));
    wire.material.opacity = clamp(lit * 1.4);
    [pa, pb].forEach((q, i) => {
      const d = dots[i], pulse = still ? 0 : (s * 0.9 + i * 0.5) % 1;
      d.position.copy(q); d.lookAt(cam.position); d.material.opacity = lit * 0.95;
      d.userData.ring.scale.setScalar(1 + pulse * 2.4); d.userData.ring.material.opacity = lit * (1 - pulse) * 0.8;
    });
    renderer.render(scene, cam);
  }
  let raf = 0, visible = true;
  const loop = (t) => { frame(t); raf = visible && !document.hidden && !reduce.matches ? requestAnimationFrame(loop) : 0; };
  const start = () => { if (!raf) raf = requestAnimationFrame(loop); };
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) start(); }).observe(canvas);
  document.addEventListener('visibilitychange', () => !document.hidden && start());
  reduce.addEventListener?.('change', () => { frame(performance.now()); start(); });
  frame(performance.now()); start();
}

const heroCanvas = document.getElementById('hero-canvas');
if (heroCanvas) init(heroCanvas);
