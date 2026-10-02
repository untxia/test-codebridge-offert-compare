// Scène 3D du bandeau : les deux vraies offres d'exemple (rendues depuis les PDF) flottent comme des feuilles de papier éclairées ;
// un fil jaune relie la ligne modifiée de l'une à celle de l'autre.
import { Scene, PerspectiveCamera, WebGLRenderer, PlaneGeometry, MeshStandardMaterial, MeshBasicMaterial, Mesh, TextureLoader, SRGBColorSpace,
  Group, BufferGeometry, Float32BufferAttribute, Line, LineBasicMaterial, Points, PointsMaterial, Color, DoubleSide, Vector3,
  AmbientLight, DirectionalLight, CanvasTexture } from 'three';

const SW = 3.0, SH = SW * 841.89 / 595.28;                      // feuille A4
const bend = (x, y) => 0.10 * (x / SW) ** 2 * 4 + 0.05 * Math.sin(y * 1.1 + x * 0.6);   // légère courbure du papier
// ligne modifiée (fractions de la page, mesurées dans les PDF) : [x gauche, x droite, y]
const ROW = { original: { x: 0.9143, v: 0.2390 }, revised: { x: 0.0857, v: 0.2241 } };

function paperGeometry() {
  const g = new PlaneGeometry(SW, SH, 28, 40), p = g.attributes.position;
  for (let i = 0; i < p.count; i++) p.setZ(i, bend(p.getX(i), p.getY(i)));
  g.computeVertexNormals(); return g;
}

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
  const scene = new Scene();
  const cam = new PerspectiveCamera(32, 1, 0.1, 50); cam.position.set(0, 0, 11);
  const world = new Group(); scene.add(world);

  scene.add(new AmbientLight('#ffffff', 1.9));
  const sun = new DirectionalLight('#ffffff', 1.4); sun.position.set(-3, 5, 6); scene.add(sun);
  const rim = new DirectionalLight('#8E9BFF', 0.5); rim.position.set(5, -2, 3); scene.add(rim);

  const loader = new TextureLoader(), geo = paperGeometry(), shadowTex = shadowTexture();
  const mk = (file) => {
    const map = loader.load(file, () => frame(performance.now())); map.colorSpace = SRGBColorSpace; map.anisotropy = 8;
    const sheet = new Mesh(geo, new MeshStandardMaterial({ map, roughness: 0.92, metalness: 0, side: DoubleSide, color: '#ffffff' }));
    const shadow = new Mesh(new PlaneGeometry(SW * 1.25, SH * 0.32), new MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false, opacity: 0.8 }));
    const holder = new Group(); holder.add(sheet); world.add(holder);
    return { sheet, shadow, holder };
  };
  const A = mk('assets/sheet-original.jpg'), B = mk('assets/sheet-revised.jpg');
  A.holder.position.set(-2.1, 0.1, -0.4); A.holder.rotation.set(0.05, 0.42, 0.06);
  B.holder.position.set(2.1, -0.1, 0.3); B.holder.rotation.set(-0.04, -0.42, -0.07);
  for (const s of [A, B]) { s.shadow.position.set(0, -SH * 0.62, -1.2); s.shadow.rotation.x = -1.2; s.holder.add(s.shadow); }

  const wire = new Line(new BufferGeometry(), new LineBasicMaterial({ color: new Color('#FFD23F') }));
  world.add(wire);

  const N = 90, p = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { p[i * 3] = (Math.random() - .5) * 12; p[i * 3 + 1] = (Math.random() - .5) * 6; p[i * 3 + 2] = (Math.random() - .5) * 6 - 1; }
  const dust = new Points(new BufferGeometry(), new PointsMaterial({ color: '#8E9BFF', size: 0.035, transparent: true, opacity: .6 }));
  dust.geometry.setAttribute('position', new Float32BufferAttribute(p, 3)); scene.add(dust);

  const mouse = { x: 0, y: 0 }, cur = { x: 0, y: 0 };
  addEventListener('pointermove', (e) => { mouse.x = e.clientX / innerWidth - .5; mouse.y = e.clientY / innerHeight - .5; }, { passive: true });
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');

  function size() {
    const w = canvas.clientWidth, h = canvas.clientHeight, small = w < 640;
    renderer.setSize(w, h, false); cam.aspect = w / h; cam.position.z = small ? 16 : 11.2; cam.updateProjectionMatrix();
    A.holder.position.x = small ? -1.55 : -2.15; B.holder.position.x = small ? 1.55 : 2.15;
  }
  size(); addEventListener('resize', size);

  // point de la feuille (fractions de page) -> repère du groupe monde
  const onSheet = (S, f) => {
    const x = (f.x - .5) * SW, y = (.5 - f.v) * SH;
    return world.worldToLocal(S.sheet.localToWorld(new Vector3(x, y, bend(x, y) + 0.01)));
  };

  function frame(t) {
    const s = t / 1000;
    cur.x += (mouse.x - cur.x) * 0.05; cur.y += (mouse.y - cur.y) * 0.05;
    const sc = Math.min(scrollY / 600, 1.5);                       // les feuilles dérivent doucement quand on descend
    world.rotation.y = cur.x * 0.5 + sc * 0.35; world.rotation.x = cur.y * 0.25 - sc * 0.12; world.position.y = sc * 0.9;
    if (!reduce.matches) {
      A.holder.position.y = 0.1 + Math.sin(s * 0.9) * 0.12; B.holder.position.y = -0.1 + Math.sin(s * 0.9 + 1.7) * 0.12;
      A.holder.rotation.z = 0.06 + Math.sin(s * 0.5) * 0.02; B.holder.rotation.z = -0.07 + Math.cos(s * 0.5) * 0.02;
      dust.rotation.y = s * 0.02;
    }
    world.updateMatrixWorld(true);
    const pa = onSheet(A, ROW.original), pb = onSheet(B, ROW.revised);
    const mid = pa.clone().lerp(pb, .5); mid.z += 0.7; mid.y += 0.4 + Math.sin(s * 1.4) * 0.05;
    const pts = [];
    for (let i = 0; i <= 28; i++) { const u = i / 28, v = 1 - u; pts.push(v * v * pa.x + 2 * u * v * mid.x + u * u * pb.x, v * v * pa.y + 2 * u * v * mid.y + u * u * pb.y, v * v * pa.z + 2 * u * v * mid.z + u * u * pb.z); }
    wire.geometry.setAttribute('position', new Float32BufferAttribute(pts, 3));
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
