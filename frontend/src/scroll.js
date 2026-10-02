// Défilement inertiel (Lenis). Désactivé si l'utilisateur préfère moins de mouvement, et suspendu quand la fenêtre d'aperçu est ouverte.
import Lenis from 'lenis';

if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const lenis = new Lenis({ lerp: 0.09, wheelMultiplier: 0.95, smoothWheel: true, anchors: true });
  const raf = (t) => { lenis.raf(t); requestAnimationFrame(raf); };
  requestAnimationFrame(raf);
  const viewer = document.getElementById('viewer');
  if (viewer) {
    new MutationObserver(() => (viewer.open ? lenis.stop() : lenis.start())).observe(viewer, { attributes: true, attributeFilter: ['open'] });
  }
  window.__lenis = lenis;
}
