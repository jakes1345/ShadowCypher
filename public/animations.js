/**
 * ShadowCypher - Premium animations & transitions
 * View Transitions API, GSAP, micro-interactions, loading states
 */

// View Transitions API - wrap DOM updates for smooth page switches
function withViewTransition(updateFn) {
  if (typeof document.startViewTransition === 'function') {
    return document.startViewTransition(updateFn);
  }
  updateFn();
  return { ready: Promise.resolve(), finished: Promise.resolve() };
}

// Stagger children animation - run when page becomes visible
function staggerPageIn(container, opts) {
  opts = opts || {};
  const el = typeof container === 'string' ? document.querySelector(container) : container;
  if (!el) return;
  const delay = opts.delay || 0.03;
  const from = opts.from || { opacity: 0, y: 12 };
  const to = opts.to || { opacity: 1, y: 0 };
  const duration = opts.duration || 0.35;
  const ease = opts.ease || 'power2.out';

  const children = el.querySelectorAll(opts.selector || '.pnl, .ph, .ogrid, .pgrid, .router-hero, .router-hero-cards');
  if (!children.length) return;

  if (typeof gsap !== 'undefined') {
    gsap.fromTo(children, from, Object.assign({}, to, {
      duration: duration,
      stagger: delay,
      ease: ease,
      overwrite: true
    }));
  } else {
    children.forEach(function(c, i) {
      c.style.opacity = '0';
      c.style.transform = 'translateY(12px)';
      c.style.animation = 'staggerIn 0.35s ease forwards';
      c.style.animationDelay = (i * delay) + 's';
    });
  }
}

// Skeleton loader - real implementation for API loading states
function showSkeleton(preEl, type) {
  type = type || 'text';
  if (!preEl) return;
  var lines = type === 'text' ? 8 : type === 'json' ? 12 : 5;
  var html = '';
  for (var i = 0; i < lines; i++) {
    var width = 60 + Math.random() * 35;
    html += '<div class="skeleton-line" style="--w:' + width + '%"></div>';
  }
  preEl.innerHTML = '<div class="skeleton-block">' + html + '</div>';
  preEl.classList.add('skeleton-active');
}

function hideSkeleton(preEl, content) {
  if (!preEl) return;
  preEl.classList.remove('skeleton-active');
  if (typeof content === 'string') {
    preEl.textContent = content;
  } else if (content && typeof content === 'object') {
    preEl.textContent = JSON.stringify(content, null, 2);
  } else {
    preEl.innerHTML = '';
  }
}

// Button ripple effect
function addRipple(btn) {
  if (!btn || btn.dataset.ripple === 'true') return;
  btn.dataset.ripple = 'true';
  btn.addEventListener('click', function(e) {
    var rect = btn.getBoundingClientRect();
    var x = e.clientX - rect.left;
    var y = e.clientY - rect.top;
    var ripple = document.createElement('span');
    ripple.className = 'btn-ripple';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    btn.appendChild(ripple);
    setTimeout(function() { ripple.remove(); }, 600);
  });
}

function initButtonRipples() {
  document.querySelectorAll('.abtn:not([data-ripple])').forEach(addRipple);
}

function animateFeedback(el, type) {
  type = type || 'success';
  if (!el) return;
  var orig = el.style.transition;
  el.style.transition = 'transform 0.15s ease, box-shadow 0.15s ease';
  el.style.transform = 'scale(0.98)';
  el.style.boxShadow = type === 'success' ? '0 0 0 2px var(--green)' : '0 0 0 2px var(--red)';
  requestAnimationFrame(function() {
    requestAnimationFrame(function() {
      el.style.transform = '';
      el.style.boxShadow = '';
      setTimeout(function() { el.style.transition = orig; }, 150);
    });
  });
}

window.ShadowCypherAnim = {
  withViewTransition: withViewTransition,
  staggerPageIn: staggerPageIn,
  showSkeleton: showSkeleton,
  hideSkeleton: hideSkeleton,
  addRipple: addRipple,
  initButtonRipples: initButtonRipples,
  animateFeedback: animateFeedback
};
