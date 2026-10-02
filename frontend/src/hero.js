// Scène 3D du bandeau : deux feuilles (offre d'origine / révisée) qui flottent, une ligne repérée sur chacune et le fil qui les relie.
import { Scene, PerspectiveCamera, WebGLRenderer, PlaneGeometry, MeshBasicMaterial, Mesh, CanvasTexture, SRGBColorSpace,
  Group, BufferGeometry, Float32BufferAttribute, Line, LineBasicMaterial, Points, PointsMaterial, Color, DoubleSide } from 'three';

const canvas = document.getElementById('hero-canvas');
if (canvas) init(canvas);

function sheetTexture(rows, hot, tint) {
  const c = document.createElement('canvas'); c.width = 512; c.height = 704;
  const g = c.getContext('2d');
  g.fillStyle = '#F4F6FF'; g.fillRect(0, 0, 512, 704);
  g.fillStyle = tint; g.fillRect(0, 0, 512, 96);
  g.fillStyle = '#14213D'; g.fillRect(40, 36, 150, 14); g.fillStyle = '#5B6B9A'; g.fillRect(40, 60, 100, 8);
  g.fillStyle = '#14213D'; g.fillRect(40, 128, 432, 26);
  g.fillStyle = '#F4F6FF'; [60, 230, 300, 380].forEach((x, i) => g.fillRect(x, 136, i === 0 ? 90 : 46, 10));
  for (let i = 0; i < rows; i++) {
    const y = 170 + i * 56;
    if (i === hot) { g.fillStyle = '#FFD23F'; g.fillRect(34, y - 6, 444, 40); }
    g.fillStyle = i === hot ? '#14213D' : '#9AA6C6';
    g.fillRect(48, y + 6, 120 + ((i * 53) % 90), 10);
    [236, 306, 380].forEach((x, k) => g.fillRect(x, y + 6, 40 + ((i + k) % 3) * 8, 10));
    g.fillRect(40, y + 40, 432, 1.5);
  }
  g.fillStyle = '#14213D'; g.fillRect(300, 640, 172, 14);
  const t = new CanvasTexture(c); t.colorSpace = SRGBColorSpace; t.anisotropy = 4; return t;
}

function init(canvas) {
  let renderer;
  try { renderer = new WebGLRenderer({ canvas, antialias: true, alpha: true }); } catch { return; }   // sans WebGL : le bandeau reste lisible sans scène
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new Scene();
  const cam = new PerspectiveCamera(32, 1, 0.1, 50); cam.position.set(0, 0, 11);
  const world = new Group(); scene.add(world);

  const geo = new PlaneGeometry(3.3, 4.54);
  const a = new Mesh(geo, new MeshBasicMaterial({ map: sheetTexture(8, 1, '#C9D2FF'), side: DoubleSide }));
  const b = new Mesh(geo, new MeshBasicMaterial({ map: sheetTexture(7, 0, '#FFE9A8'), side: DoubleSide }));
  a.position.set(-2.1, 0.1, -0.4); a.rotation.set(0.05, 0.42, 0.06);
  b.position.set(2.1, -0.1, 0.3); b.rotation.set(-0.04, -0.42, -0.07);
  world.add(a, b);

  // fil reliant la ligne repérée de chaque feuille
  const wire = new Line(new BufferGeometry(), new LineBasicMaterial({ color: new Color('#FFD23F') }));
  world.add(wire);
  // particules (poussière de papier)
  const N = 90, p = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { p[i * 3] = (Math.random() - .5) * 12; p[i * 3 + 1] = (Math.random() - .5) * 6; p[i * 3 + 2] = (Math.random() - .5) * 6 - 1; }
  const dust = new Points(new BufferGeometry(), new PointsMaterial({ color: '#8E9BFF', size: 0.035, transparent: true, opacity: .7 }));
  dust.geometry.setAttribute('position', new Float32BufferAttribute(p, 3)); scene.add(dust);

  const mouse = { x: 0, y: 0 }, cur = { x: 0, y: 0 };
  window.addEventListener('pointermove', (e) => { mouse.x = e.clientX / innerWidth - .5; mouse.y = e.clientY / innerHeight - .5; }, { passive: true });
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');

  function size() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false); cam.aspect = w / h;
    cam.position.z = w < 640 ? 17 : 11; cam.updateProjectionMatrix();
    a.position.x = w < 640 ? -1.5 : -2.1; b.position.x = w < 640 ? 1.5 : 2.1;
  }
  size(); addEventListener('resize', size);

  function frame(t) {
    const s = t / 1000;
    cur.x += (mouse.x - cur.x) * 0.05; cur.y += (mouse.y - cur.y) * 0.05;
    world.rotation.y = cur.x * 0.5; world.rotation.x = cur.y * 0.25;
    if (!reduce.matches) {
      a.position.y = 0.1 + Math.sin(s * 0.9) * 0.12; b.position.y = -0.1 + Math.sin(s * 0.9 + 1.7) * 0.12;
      a.rotation.z = 0.06 + Math.sin(s * 0.5) * 0.02; b.rotation.z = -0.07 + Math.cos(s * 0.5) * 0.02;
      dust.rotation.y = s * 0.02;
    }
    world.updateMatrixWorld(true);
    // ligne repérée : ligne 2 de la feuille d'origine -> ligne 1 de la révisée
    const pa = a.localToWorld(a.position.clone().set(1.55, 0.54, 0.02)).sub(world.position);
    const pb = b.localToWorld(b.position.clone().set(-1.55, 1.36, 0.02)).sub(world.position);
    const mid = pa.clone().lerp(pb, 0.5); mid.z += 0.6; mid.y += 0.35 + Math.sin(s * 1.4) * 0.05;
    const pts = []; for (let i = 0; i <= 24; i++) { const u = i / 24, v = 1 - u; pts.push(v * v * pa.x + 2 * u * v * mid.x + u * u * pb.x, v * v * pa.y + 2 * u * v * mid.y + u * u * pb.y, v * v * pa.z + 2 * u * v * mid.z + u * u * pb.z); }
    // les points sont en repère monde ; le groupe est tourné : on les repasse en repère local du groupe
    const loc = []; for (let i = 0; i < pts.length; i += 3) { const v = world.worldToLocal(a.position.clone().set(pts[i], pts[i + 1], pts[i + 2])); loc.push(v.x, v.y, v.z); }
    wire.geometry.setAttribute('position', new Float32BufferAttribute(loc, 3));
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
