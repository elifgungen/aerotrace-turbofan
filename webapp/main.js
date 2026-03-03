/* ═══════════════════════════════════════════════════════
   AeroTrace — Main Application
   ═══════════════════════════════════════════════════════ */

// ── Brand Constants (UI text only) ──
const PRODUCT_NAME = 'AeroTrace';
const COMPANY_NAME = 'AeroLith Systems';

// ── State ──
let fleetData = null;
let currentPage = 'intro';
let selectedEngine = null;
let engineTimeline = null;
let selectedCycle = null;
let activeDataset = 'FD001';
let datasetsManifest = null;
let autoPlayInterval = null;

// Label helpers
const LABELS = ['Normal Operation', 'Enhanced Monitoring', 'Planned Maintenance', 'Immediate Maintenance'];
const LABEL_CSS = { 'Normal Operation': 'normal', 'Enhanced Monitoring': 'enhanced', 'Planned Maintenance': 'planned', 'Immediate Maintenance': 'immediate' };
const LABEL_COLORS = { 'Normal Operation': '#16a34a', 'Enhanced Monitoring': '#d97706', 'Planned Maintenance': '#ea580c', 'Immediate Maintenance': '#dc2626' };
const LABEL_ICONS = { 'Normal Operation': '●', 'Enhanced Monitoring': '●', 'Planned Maintenance': '●', 'Immediate Maintenance': '●' };
const LABEL_ACTIONS = { 'Normal Operation': 'Rutin izleme', 'Enhanced Monitoring': 'İzleme sıklığını artır', 'Planned Maintenance': 'Bakım planla', 'Immediate Maintenance': 'Acil müdahale gerekli' };
const LABEL_TR = { 'Normal Operation': 'Normal', 'Enhanced Monitoring': 'İzleme', 'Planned Maintenance': 'Planlı Bakım', 'Immediate Maintenance': 'Acil İnceleme' };

const PLOTLY_LAYOUT_BASE = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: '#ffffff',
  font: { family: 'Inter, sans-serif', color: '#4b5563', size: 12 },
  margin: { t: 30, r: 60, b: 50, l: 60 },
  xaxis: { gridcolor: 'rgba(0,0,0,0.05)', zerolinecolor: 'rgba(0,0,0,0.05)' },
  yaxis: { gridcolor: 'rgba(0,0,0,0.05)', zerolinecolor: 'rgba(0,0,0,0.05)' },
};

const PLOTLY_CONFIG = { displayModeBar: false, responsive: true };

// ── Data Loading ──
async function loadDatasetsManifest() {
  if (datasetsManifest) return datasetsManifest;
  const res = await fetch('./data/datasets.json');
  datasetsManifest = await res.json();
  return datasetsManifest;
}

async function loadFleetData(datasetId) {
  if (datasetId) activeDataset = datasetId;
  const path = `./data/${activeDataset}/fleet_summary.json`;
  const res = await fetch(path);
  fleetData = await res.json();
  // Compute labelDistribution from fleet summary if not present
  if (!fleetData.labelDistribution) {
    const dist = {};
    (fleetData.engines || []).forEach(e => { dist[e.label] = (dist[e.label] || 0) + 1; });
    fleetData.labelDistribution = dist;
    fleetData.totalEngines = fleetData.totalEngines || fleetData.engines.length;
    fleetData.totalCycles = fleetData.totalCycles || fleetData.engines.reduce((s, e) => s + e.maxCycle, 0);
  }
  return fleetData;
}

async function loadEngineTimeline(engineId) {
  const res = await fetch(`./data/${activeDataset}/engines/engine_${engineId}.json`);
  engineTimeline = await res.json();
  return engineTimeline;
}

function getDatasetLabel() {
  if (!datasetsManifest) return activeDataset;
  const ds = datasetsManifest.find(d => d.id === activeDataset);
  return ds ? ds.label : activeDataset;
}

// ── Router ──
const ALLOWED_PAGES = new Set(['intro', 'landing', 'fleet', 'motor', 'twin', 'audit']);
let _skipPush = false; // flag to avoid double-push on popstate

function navigateTo(page, params = {}) {
  if (autoPlayInterval) { clearInterval(autoPlayInterval); autoPlayInterval = null; }
  currentPage = page;
  document.querySelectorAll('.nav-link').forEach(l => l.classList.toggle('active', l.dataset.page === page));

  // Show/hide sidebar + main-content margin for intro page
  const sidebar = document.querySelector('.sidebar');
  const main = document.querySelector('.main-content');
  const breadcrumb = document.getElementById('breadcrumb');
  if (page === 'intro') {
    sidebar.style.display = 'none';
    main.style.marginLeft = '0';
    if (breadcrumb) breadcrumb.style.display = 'none';
  } else {
    sidebar.style.display = '';
    main.style.marginLeft = '';
    if (breadcrumb) breadcrumb.style.display = '';
  }

  // Push history state for back/forward support
  const hashTarget = '#' + page;
  if (!_skipPush && location.hash !== hashTarget) {
    history.pushState({ page, params }, '', hashTarget);
  }

  renderPage(page, params);
}

function renderPage(page, params = {}) {
  const container = document.getElementById('page-container');

  // Skeleton loader — varies by page type
  const skeletons = {
    landing: `<div class="skeleton-loader">
      <div class="sk-block sk-hero"></div>
      <div class="sk-row"><div class="sk-block sk-card"></div><div class="sk-block sk-card"></div><div class="sk-block sk-card"></div><div class="sk-block sk-card"></div></div>
      <div class="sk-block sk-chart"></div>
    </div>`,
    fleet: `<div class="skeleton-loader">
      <div class="sk-row"><div class="sk-block sk-chart"></div><div class="sk-block sk-chart-sm"></div></div>
      <div class="sk-block sk-table"></div>
    </div>`,
    motor: `<div class="skeleton-loader">
      <div class="sk-block sk-chart-wide"></div>
      <div class="sk-row"><div class="sk-block sk-panel"></div><div class="sk-block sk-panel"></div></div>
    </div>`,
    twin: `<div class="skeleton-loader">
      <div class="sk-block sk-3d"></div>
      <div class="sk-row"><div class="sk-block sk-bar"></div><div class="sk-block sk-bar"></div><div class="sk-block sk-bar"></div></div>
    </div>`,
    audit: `<div class="skeleton-loader">
      <div class="sk-row"><div class="sk-block sk-panel"></div><div class="sk-block sk-panel"></div></div>
      <div class="sk-row"><div class="sk-block sk-panel"></div><div class="sk-block sk-panel"></div></div>
    </div>`,
  };
  container.innerHTML = skeletons[page] || skeletons.landing;

  switch (page) {
    case 'intro': renderIntro(container); break;
    case 'landing': renderLanding(container); break;
    case 'fleet': renderFleet(container); break;
    case 'motor': renderMotor(container, params.engineId || 1); break;
    case 'twin': renderTwin(container, params.engineId || selectedEngine || 1); break;
    case 'audit': renderAudit(container); break;
    default: renderIntro(container); currentPage = 'intro'; break;
  }
  updateBreadcrumb(page, params);
}

function updateBreadcrumb(page, params) {
  const bc = document.getElementById('breadcrumb');
  const items = [{ label: PRODUCT_NAME, page: 'landing' }];
  if (page === 'fleet') items.push({ label: 'Filo Görünümü', page: 'fleet' });
  if (page === 'motor') {
    items.push({ label: 'Filo Görünümü', page: 'fleet' });
    items.push({ label: `Motor #${params.engineId || selectedEngine || 1}`, page: 'motor' });
  }
  if (page === 'twin') {
    items.push({ label: 'Filo Görünümü', page: 'fleet' });
    items.push({ label: `Motor #${params.engineId || selectedEngine || 1}`, page: 'motor' });
    items.push({ label: '3D Twin', page: 'twin' });
  }
  if (page === 'audit') items.push({ label: 'Audit & Kanıt', page: 'audit' });

  bc.innerHTML = items.map((item, i) => {
    if (i === items.length - 1) return `<span class="breadcrumb-current">${item.label}</span>`;
    return `<span class="breadcrumb-item" data-page="${item.page}">${item.label}</span><span class="breadcrumb-sep">›</span>`;
  }).join('');

  bc.querySelectorAll('.breadcrumb-item').forEach(el => {
    el.addEventListener('click', () => navigateTo(el.dataset.page, { engineId: selectedEngine }));
  });
}

// ═══════════════════════════════════════════════════════
// PRODUCT INTRODUCTION PAGE
// ═══════════════════════════════════════════════════════
function renderIntro(container) {
  container.innerHTML = `
    <div class="intro-page fade-in">

      <!-- Header / Navbar -->
      <header class="intro-header">
        <div class="intro-header-inner">
          <a href="#" class="intro-header-logo">
            <img src="./logo-main.png" alt="AeroTrace" />
          </a>
          <button class="intro-hamburger" id="intro-hamburger" aria-label="Menü">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          </button>
          <nav class="intro-nav" id="intro-nav">
            <a href="#intro-about" class="intro-nav-link">Ne Yapıyoruz</a>
            <a href="#intro-pipeline" class="intro-nav-link">MVP Akışı</a>
            <a href="#intro-transparency" class="intro-nav-link">Şeffaflık</a>
            <button class="intro-nav-cta" id="intro-header-demo">Jüri Demo</button>
          </nav>
        </div>
      </header>

      <!-- Hero Section — 2 Column -->
      <section class="intro-hero" id="intro-about">
        <div class="intro-hero-cols">
          <!-- Left Column: Text + CTAs -->
          <div class="intro-hero-left">
            <h1 class="intro-hero-h1">Turbofan MRO için<br/><span class="nowrap">insan-onaylı</span><br/>kestirimci bakım karar desteği</h1>
            <p class="intro-hero-desc">Her çevrim için bakım önerisini gerekçesiyle birlikte üreten ve <span class="mono">policy_version</span>/<span class="mono">run_id</span>/eşikler gibi audit alanlarıyla izlenebilir kılan, insan-onaylı karar destek sistemi.</p>
            <p class="intro-brand-lockup">${PRODUCT_NAME} <span>by</span> ${COMPANY_NAME}</p>
            <ul class="intro-hero-outputs">
              <li><strong>RUL &amp; anomali skoru</strong> <span class="intro-output-dim">— cycle bazlı, EMA smoothed</span></li>
              <li><strong>4 seviyeli karar etiketi</strong> <span class="intro-output-dim">— Normal · İzle · Planla · Acil</span></li>
              <li><strong>Gerekçe + audit alanları</strong> <span class="intro-output-dim">— reason codes, eşikler, sürüm</span></li>
            </ul>
            <div class="intro-hero-actions">
              <button class="intro-cta-primary" id="intro-start-demo">Jüri Demo'yu Başlat <span class="arrow">→</span></button>
              <button class="intro-cta-secondary" id="intro-enter-dashboard">Dashboard'a Gir</button>
            </div>
            <p class="intro-cta-note">3 dakikada: veri → RUL/anomali → etiket + açıklama</p>
          </div>

          <!-- Right Column: Product Shot Card -->
          <div class="intro-hero-right">
            <div class="intro-product-card">
              <div class="intro-product-card-header">Örnek Karar <span class="mono">(Cycle 128)</span></div>
              <div class="intro-product-card-body">
                <div class="intro-product-row">
                  <span class="intro-product-label">RUL:</span>
                  <span class="mono intro-product-value">42 cycle</span>
                </div>
                <div class="intro-product-row">
                  <span class="intro-product-label">Anomali:</span>
                  <span class="mono intro-product-value">0.18 <span class="intro-product-dim">(smoothed)</span></span>
                </div>
                <div class="intro-product-row">
                  <span class="intro-product-label">Etiket:</span>
                  <span class="intro-product-value intro-product-tag-planned">Planlı Bakım</span>
                </div>
                <div class="intro-product-row">
                  <span class="intro-product-label">Reason:</span>
                  <span class="mono intro-product-value">RUL_LOW | ANOM_ON</span>
                </div>
              </div>
              <div class="intro-product-card-footer">
                <span>Top 3 sinyal: <span class="mono">s7, s12, s15</span></span>
              </div>
              <div class="intro-product-card-audit">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l7 4v6c0 5-3.5 9.5-7 10-3.5-.5-7-5-7-10V6l7-4z"/><path d="M9 12l2 2 4-4"/></svg>
                <span>audit fields: <span class="mono">policy_version, run_id, thresholds</span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Badge Row — below both columns -->
        <div class="intro-proof-row intro-proof-row-main" aria-label="Kanıt ve güven satırı">
          <span class="intro-proof-badge">11 Senaryo • C-MAPSS + N-CMAPSS</span>
          <span class="intro-proof-badge">Human-in-the-loop • Otonom karar yok</span>
          <span class="intro-proof-badge">Açıklanabilir etiket • Audit alanları</span>
        </div>
      </section>

      <!-- MVP Pipeline -->
      <section class="intro-section intro-section-pipeline" id="intro-pipeline">
        <h2 class="intro-section-title">MVP Akışı</h2>
        <div class="intro-pipeline">
          <div class="intro-pipe-step">
            <div class="intro-pipe-num">1</div>
            <div class="intro-pipe-label">Veri Toplama</div>
            <div class="intro-pipe-desc">21 sensör × her uçuş çevrimi<br/>C-MAPSS (FD001–FD004) + N-CMAPSS (DS01–DS07)<br/><span class="intro-pipe-examples"><strong>Çıktı:</strong> sensör zaman serisi</span></div>
          </div>
          <div class="intro-pipe-connector"></div>
          <div class="intro-pipe-step">
            <div class="intro-pipe-num">2</div>
            <div class="intro-pipe-label">Ön İşleme</div>
            <div class="intro-pipe-desc">Kayan pencere özellik<br/>mühendisliği, normalizasyon<br/><span class="intro-pipe-examples"><strong>Çıktı:</strong> feature set + normalize</span></div>
          </div>
          <div class="intro-pipe-connector"></div>
          <div class="intro-pipe-step">
            <div class="intro-pipe-num">3</div>
            <div class="intro-pipe-label">Sağlık Skoru: RUL + Anomali Sinyali</div>
            <div class="intro-pipe-desc">Gradient Boosting tabanlı RUL tahmini<br/>Z-score sapma analizi<br/><span class="intro-pipe-examples"><strong>Çıktı:</strong> RUL + anomali puanı</span></div>
          </div>
          <div class="intro-pipe-connector"></div>
          <div class="intro-pipe-step">
            <div class="intro-pipe-num">4</div>
            <div class="intro-pipe-label">Karar Etiketi</div>
            <div class="intro-pipe-desc">4 seviyeli bakım önerisi<br/>+ XAI açıklama<br/><span class="intro-pipe-examples">Normal / İzle / Planla / Acil İncele</span><br/><span class="intro-pipe-examples"><strong>Çıktı:</strong> etiket + açıklama + önerilen aksiyon</span></div>
          </div>
        </div>
      </section>

      <!-- Transparency -->
      <section class="intro-section" id="intro-transparency">
        <h2 class="intro-section-title">Şeffaflık &amp; Kapsam</h2>
        <div class="intro-trans-grid">
          <div class="intro-trans-card">
            <div class="intro-trans-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            </div>
            <h4>MVP / PoC Gösterimi</h4>
            <p>Açık veri ve simülasyon ortamında çalışan kavram ispatı. Gerçek operasyonel veriye entegrasyon sonraki aşama.</p>
          </div>
          <div class="intro-trans-card">
            <div class="intro-trans-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><path d="M20 8v6M23 11h-6"/></svg>
            </div>
            <h4>Nihai Karar İnsanda</h4>
            <p>Sistem otonom bakım kararı vermez. Karar desteği sunar; nihai onay bakım mühendisinde kalır.</p>
          </div>
          <div class="intro-trans-card">
            <div class="intro-trans-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
            </div>
            <h4>Ayarlanabilir Eşikler</h4>
            <p>Mevcut eşikler demo varsayılanıdır. Operasyonel gereksinime göre bakım ekibi tarafından ayarlanabilir.</p>
          </div>
          <div class="intro-trans-card">
            <div class="intro-trans-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
            </div>
            <h4>Kapsam &amp; Limitler</h4>
            <p>PoC verisi ve simülasyon üzerinde çalışır; operasyonel entegrasyon sonraki fazdır.</p>
          </div>
          <div class="intro-trans-card">
            <div class="intro-trans-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l7 4v6c0 5-3.5 9.5-7 10-3.5-.5-7-5-7-10V6l7-4z"/><path d="M9 12l2 2 4-4"/></svg>
            </div>
            <h4>Veri &amp; Güvenlik</h4>
            <p>Rol bazlı erişim ve anonimizasyon prensipleriyle ilerler; PoC aşamasında OEM verisi gerektirmez.</p>
          </div>
          <div class="intro-trans-card">
            <div class="intro-trans-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            </div>
            <h4>Politika Versiyonu &amp; İzlenebilirlik</h4>
            <p>Eşik/politikalar versiyonlanır; her karar run_id/policy_version ile geriye dönük izlenebilir.</p>
          </div>
        </div>
      </section>

      <!-- Footer -->
      <footer class="intro-footer">
        <div class="intro-footer-left">${PRODUCT_NAME} — Decision-Support Digital Twin for Turbofan MRO</div>
        <div class="intro-footer-credit">by ${COMPANY_NAME}</div>
        <div class="intro-footer-right">
          <button class="intro-footer-demo" id="intro-footer-demo">Jüri Demo</button>
          <span class="intro-footer-sep">·</span>
          <span>Teknik Dokümantasyon</span>
        </div>
        <div class="intro-footer-copy">© 2026</div>
      </footer>
    </div>
  `;

  // Smooth scroll for nav links
  container.querySelectorAll('.intro-nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const target = document.querySelector(link.getAttribute('href'));
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // Close mobile menu after nav click
      const nav = document.getElementById('intro-nav');
      if (nav) nav.classList.remove('open');
    });
  });

  // Hamburger toggle for mobile
  const hamburger = document.getElementById('intro-hamburger');
  const nav = document.getElementById('intro-nav');
  if (hamburger && nav) {
    hamburger.addEventListener('click', () => nav.classList.toggle('open'));
  }

  // CTAs
  document.getElementById('intro-enter-dashboard').addEventListener('click', () => navigateTo('landing'));
  document.getElementById('intro-header-demo').addEventListener('click', () => {
    navigateTo('landing');
    setTimeout(() => startDemo(), 500);
  });
  document.getElementById('intro-start-demo').addEventListener('click', () => {
    navigateTo('landing');
    setTimeout(() => startDemo(), 500);
  });
  // Footer demo button
  document.getElementById('intro-footer-demo').addEventListener('click', () => {
    navigateTo('landing');
    setTimeout(() => startDemo(), 500);
  });

  // Logo click → safe navigate to intro
  const logoLink = container.querySelector('.intro-header-logo');
  if (logoLink) {
    logoLink.addEventListener('click', (e) => {
      e.preventDefault();
      navigateTo('intro');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
}

// ═══════════════════════════════════════════════════════
// LANDING PAGE
// ═══════════════════════════════════════════════════════
async function renderLanding(container) {
  await loadDatasetsManifest();
  if (!fleetData) await loadFleetData();
  const d = fleetData;
  const dist = d.labelDistribution;
  const total = d.totalEngines;

  // Build dataset selector options
  const dsOptions = (datasetsManifest || []).map(ds =>
    `<option value="${ds.id}" ${ds.id === activeDataset ? 'selected' : ''}>${ds.label} (${ds.engines} motor)</option>`
  ).join('');

  container.innerHTML = `
    <div class="fade-in" >
      <!--Hero -->
      <section class="hero">
        <h1 class="hero-title">Motorun ne zaman bakıma gireceğini,<br/><span class="gradient-text">motor söyler.</span></h1>
        <p class="hero-subtitle">Her uçuş çevrimi için <strong>RUL</strong> ve <strong>anomali sinyalini</strong> birleştirip operasyonel aksiyon önerisi üreten dijital ikiz karar destek sistemi.</p>
        <button class="hero-cta" id="cta-fleet">Filoyu Gör <span class="arrow">→</span></button>
        <div class="stat-strip">
          <div class="stat-item">
            <div class="stat-value">11</div>
            <div class="stat-label">Senaryo</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">${total}</div>
            <div class="stat-label">Motor</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">${d.totalCycles.toLocaleString('tr-TR')}</div>
            <div class="stat-label">Çevrim</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">4</div>
            <div class="stat-label">Karar Seviyesi</div>
          </div>
        </div>
        <div class="dataset-selector-row">
          <label class="dataset-selector-label">Aktif Senaryo:</label>
          <select class="dataset-selector" id="dataset-select">${dsOptions}</select>
        </div>
      </section>

      <!--Decision Cards-->
      <div class="section-title">Karar Seviyeleri</div>
      <div class="decision-cards">
        ${LABELS.map(label => {
    const css = LABEL_CSS[label];
    const count = dist[label] || 0;
    const pct = ((count / total) * 100).toFixed(0);
    return `
            <div class="decision-card ${css}">
              <div class="card-icon">${LABEL_ICONS[label]}</div>
              <div class="card-label">${label}</div>
              <div class="card-count">${count}</div>
              <div class="card-percent">filonun %${pct}'${pct > 1 ? 'i' : 'ü'}</div>
              <div class="card-action">${LABEL_ACTIONS[label]}</div>
            </div>`;
  }).join('')}
      </div>

      <!--Pipeline -->
      <div class="pipeline-section">
        <div class="section-title">Nasıl Çalışır?</div>
        <div class="pipeline">
          <div class="pipeline-step">
            <div class="step-icon">1</div>
            <div class="step-title">Sensör Verisi</div>
            <div class="step-detail">21 sensör · cycle bazlı</div>
          </div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step">
            <div class="step-icon">2</div>
            <div class="step-title">RUL + Anomali</div>
            <div class="step-detail">Baseline Deviation · EMA</div>
          </div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step">
            <div class="step-icon">3</div>
            <div class="step-title">Karar Etiketi</div>
            <div class="step-detail">4 seviyeli policy v2</div>
          </div>
        </div>
      </div>

      <!--Trust Strip-->
      <div class="trust-strip">
        <div class="trust-item"><span class="trust-check">✓</span> Leakage-Safe Pipeline</div>
        <div class="trust-item"><span class="trust-check">✓</span> Audit Trail (Config Hash)</div>
        <div class="trust-item"><span class="trust-check">✓</span> Tek Kaynak Eşik Yönetimi</div>
        <div class="trust-item"><span class="trust-check">✓</span> 0 Duplicate · 0 NaN</div>
        <div class="trust-item"><span class="trust-check">✓</span> Train-Only Fit</div>
        <div class="trust-item"><span class="trust-check">✓</span> Reproducible</div>
      </div>

      <!--Fleet Preview-->
    <div class="fleet-preview">
      <div class="section-title">Filo Önizleme — RUL'a Göre Sıralı Motorlar</div>
      <div class="fleet-preview-chart" id="fleet-preview-chart"></div>
      <div class="fleet-preview-link"><a id="link-fleet-detail">Detaylı analize geç →</a></div>
    </div>
    </div>
    `;

  // Events
  document.getElementById('cta-fleet').addEventListener('click', () => navigateTo('fleet'));
  document.getElementById('link-fleet-detail').addEventListener('click', () => navigateTo('fleet'));

  // Dataset selector
  const dsSelect = document.getElementById('dataset-select');
  if (dsSelect) {
    dsSelect.addEventListener('change', async (e) => {
      const newId = e.target.value;
      fleetData = null; // force reload
      await loadFleetData(newId);
      navigateTo('landing');
    });
  }

  // Fleet Preview Bar Chart
  const sorted = [...d.engines].sort((a, b) => a.rul - b.rul);
  const colors = sorted.map(e => LABEL_COLORS[e.label]);

  Plotly.newPlot('fleet-preview-chart', [{
    x: sorted.map(e => `#${e.id} `),
    y: sorted.map(e => e.rul),
    type: 'bar',
    marker: { color: colors, line: { color: 'rgba(0,0,0,0.2)', width: 0.5 } },
    hovertemplate: 'Motor %{x}<br>RUL: %{y:.1f}<br>%{customdata}<extra></extra>',
    customdata: sorted.map(e => e.label),
  }], {
    ...PLOTLY_LAYOUT_BASE,
    xaxis: { ...PLOTLY_LAYOUT_BASE.xaxis, title: 'Motor', tickangle: -45, tickfont: { size: 9 } },
    yaxis: { ...PLOTLY_LAYOUT_BASE.yaxis, title: 'RUL (Remaining Useful Life)' },
    margin: { t: 10, r: 20, b: 80, l: 60 },
    height: 300,
    shapes: [{
      type: 'line', x0: -0.5, x1: sorted.length - 0.5, y0: 30, y1: 30,
      line: { color: 'rgba(239,68,68,0.5)', width: 1.5, dash: 'dash' }
    }],
    annotations: [{
      x: sorted.length - 1, y: 30, text: 'θ_RUL = 30', showarrow: false,
      font: { size: 10, color: '#ef4444' }, yshift: 12
    }]
  }, PLOTLY_CONFIG);
}

// ═══════════════════════════════════════════════════════
// FLEET OVERVIEW
// ═══════════════════════════════════════════════════════
let fleetFilter = 'all';

async function renderFleet(container) {
  if (!fleetData) await loadFleetData();
  const d = fleetData;
  const dist = d.labelDistribution;
  const immCount = dist['Immediate Maintenance'] || 0;
  const planCount = dist['Planned Maintenance'] || 0;

  container.innerHTML = `
    <div class="fade-in" >
      <div class="fleet-header">
        <h2>Filo Görünümü — ${d.totalEngines} Motor <span class="dataset-chip">${getDatasetLabel()}</span></h2>
        <div class="fleet-filters">
          <button class="filter-btn active" data-filter="all">Tümü (${d.totalEngines})</button>
          <button class="filter-btn" data-filter="Immediate Maintenance">Acil (${immCount})</button>
          <button class="filter-btn" data-filter="Planned Maintenance">Planlı (${planCount})</button>
          <button class="filter-btn" data-filter="Enhanced Monitoring">İzleme (${dist['Enhanced Monitoring'] || 0})</button>
          <button class="filter-btn" data-filter="Normal Operation">Normal (${dist['Normal Operation'] || 0})</button>
        </div>
      </div>

      ${immCount > 0 ? `
      <div class="critical-banner">
        <div class="banner-icon">!</div>
        <div class="banner-text">
          <strong>${immCount} motor</strong> acil bakım gerektiriyor.
          ${planCount > 0 ? `<strong>${planCount} motor</strong> planlı bakım aşamasında.` : ''}
        </div>
      </div>` : ''
    }

      <div class="fleet-grid">
        <div class="fleet-risk-chart">
          <div class="detail-panel-title">Risk Matrisi — Anomaly vs RUL</div>
          <div id="risk-matrix-chart" style="height:370px;"></div>
        </div>
        <div class="fleet-distribution">
          <div class="detail-panel-title">Karar Dağılımı</div>
          <div id="distribution-chart" style="height:370px;"></div>
        </div>
      </div>

      <div class="engine-table-container">
        <table class="engine-table">
          <thead>
            <tr>
              <th data-sort="id">Motor ID ↕</th>
              <th data-sort="rul">RUL ↕</th>
              <th data-sort="anomSmooth">Anomaly ↕</th>
              <th data-sort="label">Durum ↕</th>
              <th data-sort="cycles">Çevrim ↕</th>
              <th>Ana Sorun</th>
              <th>Aksiyon</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="engine-tbody"></tbody>
        </table>
      </div>
    </div>
    `;

  // Filters
  container.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      fleetFilter = btn.dataset.filter;
      renderFleetTable(d.engines);
    });
  });

  // Sorting
  let sortKey = 'rul';
  let sortDir = 1;
  container.querySelectorAll('th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if (sortKey === key) sortDir *= -1;
      else { sortKey = key; sortDir = 1; }
      renderFleetTable(d.engines, sortKey, sortDir);
    });
  });

  renderFleetTable(d.engines);
  renderRiskMatrix(d.engines);
  renderDistribution(d.labelDistribution);
}

function renderFleetTable(engines, sortKey = 'rul', sortDir = 1) {
  let filtered = fleetFilter === 'all' ? engines : engines.filter(e => e.label === fleetFilter);
  filtered = [...filtered].sort((a, b) => {
    const va = a[sortKey], vb = b[sortKey];
    if (typeof va === 'string') return sortDir * va.localeCompare(vb);
    return sortDir * (va - vb);
  });

  const tbody = document.getElementById('engine-tbody');
  tbody.innerHTML = filtered.map(e => {
    const css = LABEL_CSS[e.label];
    const topSensor = e.topSensor || '—';
    const topSensorClass = e.topSensor ? 'fleet-top-sensor' : '';
    return `
    <tr data-engine="${e.id}">
        <td><strong>#${e.id}</strong></td>
        <td class="mono">${e.rul.toFixed(1)}</td>
        <td class="mono">${e.anomSmooth.toFixed(3)}</td>
        <td><span class="status-badge ${css}"><span class="status-dot ${css}"></span>${e.label}</span></td>
        <td class="mono">${e.maxCycle || e.cycles}</td>
        <td><span class="${topSensorClass}">${topSensor}</span></td>
        <td style="font-size:0.78rem;color:var(--text-secondary);">${LABEL_ACTIONS[e.label]}</td>
        <td><button class="btn-view-detail" data-engine="${e.id}">Detay →</button></td>
      </tr>`;
  }).join('');

  tbody.querySelectorAll('tr').forEach(tr => {
    tr.addEventListener('click', () => {
      const eid = parseInt(tr.dataset.engine);
      selectedEngine = eid;
      navigateTo('motor', { engineId: eid });
    });
  });
}

function renderRiskMatrix(engines) {
  const traces = LABELS.map(label => {
    const group = engines.filter(e => e.label === label);
    return {
      x: group.map(e => e.anomSmooth),
      y: group.map(e => e.rul),
      text: group.map(e => `Motor #${e.id} `),
      name: label,
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: LABEL_COLORS[label],
        size: 10,
        opacity: 0.85,
        line: { color: 'rgba(0,0,0,0.3)', width: 1 }
      },
      hovertemplate: '%{text}<br>Anomaly: %{x:.3f}<br>RUL: %{y:.1f}<extra>%{fullData.name}</extra>',
    };
  });

  Plotly.newPlot('risk-matrix-chart', traces, {
    ...PLOTLY_LAYOUT_BASE,
    xaxis: { ...PLOTLY_LAYOUT_BASE.xaxis, title: 'Anomaly Score (smoothed)' },
    yaxis: { ...PLOTLY_LAYOUT_BASE.yaxis, title: 'RUL' },
    showlegend: true,
    legend: { orientation: 'h', y: -0.2, font: { size: 10 } },
    margin: { t: 10, r: 20, b: 70, l: 60 },
    shapes: [
      { type: 'line', x0: 0, x1: 1, y0: 30, y1: 30, line: { color: 'rgba(239,68,68,0.4)', width: 1, dash: 'dash' } },
    ],
  }, PLOTLY_CONFIG);
}

function renderDistribution(dist) {
  Plotly.newPlot('distribution-chart', [{
    values: LABELS.map(l => dist[l] || 0),
    labels: LABELS,
    type: 'pie',
    hole: 0.55,
    marker: { colors: LABELS.map(l => LABEL_COLORS[l]) },
    textinfo: 'value+percent',
    textfont: { size: 12, color: '#f1f5f9' },
    hovertemplate: '%{label}<br>%{value} motor (%{percent})<extra></extra>',
  }], {
    ...PLOTLY_LAYOUT_BASE,
    showlegend: true,
    legend: { orientation: 'h', y: -0.1, font: { size: 10 } },
    margin: { t: 10, r: 10, b: 50, l: 10 },
    annotations: [{ text: 'Karar<br>Dağılımı', showarrow: false, font: { size: 13, color: '#94a3b8' } }],
  }, PLOTLY_CONFIG);
}

// ═══════════════════════════════════════════════════════
// MOTOR DETAIL
// ═══════════════════════════════════════════════════════
async function renderMotor(container, engineId) {
  if (!fleetData) await loadFleetData();
  selectedEngine = engineId;
  const timeline = await loadEngineTimeline(engineId);
  const engineSummary = fleetData.engines.find(e => e.id === engineId);
  if (!timeline || !engineSummary) {
    container.innerHTML = '<p>Motor bulunamadı.</p>';
    return;
  }

  const last = timeline[timeline.length - 1];
  const css = LABEL_CSS[last.label];
  const maxCycle = last.t;
  selectedCycle = maxCycle;

  // Compute transitions
  const transitions = [];
  let prev = timeline[0].label;
  for (let i = 1; i < timeline.length; i++) {
    if (timeline[i].label !== prev) {
      transitions.push({ cycle: timeline[i].t, from: prev, to: timeline[i].label });
      prev = timeline[i].label;
    }
  }

  container.innerHTML = `
    <div class="fade-in" >
      <div class="motor-header">
        <div class="motor-header-left">
          <h2>Motor #${engineId} <span class="dataset-chip">${getDatasetLabel()}</span></h2>
        </div>
        <div class="motor-header-right">
          <button class="btn-3d-twin" id="btn-goto-twin">3D Twin Görüntüle</button>
          <div class="motor-status-large ${css}">
            ${LABEL_ICONS[last.label]} ${last.label}
          </div>
        </div>
      </div>

      <!--KPI Row-->
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-value">${last.rul.toFixed(1)}</div>
          <div class="kpi-label">RUL (Son Cycle)</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${last.anomSmooth.toFixed(3)}</div>
          <div class="kpi-label">Anomaly Score</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${maxCycle}</div>
          <div class="kpi-label">Toplam Çevrim</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${transitions.length}</div>
          <div class="kpi-label">Durum Geçişi</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${last.theta}</div>
          <div class="kpi-label">θ_RUL</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${last.alphaHigh}</div>
          <div class="kpi-label">α_high</div>
        </div>
      </div>

      <!--Cycle Scrubber-->
      <div class="cycle-scrubber">
        <label>Cycle:</label>
        <input type="range" id="cycle-slider" min="1" max="${maxCycle}" value="${maxCycle}" step="1" />
        <span class="cycle-value" id="cycle-display">${maxCycle}</span>
        <div class="scrubber-btns">
          <button class="scrubber-btn" id="btn-prev-cycle">◀</button>
          <button class="scrubber-btn" id="btn-play">▶ Play</button>
          <button class="scrubber-btn" id="btn-next-cycle">▶</button>
        </div>
      </div>

      <!--Timeline Chart-->
      <div class="detail-panel">
        <div class="detail-panel-title">Timeline — RUL & Anomaly Score</div>
        <p class="timeline-desc">Karar etiketi, RUL trendi + anomali eşiklerine göre türetilir (insan-onaylı). Arka plan renkleri mevcut karar bölgesini gösterir.</p>
        <div class="timeline-chart" id="timeline-chart"></div>
      </div>

      <!--Why Panel-->
      <div class="why-panel-xai" style="margin-top:var(--space-xl);">
        <div class="why-main-section">
          <div class="detail-panel-title">Neden Bu Karar?</div>
          <!-- Why Explanation (filled by updateMotorCycle) -->
          <div id="why-explanation-box"></div>
          <!-- Sensör Analizi -->
          <div class="sensor-insights-section" id="sensor-insights-section">
            <div class="sensor-insights-header">Sensör Analizi</div>
            <div id="sensor-cards-container"></div>
          </div>
        </div>
        <div class="why-section">
          <div class="detail-panel-title">Durum Geçişleri</div>
          <ul class="transition-list" id="transition-list">
            ${transitions.length === 0 ? '<li style="color:var(--text-muted);font-size:0.85rem;">Durum geçişi yok — tüm çevrimlerde aynı karar.</li>' :
      transitions.map(t => `
                <li class="transition-item">
                  <span class="transition-cycle">Cycle ${t.cycle}</span>
                  <span class="status-badge ${LABEL_CSS[t.from]}" style="font-size:0.7rem;">${t.from}</span>
                  <span class="transition-arrow">→</span>
                  <span class="status-badge ${LABEL_CSS[t.to]}" style="font-size:0.7rem;">${t.to}</span>
                </li>`).join('')}
          </ul>
        </div>
      </div>

      <!--Recommended Action-->
    <div class="detail-panel" style="margin-top:var(--space-xl);">
      <div class="detail-panel-title">Önerilen Aksiyon</div>
      <div id="action-text" style="font-size:0.95rem;color:var(--text-primary);font-weight:500;"></div>
    </div>
    </div>
    `;

  // Events
  document.getElementById('btn-goto-twin').addEventListener('click', () => navigateTo('twin', { engineId }));

  const slider = document.getElementById('cycle-slider');
  const display = document.getElementById('cycle-display');

  slider.addEventListener('input', () => {
    selectedCycle = parseInt(slider.value);
    display.textContent = selectedCycle;
    updateMotorCycle(timeline, selectedCycle);
  });

  document.getElementById('btn-prev-cycle').addEventListener('click', () => {
    if (selectedCycle > 1) { selectedCycle--; slider.value = selectedCycle; display.textContent = selectedCycle; updateMotorCycle(timeline, selectedCycle); }
  });
  document.getElementById('btn-next-cycle').addEventListener('click', () => {
    if (selectedCycle < maxCycle) { selectedCycle++; slider.value = selectedCycle; display.textContent = selectedCycle; updateMotorCycle(timeline, selectedCycle); }
  });

  const playBtn = document.getElementById('btn-play');
  playBtn.addEventListener('click', () => {
    if (autoPlayInterval) {
      clearInterval(autoPlayInterval);
      autoPlayInterval = null;
      playBtn.textContent = '▶ Play';
      playBtn.classList.remove('playing');
    } else {
      if (selectedCycle >= maxCycle) { selectedCycle = 1; }
      playBtn.textContent = '⏸ Stop';
      playBtn.classList.add('playing');
      autoPlayInterval = setInterval(() => {
        selectedCycle++;
        if (selectedCycle > maxCycle) {
          clearInterval(autoPlayInterval);
          autoPlayInterval = null;
          playBtn.textContent = '▶ Play';
          playBtn.classList.remove('playing');
          return;
        }
        slider.value = selectedCycle;
        display.textContent = selectedCycle;
        updateMotorCycle(timeline, selectedCycle);
      }, 80);
    }
  });

  // Render initial timeline
  renderTimeline(timeline, maxCycle);
  updateMotorCycle(timeline, maxCycle);
}

// ── Why Explanation Helper ──
function renderWhyExplanation(row) {
  const labelTr = LABEL_TR[row.label] || row.label;
  const css = LABEL_CSS[row.label];
  const rul = row.rul;
  const theta = row.theta || 30;
  const anom = row.anomSmooth;
  const alphaH = row.alphaHigh || 0.5;

  // Human-readable Turkish explanation based on label
  let explanation = '';
  if (row.label === 'Normal Operation') {
    explanation = `RUL değeri (${rul.toFixed(1)}) eşik değeri θ (${theta}) üzerinde ve anomali skoru (${anom.toFixed(3)}) düşük seyrediyor. Sistem olağan çalışma gösteriyor; herhangi bir risk sinyali yok.`;
  } else if (row.label === 'Enhanced Monitoring') {
    explanation = `RUL (${rul.toFixed(1)}) henüz kritik değil ancak anomali skoru (${anom.toFixed(3)}) yükselme eğiliminde. Erken uyarı aşaması — daha sık izleme önerilir.`;
  } else if (row.label === 'Planned Maintenance') {
    explanation = `RUL (${rul.toFixed(1)}) eşik seviyesine (θ=${theta}) yaklaşıyor veya altına düşmüş. Anomali sinyali tek başına kritik değilse planlı bakım penceresi uygundur.`;
  } else if (row.label === 'Immediate Maintenance') {
    explanation = `RUL (${rul.toFixed(1)}) eşik değerinin (θ=${theta}) altında ve anomali skoru (${anom.toFixed(3)}) yüksek (α=${alphaH}). Risk artmış — acil inceleme gerekir.`;
  }

  // Sensor insights summary (if available)
  const si = row.sensorInsights;
  const sensorNote = si && si.summary_tr ? `<p class="why-sensor-note">${si.summary_tr}</p>` : '';

  // Reason codes
  const codes = (row.reasonCodes || '').split('|').filter(Boolean);
  const codesHtml = codes.length > 0
    ? `<div class="why-codes-row"><span class="why-codes-label">Neden kodları:</span> ${codes.map(c => `<span class="reason-code-tag">${c}</span>`).join(' ')}</div>`
    : '';

  // Action
  const action = row.action || LABEL_ACTIONS[row.label] || '';

  return `
    <div class="why-structured">
      <div class="why-label-row">
        <span class="why-label-heading">Karar:</span>
        <span class="status-badge ${css}" style="font-size:0.82rem;">${row.label}</span>
        <span class="why-label-tr">(${labelTr})</span>
      </div>
      <p class="why-explanation-text">${explanation}</p>
      ${sensorNote}
      <div class="why-metric-chips">
        <span class="why-chip"><strong>RUL</strong> ${rul.toFixed(1)}</span>
        <span class="why-chip why-chip-muted"><strong>θ</strong> ${theta}</span>
        <span class="why-chip"><strong>Anomali</strong> ${anom.toFixed(3)}</span>
        <span class="why-chip why-chip-muted"><strong>α</strong> ${alphaH}</span>
      </div>
      ${codesHtml}
      <div class="why-action-row">
        <span class="why-action-label">Önerilen aksiyon:</span>
        <span class="why-action-text">${action}</span>
      </div>
    </div>
  `;
}

function renderTimeline(timeline, highlightCycle) {
  const cycles = timeline.map(r => r.t);
  const rul = timeline.map(r => r.rul);
  const anom = timeline.map(r => r.anomSmooth);

  // Dynamic thresholds from data
  const thetaRUL = timeline[0].theta || 30;
  const alphaHigh = timeline[0].alphaHigh || 0.5;

  // Decision label background shapes
  const shapes = [];
  let segStart = 0;
  let segLabel = timeline[0].label;
  const transitionPoints = []; // collect label change points
  for (let i = 1; i <= timeline.length; i++) {
    if (i === timeline.length || timeline[i].label !== segLabel) {
      const bgColor = LABEL_COLORS[segLabel];
      shapes.push({
        type: 'rect',
        xref: 'x', yref: 'paper',
        x0: timeline[segStart].t, x1: timeline[Math.min(i, timeline.length) - 1].t,
        y0: 0, y1: 1,
        fillcolor: bgColor.replace(')', ',0.08)').replace('rgb', 'rgba'),
        line: { width: 0 },
        layer: 'below',
      });
      // Collect transition points
      if (i < timeline.length) {
        transitionPoints.push({ cycle: timeline[i].t, label: timeline[i].label });
        segStart = i;
        segLabel = timeline[i].label;
      }
    }
  }

  // θ_RUL threshold line (yaxis — RUL)
  shapes.push({
    type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: thetaRUL, y1: thetaRUL,
    line: { color: 'rgba(239,68,68,0.5)', width: 1.5, dash: 'dash' }
  });

  // α_high threshold line (yaxis2 — Anomaly)
  shapes.push({
    type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y2', y0: alphaHigh, y1: alphaHigh,
    line: { color: 'rgba(249,115,22,0.45)', width: 1.5, dash: 'dot' }
  });

  // Transition marker lines
  transitionPoints.forEach(tp => {
    shapes.push({
      type: 'line', xref: 'x', x0: tp.cycle, x1: tp.cycle, yref: 'paper', y0: 0, y1: 1,
      line: { color: 'rgba(100,116,139,0.3)', width: 1, dash: 'dot' }
    });
  });

  // Cursor line (always last shape — updated by updateMotorCycle)
  shapes.push({
    type: 'line', xref: 'x', x0: highlightCycle, x1: highlightCycle, yref: 'paper', y0: 0, y1: 1,
    line: { color: 'rgba(129,140,248,0.7)', width: 2 }
  });

  // Annotations: threshold labels + transition labels + cursor
  const annotations = [];

  // θ_RUL label
  annotations.push({
    xref: 'paper', x: 1.0, yref: 'y', y: thetaRUL,
    text: `θ=${thetaRUL}`, showarrow: false,
    font: { size: 9, color: 'rgba(239,68,68,0.7)' },
    xanchor: 'right', yanchor: 'bottom',
  });

  // α_high label
  annotations.push({
    xref: 'paper', x: 0.0, yref: 'y2', y: alphaHigh,
    text: `α=${alphaHigh}`, showarrow: false,
    font: { size: 9, color: 'rgba(249,115,22,0.7)' },
    xanchor: 'left', yanchor: 'bottom',
  });

  // Transition labels (small text at top)
  const LABEL_SHORT = { 'Normal Operation': 'Normal', 'Enhanced Monitoring': 'İzle', 'Planned Maintenance': 'Planla', 'Immediate Maintenance': 'Acil' };
  transitionPoints.forEach(tp => {
    annotations.push({
      xref: 'x', x: tp.cycle, yref: 'paper', y: 1.0,
      text: `→ ${LABEL_SHORT[tp.label] || tp.label}`,
      showarrow: false,
      font: { size: 8, color: LABEL_COLORS[tp.label] || '#64748b' },
      xanchor: 'left', yanchor: 'bottom',
      textangle: 0,
    });
  });

  // Cursor annotation (initial)
  const hRow = timeline.find(r => r.t === highlightCycle) || timeline[timeline.length - 1];
  annotations.push({
    xref: 'x', x: highlightCycle, yref: 'paper', y: 0.0,
    text: `C${hRow.t} | RUL ${hRow.rul.toFixed(1)} | A ${hRow.anomSmooth.toFixed(3)} | ${LABEL_SHORT[hRow.label] || hRow.label}`,
    showarrow: false,
    font: { size: 8, color: '#4f46e5', family: 'JetBrains Mono, monospace' },
    bgcolor: 'rgba(255,255,255,0.85)',
    borderpad: 3,
    xanchor: highlightCycle > cycles[cycles.length - 1] * 0.7 ? 'right' : 'left',
    yanchor: 'top',
  });

  Plotly.newPlot('timeline-chart', [
    {
      x: cycles, y: rul, name: 'RUL',
      type: 'scatter', mode: 'lines',
      line: { color: '#818cf8', width: 2.5 },
      fill: 'tozeroy',
      fillcolor: 'rgba(129,140,248,0.04)',
      hovertemplate: 'Cycle %{x}<br>RUL: %{y:.1f}<extra></extra>',
    },
    {
      x: cycles, y: anom, name: 'Anomaly Score',
      type: 'scatter', mode: 'lines',
      line: { color: '#f97316', width: 2.5 },
      yaxis: 'y2',
      hovertemplate: 'Cycle %{x}<br>Anomaly: %{y:.4f}<extra></extra>',
    },
  ], {
    ...PLOTLY_LAYOUT_BASE,
    xaxis: { ...PLOTLY_LAYOUT_BASE.xaxis, title: 'Cycle' },
    yaxis: { ...PLOTLY_LAYOUT_BASE.yaxis, title: 'RUL', side: 'left' },
    yaxis2: { title: 'Anomaly Score', side: 'right', overlaying: 'y', range: [0, 1], gridcolor: 'rgba(0,0,0,0)', titlefont: { color: '#f97316' }, tickfont: { color: '#f97316' } },
    showlegend: true,
    legend: { orientation: 'h', y: 1.13, font: { size: 11 } },
    shapes,
    annotations,
    margin: { t: 40, r: 60, b: 65, l: 60 },
    height: 380,
  }, PLOTLY_CONFIG);
}

function updateMotorCycle(timeline, cycle) {
  const row = timeline.find(r => r.t === cycle) || timeline[timeline.length - 1];
  const LABEL_SHORT = { 'Normal Operation': 'Normal', 'Enhanced Monitoring': 'İzle', 'Planned Maintenance': 'Planla', 'Immediate Maintenance': 'Acil' };
  const maxCycleVal = timeline[timeline.length - 1].t;

  // ── Why Explanation (new structured panel) ──
  const whyBox = document.getElementById('why-explanation-box');
  if (whyBox) {
    whyBox.innerHTML = renderWhyExplanation(row);
  }

  // Update Sensor Insight Cards
  const cardsContainer = document.getElementById('sensor-cards-container');
  const insightsSection = document.getElementById('sensor-insights-section');
  if (cardsContainer && insightsSection) {
    const isNormal = row.label === 'Normal Operation';
    const hasSensors = si && si.topSensors && si.topSensors.length > 0;

    if (isNormal || !hasSensors) {
      insightsSection.style.display = 'none';
    } else {
      insightsSection.style.display = 'block';
      cardsContainer.innerHTML = si.topSensors.map((s, i) => {
        const severityIcon = s.severity === 'critical' ? '<span class="severity-dot" style="background:var(--color-immediate)"></span>' : s.severity === 'warning' ? '<span class="severity-dot" style="background:var(--color-enhanced)"></span>' : '<span class="severity-dot" style="background:var(--color-normal)"></span>';
        const arrow = s.direction === 'up' ? '↑' : '↓';
        const pctStr = s.pctChange !== undefined ? `${s.pctChange > 0 ? '+' : ''}${s.pctChange}% ` : '';
        const barWidth = Math.min((s.zscore / 6.0) * 100, 100);
        return `
    <div class="sensor-insight-card severity-${s.severity}" style="animation-delay: ${i * 60}ms;" >
            <div class="sensor-card-header">
              <span class="sensor-severity-icon">${severityIcon}</span>
              <span class="sensor-card-name">${s.name}</span>
              <span class="sensor-card-fullname">(${s.fullName})</span>
              <span class="sensor-card-zscore">z: ${s.zscore.toFixed(2)}</span>
              <span class="sensor-card-direction sensor-direction-${s.direction}">${arrow} ${pctStr}</span>
            </div>
            <div class="sensor-bar">
              <div class="sensor-bar-fill severity-${s.severity}-fill" style="width: ${barWidth}%;"></div>
            </div>
          </div> `;
      }).join('');
    }
  }

  // Update Action
  const actionEl = document.getElementById('action-text');
  if (actionEl) {
    actionEl.innerHTML = `<span class="status-badge ${LABEL_CSS[row.label]}" > <span class="status-dot ${LABEL_CSS[row.label]}"></span>${row.label}</span> — ${row.action || LABEL_ACTIONS[row.label]} `;
  }

  // Update cursor line + cursor annotation on chart
  const chartEl = document.getElementById('timeline-chart');
  if (chartEl && chartEl.data) {
    const currentShapes = chartEl.layout.shapes ? [...chartEl.layout.shapes] : [];
    const currentAnnotations = chartEl.layout.annotations ? [...chartEl.layout.annotations] : [];

    // Update cursor line (always last shape)
    if (currentShapes.length > 0) {
      currentShapes[currentShapes.length - 1] = {
        ...currentShapes[currentShapes.length - 1],
        x0: cycle, x1: cycle
      };
    }

    // Update cursor annotation (always last annotation)
    if (currentAnnotations.length > 0) {
      currentAnnotations[currentAnnotations.length - 1] = {
        ...currentAnnotations[currentAnnotations.length - 1],
        x: cycle,
        text: `C${row.t} | RUL ${row.rul.toFixed(1)} | A ${row.anomSmooth.toFixed(3)} | ${LABEL_SHORT[row.label] || row.label}`,
        xanchor: cycle > maxCycleVal * 0.7 ? 'right' : 'left',
      };
    }

    Plotly.relayout('timeline-chart', { shapes: currentShapes, annotations: currentAnnotations });
  }
}

// ═══════════════════════════════════════════════════════
// 3D TWIN
// ═══════════════════════════════════════════════════════
async function renderTwin(container, engineId) {
  if (!fleetData) await loadFleetData();
  selectedEngine = engineId;
  const timeline = await loadEngineTimeline(engineId);
  const last = timeline[timeline.length - 1];

  // Compute component healths based on anomaly + RUL
  // Uses piecewise mapping: RUL > 2*theta → ~95-100%, theta-2*theta → 60-95%, 0-theta → 15-60%
  function computeHealths(row) {
    const theta = row.theta || 30;
    let rulHealth;
    if (row.rul > theta * 2) {
      rulHealth = 0.85 + 0.15 * Math.min(1, (row.rul - theta * 2) / (theta * 2));
    } else if (row.rul > theta) {
      rulHealth = 0.55 + 0.30 * ((row.rul - theta) / theta);
    } else {
      rulHealth = 0.10 + 0.45 * (row.rul / theta);
    }
    // Anomaly reduces health moderately (max ~20% penalty)
    const anomFactor = 1 - (row.anomSmooth * 0.25);
    const base = rulHealth * anomFactor;
    // Component-specific sensitivity multipliers
    const spread = { 'Fan': 0.02, 'LPC': 0.00, 'HPC': -0.04, 'Combustor': -0.06, 'HPT': -0.08, 'LPT': -0.02 };
    const result = {};
    for (const [name, offset] of Object.entries(spread)) {
      const jitter = Math.random() * 0.02 - 0.01;
      result[name] = Math.max(0.05, Math.min(1, base + offset + jitter));
    }
    result['Shaft'] = 0.95; // reference part (fixed)
    return result;
  }

  const healths = computeHealths(last);

  container.innerHTML = `
    <div class="fade-in" >
      <div class="motor-header">
        <div class="motor-header-left"><h2>3D Digital Twin — Motor #${engineId}</h2></div>
        <div class="motor-header-right">
          <div class="motor-status-large ${LABEL_CSS[last.label]}">${LABEL_ICONS[last.label]} ${last.label}</div>
        </div>
      </div>
      <p class="twin-disclaimer">3D görünüm temsilîdir; karar destek amaçlı şematik sağlık görselleştirmesi.</p>

      <div class="cycle-scrubber">
        <label>Cycle:</label>
        <input type="range" id="twin-cycle-slider" min="1" max="${last.t}" value="${last.t}" step="1" />
        <span class="cycle-value" id="twin-cycle-display">${last.t}</span>
        <div class="scrubber-btns">
          <button class="scrubber-btn" id="twin-play">▶ Auto-Play</button>
        </div>
      </div>

      <div class="twin-container">
        <div class="twin-3d-panel">
          <div id="twin-3d-chart" style="height:480px;"></div>
        </div>
        <div class="twin-info-panel" id="twin-health-cards">
          <div class="twin-panel-title">Bileşen Sağlığı (%)</div>
          ${Object.entries(healths).map(([name, health]) => renderHealthCard(name, health)).join('')}
        </div>
      </div>
    </div>
    `;

  render3DEngine(healths);

  // Cycle slider
  const slider = document.getElementById('twin-cycle-slider');
  const display = document.getElementById('twin-cycle-display');

  slider.addEventListener('input', () => {
    const cycle = parseInt(slider.value);
    display.textContent = cycle;
    const row = timeline.find(r => r.t === cycle) || timeline[timeline.length - 1];
    const h = computeHealths(row);
    updateHealthCards(h);
    render3DEngine(h);
  });

  const playBtn = document.getElementById('twin-play');
  let twinPlayCycle = last.t;
  playBtn.addEventListener('click', () => {
    if (autoPlayInterval) {
      clearInterval(autoPlayInterval);
      autoPlayInterval = null;
      playBtn.textContent = '▶ Auto-Play';
      playBtn.classList.remove('playing');
      return;
    }
    twinPlayCycle = 1;
    playBtn.textContent = '⏸ Durdur';
    playBtn.classList.add('playing');
    autoPlayInterval = setInterval(() => {
      twinPlayCycle += 2;
      if (twinPlayCycle > last.t) {
        clearInterval(autoPlayInterval);
        autoPlayInterval = null;
        playBtn.textContent = '▶ Auto-Play';
        playBtn.classList.remove('playing');
        return;
      }
      slider.value = twinPlayCycle;
      display.textContent = twinPlayCycle;
      const row = timeline.find(r => r.t === twinPlayCycle) || timeline[twinPlayCycle - 1] || timeline[timeline.length - 1];
      const h = computeHealths(row);
      updateHealthCards(h);
      render3DEngine(h);
    }, 120);
  });
}

function renderHealthCard(name, health) {
  const pct = (health * 100).toFixed(0);
  const color = health > 0.7 ? '#34d399' : health > 0.4 ? '#fbbf24' : '#ef4444';
  const isShaft = name === 'Shaft';
  return `
    <div class="component-health-card" data-component="${name}" >
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span class="component-name">${name}</span>
        <span class="health-value" style="color:${color};">${pct}%</span>
      </div>
      <div class="health-bar">
        <div class="health-bar-fill" style="width:${pct}%;background:${color};"></div>
      </div>
      ${isShaft ? '<div class="shaft-ref-note">Referans parça (sabit)</div>' : ''}
    </div> `;
}

function updateHealthCards(healths) {
  Object.entries(healths).forEach(([name, health]) => {
    const card = document.querySelector(`[data-component="${name}"]`);
    if (!card) return;
    const pct = (health * 100).toFixed(0);
    const color = health > 0.7 ? '#34d399' : health > 0.4 ? '#fbbf24' : '#ef4444';
    card.querySelector('.health-value').textContent = `${pct}% `;
    card.querySelector('.health-value').style.color = color;
    const fill = card.querySelector('.health-bar-fill');
    fill.style.width = `${pct}% `;
    fill.style.background = color;
  });
}

function render3DEngine(healths) {
  function healthToColor(h) {
    const r = Math.round(239 + (52 - 239) * h);
    const g = Math.round(68 + (211 - 68) * h);
    const b = Math.round(68 + (153 - 68) * h);
    return `rgb(${r}, ${g}, ${b})`;
  }

  function createCylinder(zStart, zEnd, radius, nPts, health, name) {
    const theta = [];
    const z = [];
    const r = [];
    const nZ = 12;

    for (let iz = 0; iz <= nZ; iz++) {
      const zVal = zStart + (zEnd - zStart) * iz / nZ;
      for (let it = 0; it <= nPts; it++) {
        theta.push(2 * Math.PI * it / nPts);
        z.push(zVal);
        r.push(radius);
      }
    }

    const x = theta.map((t, i) => r[i] * Math.cos(t));
    const y = theta.map((t, i) => r[i] * Math.sin(t));

    return {
      type: 'surface',
      x: reshape(x, nZ + 1, nPts + 1),
      y: reshape(y, nZ + 1, nPts + 1),
      z: reshape(z, nZ + 1, nPts + 1),
      colorscale: [[0, healthToColor(health)], [1, healthToColor(health)]],
      surfacecolor: reshape(z.map(() => health), nZ + 1, nPts + 1),
      showscale: false,
      opacity: 0.88,
      name,
      hovertemplate: `${name} <br>Health: ${(health * 100).toFixed(0)}%<extra></extra>`,
    };
  }

  function reshape(arr, rows, cols) {
    const result = [];
    for (let i = 0; i < rows; i++) {
      result.push(arr.slice(i * cols, (i + 1) * cols));
    }
    return result;
  }

  const nPts = 32;
  // Turbofan-style narrower proportions (schematic)
  const traces = [
    createCylinder(0, 2.2, 1.55, nPts, healths['Fan'], 'Fan'),
    createCylinder(2.4, 4.3, 1.22, nPts, healths['LPC'], 'LPC'),
    createCylinder(4.5, 6.4, 0.98, nPts, healths['HPC'], 'HPC'),
    createCylinder(6.6, 8.0, 0.92, nPts, healths['Combustor'], 'Combustor'),
    createCylinder(8.2, 9.6, 0.95, nPts, healths['HPT'], 'HPT'),
    createCylinder(9.8, 11.6, 1.08, nPts, healths['LPT'], 'LPT'),
    // Inner shaft
    createCylinder(-0.3, 12.0, 0.22, 16, healths['Shaft'], 'Shaft'),
  ];

  Plotly.react('twin-3d-chart', traces, {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    scene: {
      xaxis: { visible: false },
      yaxis: { visible: false },
      zaxis: { visible: false, range: [-0.5, 12.5] },
      camera: { eye: { x: 1.8, y: 0.8, z: 0.5 } },
      bgcolor: 'rgba(0,0,0,0)',
      aspectratio: { x: 1, y: 1, z: 2.8 },
    },
    margin: { t: 0, r: 0, b: 0, l: 0 },
    font: { family: 'Inter, sans-serif', color: '#94a3b8' },
  }, { ...PLOTLY_CONFIG, scrollZoom: true });
}

// ═══════════════════════════════════════════════════════
// AUDIT
// ═══════════════════════════════════════════════════════
async function renderAudit(container) {
  if (!fleetData) await loadFleetData();
  const d = fleetData;

  container.innerHTML = `
    <div class="fade-in">
      <h2 style="margin-bottom:var(--space-xl)">Audit & Kanıt Zinciri</h2>

      <div class="audit-grid">
        <div class="audit-card">
          <div class="audit-card-title">Policy Snapshot</div>
          <div class="audit-item"><span class="audit-key">Policy Version</span><span class="audit-value">${d.policyVersion}</span></div>
          <div class="audit-item"><span class="audit-key">θ_RUL (threshold)</span><span class="audit-value">${d.theta}</span></div>
          <div class="audit-item"><span class="audit-key">Smoothing</span><span class="audit-value">EMA · span=7</span></div>
          <div class="audit-item"><span class="audit-key">Persistence</span><span class="audit-value">min_cycles_on=3</span></div>
          <div class="audit-item"><span class="audit-key">Dataset</span><span class="audit-value">${d.dataset}</span></div>
        </div>

        <div class="audit-card">
          <div class="audit-card-title">Veri Kalitesi</div>
          <div class="audit-item"><span class="audit-key">Toplam Satır</span><span class="audit-value">${d.totalCycles.toLocaleString('tr-TR')}</span></div>
          <div class="audit-item"><span class="audit-key">Motor Sayısı</span><span class="audit-value">${d.totalEngines}</span></div>
          <div class="audit-item"><span class="audit-key">Duplicate</span><span class="audit-value audit-check">✓ 0</span></div>
          <div class="audit-item"><span class="audit-key">NaN</span><span class="audit-value audit-check">✓ 0</span></div>
          <div class="audit-item"><span class="audit-key">Join Key</span><span class="audit-value mono" style="font-size:0.72rem;">(asset_id, t)</span></div>
        </div>

        <div class="audit-card">
          <div class="audit-card-title">Yöntem Güvencesi</div>
          <div class="audit-item"><span class="audit-key">Anomaly Fit</span><span class="audit-value audit-check">✓ Train-Only</span></div>
          <div class="audit-item"><span class="audit-key">Leakage</span><span class="audit-value audit-check">✓ Safe</span></div>
          <div class="audit-item"><span class="audit-key">Anomaly Method</span><span class="audit-value">Baseline Deviation</span></div>
          <div class="audit-item"><span class="audit-key">Mapping</span><span class="audit-value">Sigmoid → [0,1]</span></div>
          <div class="audit-item"><span class="audit-key">Reproduciblity</span><span class="audit-value audit-check">✓ Repro Docs</span></div>
        </div>

        <div class="audit-card">
          <div class="audit-card-title">Run Metadata</div>
          <div class="audit-item"><span class="audit-key">Run ID</span><span class="audit-value mono" style="font-size:0.7rem;">${d.runId || 'N/A'}</span></div>
          <div class="audit-item"><span class="audit-key">Config Source</span><span class="audit-value mono" style="font-size:0.7rem;">decision_support_thresholds.json</span></div>
          <div class="audit-item"><span class="audit-key">Karar Etiketleri</span><span class="audit-value">4 seviye</span></div>
          <div class="audit-item"><span class="audit-key">Reason Codes</span><span class="audit-value audit-check">✓ Her satırda</span></div>
        </div>
      </div>

      <!-- Proof Cards -->
      <div class="proof-card" style="margin-top:var(--space-2xl);">
        <div class="proof-card-label">KANIT KARTI #1</div>
        <div class="proof-card-claim">Her motor, her çevrimde izlenebilir bir karar alır.</div>
        <div class="proof-card-evidence">
          <p><span class="evidence-icon">•</span> ${d.totalCycles.toLocaleString('tr-TR')} satır × 20 kolon → her cycle'da: rul_pred, anomaly_score, decision_label, reason_codes, reason_text</p>
          <p><span class="evidence-icon">•</span> Doğrulama: Herhangi bir motoru seçip timeline'da cycle-cycle karar geçmişini inceleyebilirsiniz.</p>
          <p><span class="evidence-icon">•</span> Config yolu: decision_support_thresholds.json — θ_RUL=${d.theta}</p>
        </div>
      </div>

      <div class="proof-card">
        <div class="proof-card-label">KANIT KARTI #2</div>
        <div class="proof-card-claim">Pipeline leakage-safe: anomaly skoru sadece eğitim verisine fit edilir.</div>
        <div class="proof-card-evidence">
          <p><span class="evidence-icon">•</span> Anomaly baseline yalnızca train split üzerinde hesaplanır; test split skorları bu baseline'a göre üretilir.</p>
          <p><span class="evidence-icon">•</span> Kanıt: anomaly_thresholds.json → "mapping_fit_on": "train"</p>
          <p><span class="evidence-icon">•</span> Doğrulama: anomaly_baseline_deviation.py kaynak kodunda .fit() yalnızca train_df üzerinde çağrılır.</p>
        </div>
      </div>

      <div class="proof-card">
        <div class="proof-card-label">KANIT KARTI #3</div>
        <div class="proof-card-claim">Karar şeffaflığı: her etiketin neden verildiği açıklanır.</div>
        <div class="proof-card-evidence">
          <p><span class="evidence-icon">•</span> reason_codes: RUL_HIGH|ANOM_OFF, RUL_LOW|ANOM_ON gibi kodlar — neden bu karar verildiğini açıklar.</p>
          <p><span class="evidence-icon">•</span> reason_text: Türkçe açıklama metni: "RUL > theta ve anomaly_state OFF; rutin operasyon devam."</p>
          <p><span class="evidence-icon">•</span> Doğrulama: Motor Detail → Why Panel'de her cycle için reason codes ve metin görüntülenir.</p>
        </div>
      </div>
    </div>
    `;
}

// ═══════════════════════════════════════════════════════
// DEMO MODE
// ═══════════════════════════════════════════════════════
const DEMO_STEPS = [
  {
    page: 'landing',
    narration: `${PRODUCT_NAME}: C-MAPSS (FD001–FD004) ve N-CMAPSS (DS01–DS07) senaryolarında çalıştırılmış, şu an ${activeDataset} üzerinden gösterilen karar destek sistemidir.`,
    params: {},
  },
  {
    page: 'fleet',
    narration: 'Filo görünümü: 100 motorun risk durumu tek bakışta. Kırmızı noktalar acil bakım gerektiren motorlar. "Ana Sorun" kolonu — hangi sensör sorunlu, anında görülüyor.',
    params: {},
  },
  {
    page: 'motor',
    narration: 'Motor timeline: RUL düşüşü ve anomali artışı birlikte gözlemleniyor. Cycle scrubber ile motorun tüm yaşam döngüsünü izleyin.',
    params: { engineId: 76 },
  },
  {
    page: 'motor',
    narration: 'XAI Sensör Analizi: "Neden acil bakım?" sorusuna somut cevap. Hangi sensörler ne kadar sapmış — z-score barlarıyla bakım mühendisine yol gösteriyor.',
    params: { engineId: 76 },
    scrollToXAI: true,
  },
  {
    page: 'twin',
    narration: '3D dijital ikiz: motor bileşenlerinin sağlık durumu renk kodlu gösterilir. Auto-play ile bozulma animasyonunu izleyin.',
    params: { engineId: 76 },
  },
  {
    page: 'audit',
    narration: 'Tam izlenebilirlik: policy version, eşik değerleri, config hash, veri kalitesi kontrolleri. Her kararın nasıl alındığı audit edilebilir.',
    params: {},
  },
];

let demoStep = 0;
let demoNavLock = false;
let demoPendingTimeout = null;

function startDemo() {
  demoStep = 0;
  document.getElementById('demo-overlay').classList.remove('hidden');
  runDemoStep();
}

function runDemoStep() {
  // Clear any pending timeout from previous step
  if (demoPendingTimeout) { clearTimeout(demoPendingTimeout); demoPendingTimeout = null; }

  const step = DEMO_STEPS[demoStep];
  document.getElementById('demo-step-label').textContent = `Adım ${demoStep + 1}/${DEMO_STEPS.length}`;
  document.getElementById('demo-narration').textContent = step.narration;
  document.getElementById('demo-prev').style.visibility = demoStep === 0 ? 'hidden' : 'visible';
  document.getElementById('demo-next').textContent = demoStep === DEMO_STEPS.length - 1 ? 'Bitir ✓' : 'İleri →';
  navigateTo(step.page, step.params);

  // Auto-scroll to XAI panel if step requests it, using rAF + timeout for stability
  if (step.scrollToXAI) {
    demoPendingTimeout = setTimeout(() => {
      requestAnimationFrame(() => {
        const xaiPanel = document.querySelector('.why-panel-xai');
        if (xaiPanel) xaiPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    }, 450);
  }
}

function endDemo() {
  if (demoPendingTimeout) { clearTimeout(demoPendingTimeout); demoPendingTimeout = null; }
  demoNavLock = false;
  document.getElementById('demo-overlay').classList.add('hidden');
}

// ═══════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', async () => {
  await loadFleetData();

  // Find best demo engine: Immediate Maintenance with richest sensor insights
  const immEngines = fleetData.engines
    .filter(e => e.label === 'Immediate Maintenance' && e.topSensor)
    .sort((a, b) => a.rul - b.rul);
  if (immEngines.length > 0) {
    const bestId = immEngines[0].id;
    DEMO_STEPS[2].params.engineId = bestId;
    DEMO_STEPS[3].params.engineId = bestId;
    DEMO_STEPS[4].params.engineId = bestId;
    DEMO_STEPS[2].narration = `Motor #${bestId}'in timeline'ında RUL düşüşü ve anomali artışı birlikte gözlemleniyor. Cycle scrubber ile motorun tüm yaşam döngüsünü izleyin.`;
    DEMO_STEPS[3].narration = `XAI Sensör Analizi: "Neden Motor #${bestId} acil bakımda?" — ${immEngines[0].topSensor}. Hangi sensörler sapmış, z-score barlarıyla görüyorsunuz.`;
  }

  // Nav links
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      navigateTo(link.dataset.page);
    });
  });

  // Demo mode
  document.getElementById('btn-demo-mode').addEventListener('click', startDemo);
  document.getElementById('demo-next').addEventListener('click', () => {
    if (demoNavLock) return;
    if (demoStep >= DEMO_STEPS.length - 1) { endDemo(); return; }
    demoNavLock = true;
    demoStep++;
    runDemoStep();
    setTimeout(() => { demoNavLock = false; }, 350);
  });
  document.getElementById('demo-prev').addEventListener('click', () => {
    if (demoNavLock) return;
    if (demoStep > 0) {
      demoNavLock = true;
      demoStep--;
      runDemoStep();
      setTimeout(() => { demoNavLock = false; }, 350);
    }
  });
  document.getElementById('demo-close').addEventListener('click', endDemo);

  // Sidebar logo click → Ana Sayfa
  const sidebarLogo = document.querySelector('.sidebar-logo');
  if (sidebarLogo) {
    sidebarLogo.style.cursor = 'pointer';
    sidebarLogo.addEventListener('click', () => navigateTo('landing'));
  }

  // Browser back/forward support
  window.addEventListener('popstate', (e) => {
    const pageFromHash = (location.hash || '').replace('#', '') || 'intro';
    const safePage = ALLOWED_PAGES.has(pageFromHash) ? pageFromHash : 'intro';
    const params = (e.state && e.state.params) || {};
    _skipPush = true;
    navigateTo(safePage, params);
    _skipPush = false;
  });

  // Initial render — respect URL hash if present
  const initHash = (location.hash || '').replace('#', '');
  const initPage = ALLOWED_PAGES.has(initHash) ? initHash : 'intro';
  navigateTo(initPage);
});
