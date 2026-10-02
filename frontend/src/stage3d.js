// 3D de la page : (1) le logo en vrai volume (feuilles biseautées, ligne surlignée, pastille ▲) qui s'assemble à l'ouverture, tourne sur lui-même
// pendant le défilement et vient se poser dans le header ; (2) un décor profond de feuilles/anneaux en verre qui dérive avec le scroll et la souris.
import { Scene, PerspectiveCamera, WebGLRenderer, Group, Mesh, Shape, ExtrudeGeometry, ShapeGeometry, TorusGeometry, CylinderGeometry, EdgesGeometry, LineSegments, LineBasicMaterial,
  MeshPhysicalMaterial, MeshStandardMaterial, MeshBasicMaterial, DirectionalLight, PointLight, AmbientLight, Color, PMREMGenerator, ACESFilmicToneMapping, SRGBColorSpace,
  Float32BufferAttribute, OctahedronGeometry, IcosahedronGeometry, DoubleSide } from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const outBack = (t) => { const c = 1.7; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
const ptr = { x: 0, y: 0, sx: 0, sy: 0 };
addEventListener('pointermove', (e) => { ptr.x = (e.clientX / innerWidth - .5) * 2; ptr.y = (e.clientY / innerHeight - .5) * 2; }, { passive: true });

function roundRect(w, h, r) {
  const s = new Shape(), x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r); s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); return s;
}
function paint(geo, c1, c2, w, h) {   // dégradé diagonal en couleurs de sommets
  const a = new Color(c1), b = new Color(c2), p = geo.attributes.position, col = [], c = new Color();
  for (let i = 0; i < p.count; i++) { const t = clamp(((p.getX(i) / w + .5) + (.5 - p.getY(i) / h)) / 2); c.copy(a).lerp(b, t); col.push(c.r, c.g, c.b); }
  geo.setAttribute('color', new Float32BufferAttribute(col, 3)); return geo;
}
const ext = (shape, depth, bev = .7) => new ExtrudeGeometry(shape, { depth, bevelEnabled: true, bevelThickness: bev, bevelSize: bev, bevelSegments: 4, curveSegments: 14 });

// ---------- le logo ----------
function buildLogo() {
  const g = new Group(), parts = {};
  const gloss = (c1, c2, w, h, shape, depth) => new Mesh(paint(ext(shape, depth), c1, c2, w, h), new MeshPhysicalMaterial({ vertexColors: true, roughness: .26, metalness: .05, clearcoat: .7, clearcoatRoughness: .18, envMapIntensity: .22 }));
  const bar = (w, h, mat, z) => { const m = new Mesh(ext(roundRect(w, h, h / 2), 1, .35), mat); m.position.z = z; return m; };
  const white = new MeshStandardMaterial({ color: '#dfe5ff', roughness: .5, emissive: '#7f8dff', emissiveIntensity: .1 });
  const hot = new MeshStandardMaterial({ color: '#ffc93f', roughness: .3, emissive: '#ff8a1f', emissiveIntensity: .3 });

  const back = new Group(); back.position.set(-12, 0, -5); back.rotation.z = 9 * Math.PI / 180;
  back.add(gloss('#4adea8', '#2a8fd8', 30, 42, roundRect(30, 42, 6), 3));
  [[16, 11], [18, 4], [12, -3]].forEach(([w, y], i) => { const b = bar(w, 3, white, 4.4); b.position.set(-4 + (w - 16) / 2 + (i === 0 ? 0 : 0), y, 4.4); back.add(b); });
  // positions (SVG) : lignes à x=11..: centre local = x+w/2-20
  back.children.slice(1).forEach((b, i) => { const w = [16, 18, 12][i], y = [32 - 21.5, 32 - 28.5, 32 - 35.5][i]; b.position.set(11 + w / 2 - 20, y, 4.4); });
  const front = new Group(); front.position.set(9.5, 2, 0); front.rotation.z = -8 * Math.PI / 180;
  front.add(gloss('#a9b6ff', '#5565f2', 33, 46, roundRect(33, 46, 6), 3));
  { const l1 = bar(19, 3.5, white, 4.4); l1.position.set(32 + 9.5 - 41.5, 30 - 18.75, 4.4);
    const hl = bar(21, 8, hot, 4.6); hl.position.set(31 + 10.5 - 41.5, 30 - 30, 4.6);
    const l3 = bar(13, 3.5, white, 4.4); l3.position.set(32 + 6.5 - 41.5, 30 - 42.75, 4.4); front.add(l1, hl, l3); parts.hl = hl; }
  const badge = new Group(); badge.position.set(17, -17, 7);
  { const disc = new Mesh(new CylinderGeometry(9, 9, 3, 48), new MeshPhysicalMaterial({ color: '#10142e', roughness: .3, clearcoat: 1, metalness: .2 })); disc.rotation.x = Math.PI / 2;
    const rim = new Mesh(new TorusGeometry(9, .55, 12, 64), new MeshStandardMaterial({ color: '#8e9bff', emissive: '#6577ff', emissiveIntensity: .6, roughness: .3 })); rim.position.z = 1.5;
    const t = new Shape(); t.moveTo(0, 6.2); t.lineTo(5.6, -3.2); t.lineTo(-5.6, -3.2); t.closePath();
    const tri = new Mesh(new ExtrudeGeometry(t, { depth: 1.2, bevelEnabled: true, bevelThickness: .5, bevelSize: .8, bevelSegments: 3 }), hot); tri.position.set(0, -1.1, 1.6);
    badge.add(disc, rim, tri); }
  g.add(back, front, badge); parts.back = back; parts.front = front; parts.badge = badge;
  return { g, parts };
}

function logoScene() {
  const canvas = document.getElementById('logo3d'); if (!canvas) return null;
  let r; try { r = new WebGLRenderer({ canvas, antialias: true, alpha: true }); } catch { return null; }
  r.setClearColor(0x000000, 0); r.outputColorSpace = SRGBColorSpace; r.toneMapping = ACESFilmicToneMapping; r.toneMappingExposure = .85;
  const scene = new Scene(), pm = new PMREMGenerator(r); scene.environment = pm.fromScene(new RoomEnvironment(), .04).texture;
  const cam = new PerspectiveCamera(30, 1, 10, 6000);
  const key = new DirectionalLight('#ffffff', 1.0); key.position.set(-300, 400, 600); scene.add(key);
  const rim = new PointLight('#8e9bff', 1.4e5, 0, 2); rim.position.set(400, -200, 300); scene.add(rim);
  scene.add(new AmbientLight('#8f98d8', .1));
  const { g, parts } = buildLogo(); const root = new Group(); root.add(g); scene.add(root);
  let W = 0, H = 0, t0 = 0, st = null, last = 0;
  const size = () => { W = innerWidth; H = innerHeight; r.setPixelRatio(Math.min(devicePixelRatio, 2)); r.setSize(W, H, false); cam.aspect = W / H; cam.position.z = (H / 2) / Math.tan(cam.fov * Math.PI / 360); cam.updateProjectionMatrix(); };
  size(); addEventListener('resize', size);
  const base = { back: parts.back.position.clone(), front: parts.front.position.clone(), badge: parts.badge.position.clone() };
  function draw(now) {
    if (!st) return; if (!t0) t0 = now; const t = (now - t0) / 1000, e = st.e, bell = Math.sin(Math.PI * e);
    ptr.sx += (ptr.x - ptr.sx) * .08; ptr.sy += (ptr.y - ptr.sy) * .08;
    const s = st.size / 64; root.scale.set(s, s, s); root.position.set(st.cx - W / 2, H / 2 - st.cy, 0);
    // assemblage à l'ouverture : chaque pièce arrive de loin en tournant, avec un petit rebond
    const q = (d, dur = 1.25) => clamp((t - d) / dur), a = outBack(q(.15)), b = outBack(q(.4)), c = outBack(q(1.05, .9));
    const B = parts.back, F = parts.front, K = parts.badge, hold = 1 - e;
    B.position.set(base.back.x - 46 * (1 - a), base.back.y - 22 * (1 - a), base.back.z - 40 * (1 - a) - bell * 14); B.rotation.y = -1.9 * (1 - a); B.scale.setScalar(Math.max(.001, lerp(.35, 1, clamp(a))));
    F.position.set(base.front.x + 46 * (1 - b), base.front.y + 22 * (1 - b), base.front.z + 30 * (1 - b) + bell * 6); F.rotation.y = 1.9 * (1 - b); F.scale.setScalar(Math.max(.001, lerp(.35, 1, clamp(b))));
    K.position.set(base.badge.x, base.badge.y, base.badge.z + bell * 18); K.scale.setScalar(Math.max(.001, c)); K.rotation.z = (1 - c) * -3;
    parts.hl.position.z = 4.6 + Math.sin(t * 2.2) * .25 * hold + bell * 4;
    // flottement + inclinaison à la souris, puis tour complet au défilement (face à nous à l'arrivée, e = 1)
    const fl = hold * (q(1.2, .6));
    g.position.y = Math.sin(t * 1.4) * 1.6 * fl; g.rotation.x = (-ptr.sy * .38 + Math.sin(t * .9) * .05) * hold * fl - bell * .22;
    g.rotation.y = (ptr.sx * .55 + Math.sin(t * .7) * .1) * hold * fl + e * Math.PI * 2;
    r.setSize(W, H, false); r.render(scene, cam);
  }
  return { update(s) { if (!st) document.querySelector('.stage')?.classList.add('gl'); st = s; canvas.style.opacity = s.out; canvas.style.visibility = s.out <= 0 ? 'hidden' : 'visible'; },
    frame: draw, active: () => st && st.out > 0 };
}

// ---------- le décor profond ----------
function bgScene() {
  const canvas = document.getElementById('bg3d'); if (!canvas || innerWidth < 640) return null;
  let r; try { r = new WebGLRenderer({ canvas, antialias: true, alpha: true }); } catch { return null; }
  r.setClearColor(0x000000, 0);
  const scene = new Scene(), cam = new PerspectiveCamera(45, 1, .1, 200), PAL = ['#8e9bff', '#4adea8', '#ff9ad5', '#ffd23f', '#6fb7ff'];
  const items = [];
  const mk = (geo, col, fill, x, y, z, rot) => {
    const grp = new Group(); const edges = new LineSegments(new EdgesGeometry(geo), new LineBasicMaterial({ color: col, transparent: true, opacity: .55 }));
    grp.add(new Mesh(geo, new MeshBasicMaterial({ color: col, transparent: true, opacity: fill, side: DoubleSide, depthWrite: false })), edges);
    grp.position.set(x, y, z); grp.rotation.set(...rot); scene.add(grp); items.push({ grp, sp: [(Math.random() - .5) * .25, (Math.random() - .5) * .35, (Math.random() - .5) * .15], ph: Math.random() * 6, y0: y }); };
  const N = 18, span = 70;
  for (let i = 0; i < N; i++) {
    const col = PAL[i % PAL.length], x = (Math.random() - .5) * 34, y = -(i / N) * span + 4 + (Math.random() - .5) * 4, z = -7 - Math.random() * 16, k = i % 4;
    const rot = [Math.random() * 3, Math.random() * 3, Math.random() * 3];
    if (k === 0 || k === 1) mk(new ShapeGeometry(roundRect(3.2, 4.4, .4)), col, .06, x, y, z, rot);
    else if (k === 2) mk(new TorusGeometry(1.6, .035, 8, 64), col, .0, x, y, z, rot);
    else mk(i % 8 === 3 ? new OctahedronGeometry(1.2) : new IcosahedronGeometry(1.1), col, .035, x, y, z, rot);
  }
  const size = () => { r.setPixelRatio(Math.min(devicePixelRatio, 1.5)); r.setSize(innerWidth, innerHeight, false); cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix(); };
  size(); addEventListener('resize', size);
  let sy0 = scrollY, kick = 0;
  return { frame(now) {
    const t = now / 1000, dy = scrollY - sy0; sy0 = scrollY; kick = kick * .92 + Math.abs(dy) * .004;
    const max = Math.max(1, document.documentElement.scrollHeight - innerHeight);
    cam.position.set(ptr.sx * 1.6, 4 - (scrollY / max) * span * .92, 12); cam.lookAt(ptr.sx * .6, cam.position.y - 1 - ptr.sy * .8, 0);
    for (const it of items) { it.grp.rotation.x += (it.sp[0] + kick) * .012; it.grp.rotation.y += (it.sp[1] + kick) * .012; it.grp.rotation.z += it.sp[2] * .01; it.grp.position.y = it.y0 + Math.sin(t * .5 + it.ph) * .35; }
    r.render(scene, cam); } };
}

if (!REDUCED) {
  const L = logoScene(), B = bgScene();
  window.__logo3d = L; dispatchEvent(new Event('logo3d-ready'));
  if (L || B) {
    const loop = (now) => { requestAnimationFrame(loop); if (document.hidden) return; B?.frame(now); if (L && L.active()) L.frame(now); };
    requestAnimationFrame(loop);
  }
}
