/* ═══════════════════════════════════════════════════════════
   HOME PAGE — home.js
   ═══════════════════════════════════════════════════════════ */

// ── TYPEWRITER on hero subtitle ───────────────────────────
// (optional enhancement - already handled via CSS animation)

// ── ARCH CARD HOVER TILT ──────────────────────────────────
document.querySelectorAll('.arch-card').forEach(card => {
  card.addEventListener('mousemove', e => {
    const r = card.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width  - 0.5;
    const y = (e.clientY - r.top)  / r.height - 0.5;
    card.style.transform = `perspective(600px) rotateY(${x * 6}deg) rotateX(${-y * 4}deg)`;
  });
  card.addEventListener('mouseleave', () => { card.style.transform = ''; });
});

// ── COUNTER ANIMATE ───────────────────────────────────────
function animateCounter(el, target, suffix = '') {
  let start = 0;
  const step = target / 40;
  const timer = setInterval(() => {
    start += step;
    if (start >= target) { el.textContent = target + suffix; clearInterval(timer); }
    else { el.textContent = Math.floor(start) + suffix; }
  }, 30);
}

const statsObs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      statsObs.unobserve(e.target);
      // animate if numeric
      const numEl = e.target.querySelector('.stat-num');
      if (numEl && /^\d+/.test(numEl.textContent)) {
        const val = parseInt(numEl.textContent);
        const suffix = numEl.textContent.replace(/^\d+/, '');
        animateCounter(numEl, val, suffix);
      }
    }
  });
}, { threshold: 0.5 });
document.querySelectorAll('.stat').forEach(s => statsObs.observe(s));
