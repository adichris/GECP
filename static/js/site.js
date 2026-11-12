(() => {
  const root = document.documentElement;
  const key = `gecp-theme-${root.dataset.siteId}`;
  const schemes = ['system', 'light', 'dark'];
  const lightPalette = ['light', 'corporate', 'emerald', 'lofi'].includes(root.dataset.lightTheme) ? root.dataset.lightTheme : 'light';
  const systemScheme = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'system';
  try {
    const saved = localStorage.getItem(key);
    if (schemes.includes(saved)) preference = saved;
    else if (saved) preference = ['forest', 'business'].includes(saved) ? 'dark' : 'light';
  } catch (_) {}
  const applyTheme = () => {
    root.dataset.themePreference = preference;
    const resolved = preference === 'system' ? (systemScheme.matches ? 'dark' : 'light') : preference;
    root.dataset.theme = resolved === 'dark' ? 'dark' : lightPalette;
    root.style.colorScheme = resolved;
  };
  applyTheme();
  systemScheme.addEventListener('change', () => { if (preference === 'system') applyTheme(); });
  window.addEventListener('storage', event => {
    if (event.key !== key) return;
    preference = schemes.includes(event.newValue) ? event.newValue : 'system';
    applyTheme();
    const selector = document.getElementById('theme-selector');
    if (selector) selector.value = preference;
  });
  document.addEventListener('DOMContentLoaded', () => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (!motion.matches && 'IntersectionObserver' in window) {
      const observer = new IntersectionObserver(entries => entries.forEach(entry => {
        if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); }
      }), {threshold: 0.06});
      document.querySelectorAll('.directory-group, .programme-card, .editorial-card, .join-band, .asset-card').forEach(element => {
        element.classList.add('reveal'); observer.observe(element);
      });
      motion.addEventListener('change', event => { if (event.matches) document.querySelectorAll('.reveal').forEach(el => el.classList.add('is-visible')); });
    }
    const selector = document.getElementById('theme-selector');
    if (selector) {
      selector.value = preference;
      selector.addEventListener('change', () => {
        if (!schemes.includes(selector.value)) return;
        preference = selector.value;
        applyTheme();
        try { localStorage.setItem(key, selector.value); } catch (_) {}
      });
    }
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') document.querySelectorAll('[data-mega][open]').forEach(menu => {
        menu.open = false; menu.querySelector('summary').focus();
      });
    });
    document.addEventListener('click', event => {
      document.querySelectorAll('[data-mega][open]').forEach(menu => { if (!menu.contains(event.target)) menu.open = false; });
    });
    const errorNotice = () => {
      const notice = document.getElementById('request-status');
      if (notice) { notice.textContent = 'That request could not be completed. Please try again or reload the page.'; notice.hidden = false; }
    };
    document.body.addEventListener('htmx:responseError', errorNotice);
    document.body.addEventListener('htmx:sendError', errorNotice);
    document.body.addEventListener('htmx:timeout', errorNotice);
    document.body.addEventListener('htmx:afterSwap', () => {
      const notice = document.getElementById('request-status'); if (notice) notice.hidden = true;
    });
    const header = document.querySelector('.site-header');
    if (header) {
      const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 24);
      onScroll();
      window.addEventListener('scroll', onScroll, { passive: true });
    }
    document.addEventListener('submit', event => {
      const message = event.target.dataset && event.target.dataset.confirm;
      if (message && !window.confirm(message)) event.preventDefault();
    });
  });
})();
