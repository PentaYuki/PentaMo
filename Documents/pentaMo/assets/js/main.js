/* ═══════════════════════════════════════════════════════════
   PENTA AUTO — main.js
   Global scripts: nav, fade-in observer, grid canvas
   ═══════════════════════════════════════════════════════════ */

// ── NAV SCROLL ────────────────────────────────────────────
const nav = document.getElementById('nav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 40);
  });
  // Active link
  const path = window.location.pathname.split('/').pop();
  nav.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href')?.includes(path)) a.classList.add('active');
  });
}

// ── FADE IN OBSERVER ──────────────────────────────────────
const fadeObs = new IntersectionObserver(
  entries => entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('visible'); fadeObs.unobserve(e.target); }
  }),
  { threshold: 0.1 }
);
document.querySelectorAll('.fade-in').forEach((el, i) => {
  el.style.transitionDelay = (i * 0.05) + 's';
  fadeObs.observe(el);
});

// ── GRID CANVAS ───────────────────────────────────────────
const canvas = document.getElementById('grid-canvas');
if (canvas) {
  const ctx = canvas.getContext('2d');
  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    drawGrid();
  }
  function drawGrid() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = 'rgba(56,189,248,0.04)';
    ctx.lineWidth = 1;
    const spacing = 60;
    for (let x = 0; x <= canvas.width; x += spacing) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y <= canvas.height; y += spacing) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();
}

// ── FILTER TAGS ───────────────────────────────────────────
document.querySelectorAll('.filter-tag').forEach(tag => {
  tag.addEventListener('click', function () {
    const group = this.closest('.filter-bar');
    group.querySelectorAll('.filter-tag').forEach(t => t.classList.remove('active'));
    this.classList.add('active');
    // Trigger filter (extend per page)
    const filter = this.dataset.filter || 'all';
    document.dispatchEvent(new CustomEvent('penta:filter', { detail: { filter } }));
  });
});
