/* ============================================================
   ROOTS & RECKONING — app.js
   Handles: dark mode toggle, timeline expand/filter, map, scroll animations
   ============================================================ */

(function () {
  'use strict';

  // ── DARK MODE TOGGLE ──────────────────────────────────────
  const root = document.documentElement;
  const toggle = document.querySelector('[data-theme-toggle]');

  let currentTheme = 'dark'; // default
  try {
    const sys = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    currentTheme = sys;
  } catch (e) {}
  root.setAttribute('data-theme', currentTheme);
  updateToggleIcon(currentTheme);

  function updateToggleIcon(theme) {
    if (!toggle) return;
    toggle.setAttribute('aria-label', 'Switch to ' + (theme === 'dark' ? 'light' : 'dark') + ' mode');
    toggle.innerHTML = theme === 'dark'
      ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
           <circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
         </svg>`
      : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
           <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
         </svg>`;
  }

  if (toggle) {
    toggle.addEventListener('click', () => {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', currentTheme);
      updateToggleIcon(currentTheme);
      // Re-render map tiles if map exists
      if (window._leafletMap) {
        window._leafletMap.invalidateSize();
      }
    });
  }


  // ── TIMELINE EVENT EXPAND/COLLAPSE ───────────────────────
  const eventCards = document.querySelectorAll('.event-card');
  eventCards.forEach(card => {
    card.addEventListener('click', () => {
      const expanded = card.getAttribute('aria-expanded') === 'true';
      // Close all others
      eventCards.forEach(c => c.setAttribute('aria-expanded', 'false'));
      // Toggle this one
      card.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    });
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        card.click();
      }
    });
  });


  // ── ERA FILTER BUTTONS ────────────────────────────────────
  const eraButtons = document.querySelectorAll('.era-btn');
  const timelineEvents = document.querySelectorAll('.timeline-event');

  eraButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const era = btn.dataset.era;

      // Update active state
      eraButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Show/hide events
      timelineEvents.forEach(ev => {
        if (era === 'all' || ev.dataset.era === era) {
          ev.classList.remove('hidden');
        } else {
          ev.classList.add('hidden');
          // Close any open cards in hidden events
          const card = ev.querySelector('.event-card');
          if (card) card.setAttribute('aria-expanded', 'false');
        }
      });
    });
  });


  // ── SCROLL-IN ANIMATION ───────────────────────────────────
  const observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
  );

  timelineEvents.forEach((el, i) => {
    el.style.transitionDelay = Math.min(i * 0.05, 0.4) + 's';
    observer.observe(el);
  });


  // ── LEAFLET MAP ───────────────────────────────────────────
  function initMap() {
    const mapEl = document.getElementById('map-container');
    if (!mapEl || typeof L === 'undefined') return;

    const map = L.map('map-container', {
      center: [37.8716, -122.2727],
      zoom: 14,
      scrollWheelZoom: false,
      zoomControl: true,
    });
    window._leafletMap = map;

    // OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Custom marker factory
    function makeMarker(color, large) {
      const size = large ? 18 : 14;
      return L.divIcon({
        className: '',
        html: `<div style="width:${size}px;height:${size}px;background:${color};border-radius:50%;border:3px solid rgba(255,255,255,0.9);box-shadow:0 2px 8px rgba(0,0,0,0.4);"></div>`,
        iconSize: [size, size],
        iconAnchor: [size/2, size/2],
      });
    }

    const COLORS = {
      exclusion: '#c47ab0',
      arrival: '#5aae78',
      empire: '#e8840a',
      reckoning: '#e05050',
      bagai: '#4a90d9',
    };

    // LOCATIONS
    const locations = [
      {
        lat: 37.8559,
        lng: -122.2478,
        color: COLORS.exclusion,
        large: true,
        title: '1916 Elmwood Neighborhood',
        desc: 'First single-family zoning in the United States. Duncan McDuffie\'s development had racially restrictive deed covenants. Berkeley Ordinance No. 452 (1916) created the Class 1 zone here.',
        source: 'https://goodhumanhabitat.org/governance/racism-and-single-family-zoning/',
      },
      {
        lat: 37.8702,
        lng: -122.2680,
        color: COLORS.empire,
        large: true,
        title: 'Pasand Madras Indian Cuisine (Shattuck Ave)',
        desc: 'Lakireddy Bali Reddy\'s flagship restaurant, opened 1975. The financial engine of his real estate empire and the hub of his trafficking operation. Workers were housed in nearby apartments.',
        source: 'https://en.wikipedia.org/wiki/Lakireddy_Bali_Reddy',
      },
      {
        lat: 37.8700,
        lng: -122.2590,
        color: COLORS.arrival,
        large: true,
        title: 'International House — UC Berkeley',
        desc: 'Where Ashok Desai applied to live four days after arriving from rural India in 1967. I-House became the starting point of the entire Desai family\'s American story.',
        source: 'https://ihouse.berkeley.edu',
      },
      {
        lat: 37.8702,
        lng: -122.2680,
        color: COLORS.bagai,
        large: false,
        title: 'Kala Bagai Way (Shattuck Ave)',
        desc: 'A two-block stretch of Shattuck Avenue renamed in 2020 to honor Kala Bagai, one of the first South Asian women in the US. She arrived in 1915 and was later locked out of her Berkeley home by racist neighbors. Ironically, the same street as Reddy\'s restaurant.',
        source: 'https://indiacurrents.com/kala-bagai-way-the-first-street-in-the-us-named-after-a-historic-indian-american-woman/',
      },
      {
        lat: 37.8716,
        lng: -122.2727,
        color: COLORS.reckoning,
        large: false,
        title: 'Berkeley City Hall',
        desc: 'Site of the 1916 zoning vote that created exclusionary single-family zoning. In 2021, the City Council passed a resolution here to end that same exclusionary zoning — 105 years later.',
        source: 'https://berkeleyca.gov',
      },
      {
        lat: 37.8625,
        lng: -122.2680,
        color: COLORS.reckoning,
        large: false,
        title: 'Berkeley High School',
        desc: 'Home of the Jacket student newspaper, whose reporters broke the Lakireddy Bali Reddy trafficking story in 1999-2000 — triggering the federal investigation that led to his arrest. They won the "Journalist of the Year" award.',
        source: 'https://en.wikipedia.org/wiki/Berkeley_High_Jacket',
      },
      {
        lat: 37.8690,
        lng: -122.2630,
        color: COLORS.empire,
        large: false,
        title: 'UC Berkeley Campus',
        desc: 'Where Lakireddy Bali Reddy arrived as an engineering student in 1960. Also where Ashok Desai enrolled in 1967, and where the South Asian student community has been active since 1904.',
        source: 'https://en.wikipedia.org/wiki/University_of_California,_Berkeley',
      },
    ];

    locations.forEach(loc => {
      const marker = L.marker([loc.lat, loc.lng], { icon: makeMarker(loc.color, loc.large) });
      marker.addTo(map);

      const popupContent = `
        <div style="font-family: 'Switzer', sans-serif; max-width: 240px;">
          <div style="font-weight:700; font-size:13px; margin-bottom:4px; line-height:1.3; color:#1a1510;">${loc.title}</div>
          <div style="font-size:12px; color:#5c5040; line-height:1.55; margin-bottom:6px;">${loc.desc}</div>
          <a href="${loc.source}" target="_blank" rel="noopener" style="font-size:11px;font-weight:600;color:#b85e00;text-decoration:none;">Source ↗</a>
        </div>
      `;
      marker.bindPopup(popupContent, { maxWidth: 260 });
    });

    // Add era polygon for Elmwood zoning district (rough bounds)
    const elmwoodBounds = [
      [37.8530, -122.2530],
      [37.8530, -122.2420],
      [37.8600, -122.2420],
      [37.8600, -122.2530],
    ];
    L.polygon(elmwoodBounds, {
      color: COLORS.exclusion,
      fillColor: COLORS.exclusion,
      fillOpacity: 0.08,
      weight: 2,
      dashArray: '6 4',
    }).addTo(map).bindPopup('<strong style="font-size:12px;">Elmwood District</strong><br><span style="font-size:11px;color:#5c5040;">First single-family zone in the US (1916 Ordinance No. 452). Duncan McDuffie\'s development with racially restrictive deed covenants.</span>');
  }

  // Wait for Leaflet to load
  if (typeof L !== 'undefined') {
    initMap();
  } else {
    document.addEventListener('DOMContentLoaded', initMap);
    window.addEventListener('load', initMap);
  }


  // ── STICKY NAV SCROLL BEHAVIOR ───────────────────────────
  let lastScrollY = window.scrollY;
  const nav = document.getElementById('site-nav');
  window.addEventListener('scroll', () => {
    const currentY = window.scrollY;
    if (currentY > 80) {
      nav.style.boxShadow = '0 2px 16px rgba(0,0,0,0.1)';
    } else {
      nav.style.boxShadow = '';
    }
    lastScrollY = currentY;
  }, { passive: true });

})();
