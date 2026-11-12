// Entry point: registers lazily loaded pages, sets the footer mode text, draws the background and starts the router.
import { start, lazy, route, app, isStatic, $ } from './core.js';

const PAGES = { 'home.js': ['home'], 'convert.js': ['convert'], 'about.js': ['about'] };
lazy(Object.fromEntries(Object.entries(PAGES).flatMap(([file, names]) => names.map(n => [n, () => import('./' + file)]))));
route('notfound', () => { app().innerHTML = '<h1>Not found</h1><p><a href="#/">Back to the start</a></p>'; });

$('#mode').textContent = isStatic()
  ? 'static site: files are converted in your browser and never uploaded'
  : 'local app: browser conversion plus the Python converter on this computer';

// Subtle background: slow contour lines drifting like an elevation profile (still under prefers-reduced-motion).
(function background() {
  const cv = $('#bg'), ctx = cv.getContext('2d');
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const draw = t => {
    const w = cv.width = innerWidth, h = cv.height = innerHeight;
    ctx.clearRect(0, 0, w, h);
    for (let k = 0; k < 7; k++) {
      ctx.strokeStyle = k % 3 ? 'rgba(255,122,47,.28)' : 'rgba(47,208,255,.3)';
      ctx.lineWidth = 1.2; ctx.beginPath();
      for (let x = 0; x <= w; x += 12) {
        const y = h * (0.2 + k * 0.11) + 26 * Math.sin(x / 170 + k + t / 5200) + 12 * Math.sin(x / 61 - k * 2 + t / 3100);
        x ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
    }
  };
  if (still) { draw(0); addEventListener('resize', () => draw(0)); return; }
  let last = 0;
  const loop = t => { if (t - last > 80) { draw(t); last = t; } requestAnimationFrame(loop); };
  requestAnimationFrame(loop);
})();

start();
