  /* ==========================================================
     BACKEND CONNECTION
     Change this if your backend runs on a different port/host.
  ========================================================== */
  const API_BASE_URL = 'http://localhost:5000/api/auth';
  const API_ANALYZE_URL = 'http://localhost:5000/api/analyze';
  const API_HISTORY_URL = 'http://localhost:5000/api/history';
  let chartsInitialized = false;
  let liveAnalysisResult = null;

  /* =============================================
   PAGE SWITCHING (all sidebar pages)
============================================= */
const pages = {
  dashboard: document.getElementById('page-dashboard'),
  'new-analysis': document.getElementById('page-new-analysis'),
  'analysis-history': document.getElementById('page-analysis-history'),
  reports: document.getElementById('page-reports'),
  'compare-code': document.getElementById('page-compare-code'),
  'help-support': document.getElementById('page-help-support'),
};

function showPage(pageKey) {
  Object.entries(pages).forEach(([key, el]) => {
    if (!el) return;
    el.classList.toggle('hidden', key !== pageKey);
  });
}

  /* ---------- Page + form elements ---------- */
  const loginPage = document.getElementById('login-page');
  const dashboardPage = document.getElementById('dashboard-page');
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');
  const authTitle = document.getElementById('auth-title');
  const authSubtitle = document.getElementById('auth-subtitle');
  const authMessage = document.getElementById('auth-message');
  const showSignupLink = document.getElementById('show-signup');
  const showLoginLink = document.getElementById('show-login');

  /* ---------- Toggle between Login and Signup forms ---------- */
  showSignupLink.addEventListener('click', (e) => {
    e.preventDefault();
    loginForm.classList.add('hidden');
    signupForm.classList.remove('hidden');
    authTitle.textContent = 'Create Account';
    authSubtitle.innerHTML = 'Sign up to start using <span class="text-purple-light">AI Code Analysis &amp; Optimizer</span>';
    hideAuthMessage();
  });

  showLoginLink.addEventListener('click', (e) => {
    e.preventDefault();
    signupForm.classList.add('hidden');
    loginForm.classList.remove('hidden');
    authTitle.textContent = 'Welcome Back!';
    authSubtitle.innerHTML = 'Login to continue to <span class="text-purple-light">AI Code Analysis &amp; Optimizer</span>';
    hideAuthMessage();
  });

  function showAuthMessage(text, type) {
    authMessage.textContent = text;
    authMessage.className = 'text-sm rounded-lg px-4 py-2.5 mb-4 ' +
      (type === 'error'
        ? 'bg-red-500/10 text-red-400 border border-red-500/30'
        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30');
  }
  function hideAuthMessage() {
    authMessage.classList.add('hidden');
  }

  function setButtonLoading(btn, loading, originalText) {
    btn.disabled = loading;
    btn.innerHTML = loading
      ? '<span class="animate-pulse">Please wait...</span>'
      : originalText;
  }

  /* ---------- Session helpers (token + user stored in localStorage) ---------- */
  function saveSession(token, user) {
    localStorage.setItem('authToken', token);
    localStorage.setItem('authUser', JSON.stringify(user));
  }
  function getSession() {
    const token = localStorage.getItem('authToken');
    const userRaw = localStorage.getItem('authUser');
    if (!token || !userRaw) return null;
    return { token, user: JSON.parse(userRaw) };
  }
  function clearSession() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
  }

  function initials(name) {
    return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
  }

  function goToDashboard(user) {
  loginPage.classList.add('hidden');
  dashboardPage.classList.remove('hidden');

  document.getElementById('welcome-heading').textContent = `Welcome back, ${user.name.split(' ')[0]}! 👋`;
  document.getElementById('sidebar-username').textContent = user.name;
  document.getElementById('sidebar-avatar').textContent = initials(user.name);
  const topbarAvatarEl = document.getElementById('topbar-avatar');
  if (topbarAvatarEl) topbarAvatarEl.textContent = initials(user.name);

  // Always go back to the Dashboard tab and clear any previous user's live report
  liveAnalysisResult = null;
  window.currentReportIssues = null;
  document.querySelectorAll('[data-nav]').forEach(i => i.classList.remove('active'));
  const dashNav = document.querySelector('[data-page="dashboard"]');
  if (dashNav) dashNav.classList.add('active');
  showPage('dashboard');

  initDashboardCharts();
  loadHistoryFromBackend(); // fetch THIS user's history right away
  loadDashboardData();
}

  /* ---------- LOGIN: calls POST /api/auth/login ---------- */
  loginForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    hideAuthMessage();

    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('password').value;
    const submitBtn = document.getElementById('login-submit-btn');
    const originalHtml = submitBtn.innerHTML;

    setButtonLoading(submitBtn, true, originalHtml);
    try {
      const res = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();

      if (!res.ok) {
        showAuthMessage(data.message || 'Login failed. Please try again.', 'error');
        return;
      }

      saveSession(data.token, data.user);
      goToDashboard(data.user);
    } catch (err) {
      showAuthMessage('Could not reach the server. Is the backend running on port 5000?', 'error');
    } finally {
      setButtonLoading(submitBtn, false, originalHtml);
    }
  });

  /* ---------- SIGNUP: calls POST /api/auth/register ---------- */
  signupForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    hideAuthMessage();

    const name = document.getElementById('signup-name').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const confirm = document.getElementById('signup-confirm').value;
    const submitBtn = document.getElementById('signup-submit-btn');
    const originalHtml = submitBtn.innerHTML;

    // Browser-side form validation only; server-side validation remains required.
    // eslint-disable-next-line security/detect-possible-timing-attacks -- Comparing the two signup form fields, not authenticating a secret.
    if (password !== confirm) {
      showAuthMessage('Passwords do not match.', 'error');
      return;
    }

    setButtonLoading(submitBtn, true, originalHtml);
    try {
      const res = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });
      const data = await res.json();

      if (!res.ok) {
        showAuthMessage(data.message || 'Could not create account.', 'error');
        return;
      }

      saveSession(data.token, data.user);
      goToDashboard(data.user);
    } catch (err) {
      showAuthMessage('Could not reach the server. Is the backend running on port 5000?', 'error');
    } finally {
      setButtonLoading(submitBtn, false, originalHtml);
    }
  });

  /* ---------- LOGOUT ---------- */
  document.getElementById('logout-btn').addEventListener('click', () => {
  clearSession();

  // Clear all session-specific in-memory state so the next login starts fresh
  liveAnalysisResult = null;
  analysisHistoryData = [];
  window.currentReportIssues = null;

  document.getElementById('history-table-body').innerHTML = '';
  document.getElementById('history-count').textContent = '';
  document.getElementById('history-search').value = '';
  document.getElementById('history-lang-filter').value = '';

  dashboardPage.classList.add('hidden');
  loginPage.classList.remove('hidden');
  loginForm.reset();
  signupForm.reset();
});

  /* ---------- Auto-login on page load if a valid session already exists ---------- */
  (function tryAutoLogin() {
    const session = getSession();
    if (session) {
      goToDashboard(session.user);
    }
  })();

  /* ---------- Password show/hide ---------- */
  const pwInput = document.getElementById('password');
  const eyeIcon = document.getElementById('eye-icon');
  document.getElementById('toggle-pw').addEventListener('click', () => {
    const show = pwInput.type === 'password';
    pwInput.type = show ? 'text' : 'password';
    eyeIcon.innerHTML = show
      ? '<path d="M3 3l18 18" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M10.6 5.1A11.6 11.6 0 0112 5c7 0 11 7 11 7a14.6 14.6 0 01-3.1 3.9M6.5 6.6C3.5 8.3 1 12 1 12s4 7 11 7a10.8 10.8 0 004.2-.85" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M9.9 9.9a3 3 0 004.2 4.2" stroke="currentColor" stroke-width="1.6"/>'
      : '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.6"/>';
  });

  /* ---------- Sidebar nav active state ---------- */
  document.querySelectorAll('[data-nav]').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelectorAll('[data-nav]').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
    });
  });

  /* ---------- Charts (Chart.js) ---------- */
function initDashboardCharts() {
  if (chartsInitialized) return;
  chartsInitialized = true;

  try {
    document.querySelectorAll('canvas.spark').forEach(canvas => {
      const values = canvas.dataset.values.split(',').map(Number);
      const color = canvas.dataset.color;
      new Chart(canvas, {
        type: 'line',
        data: {
          labels: values.map((_, i) => i),
          datasets: [{
            data: values, borderColor: color, borderWidth: 2, pointRadius: 0,
            tension: 0.45, fill: true, backgroundColor: color + '22',
          }]
        },
        options: {
          responsive: false, animation: { duration: 600 },
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: { x: { display: false }, y: { display: false } },
          elements: { line: { borderJoinStyle: 'round' } }
        }
      });
    });
  } catch (err) {
    console.warn('Sparkline charts could not load:', err);
  }
}

/* ---- helper: darken/lighten a hex color ---- */
function shadeColor(hex, percent) {
  let r = parseInt(hex.slice(1, 3), 16);
  let g = parseInt(hex.slice(3, 5), 16);
  let b = parseInt(hex.slice(5, 7), 16);
  r = Math.max(0, Math.min(255, Math.floor(r * (1 + percent))));
  g = Math.max(0, Math.min(255, Math.floor(g * (1 + percent))));
  b = Math.max(0, Math.min(255, Math.floor(b * (1 + percent))));
  return `rgb(${r}, ${g}, ${b})`;
}

/* ---- plugin: single clean glass/bubble highlight across the whole ring ---- */
const donutGlossPlugin = {
  id: 'donutGloss',
  afterDatasetsDraw(chart) {
    const { ctx, chartArea } = chart;
    const meta = chart.getDatasetMeta(0);
    if (!meta || !meta.data.length) return;

    const first = meta.data[0].getProps(['x', 'y', 'outerRadius', 'innerRadius'], true);

    ctx.save();
    ctx.beginPath();
    meta.data.forEach((arc) => {
      const { x, y, startAngle, endAngle, innerRadius, outerRadius } = arc.getProps(
        ['x', 'y', 'startAngle', 'endAngle', 'innerRadius', 'outerRadius'],
        true
      );
      ctx.moveTo(x + outerRadius * Math.cos(startAngle), y + outerRadius * Math.sin(startAngle));
      ctx.arc(x, y, outerRadius, startAngle, endAngle);
      ctx.arc(x, y, innerRadius, endAngle, startAngle, true);
      ctx.closePath();
    });
    ctx.clip();

    const grad = ctx.createRadialGradient(
      first.x - first.outerRadius * 0.45, first.y - first.outerRadius * 0.55, 0,
      first.x, first.y, first.outerRadius * 1.4
    );
    grad.addColorStop(0, 'rgba(255,255,255,0.5)');
    grad.addColorStop(0.35, 'rgba(255,255,255,0.15)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');

    ctx.globalCompositeOperation = 'screen';
    ctx.fillStyle = grad;
    ctx.fillRect(chartArea.left - 20, chartArea.top - 20, chartArea.width + 40, chartArea.height + 40);
    ctx.restore();
  }
};

let dashboardIssueDonutChart = null;

/* ---- BRIGHT, VIBRANT palette — pops more than the old muted tailwind shades ---- */
const DONUT_COLORS = {
  critical: '#ff5c7a',  // vivid pink-red
  high:     '#ff9d3d',  // vivid tangerine
  medium:   '#ffe25c',  // vivid sunflower yellow
  low:      '#3fc7ff',  // vivid cyan-blue
};

function renderDashboardIssueDonut(critical, high, medium, low) {
  const canvas = document.getElementById('issueDonut');
  const ctx = canvas.getContext('2d');

  try {
    if (dashboardIssueDonutChart) dashboardIssueDonutChart.destroy();

    const total = critical + high + medium + low;
    const hasData = total > 0;
    const chartData = hasData ? [critical, high, medium, low] : [1];
    const baseColors = hasData
      ? [DONUT_COLORS.critical, DONUT_COLORS.high, DONUT_COLORS.medium, DONUT_COLORS.low]
      : ['#211f38'];

    // brighter highlight-to-edge gradient for a lifted, glossy pop
    const sliceGradients = baseColors.map((hex) => {
      const grad = ctx.createRadialGradient(
        canvas.width / 2, canvas.height / 2, 0,
        canvas.width / 2, canvas.height / 2, canvas.width / 2
      );
      grad.addColorStop(0, shadeColor(hex, 0.3));
      grad.addColorStop(1, shadeColor(hex, -0.02));
      return grad;
    });

    dashboardIssueDonutChart = new Chart(canvas, {
      type: 'doughnut',
      plugins: [donutGlossPlugin],
      data: {
        labels: ['Critical', 'High', 'Medium', 'Low'],
        datasets: [{
          data: chartData,
          backgroundColor: sliceGradients,
          borderColor: '#100f20',
          borderWidth: 2,
          hoverOffset: 8,
          hoverBorderWidth: 3,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: hasData,
            backgroundColor: '#161528',
            titleColor: '#e7e6f5',
            bodyColor: '#c9c7de',
            borderColor: '#26233f',
            borderWidth: 1,
            padding: 10,
            callbacks: { label: (tooltipContext) => ` ${tooltipContext.label}: ${tooltipContext.parsed}` }
          }
        },
        animation: { animateRotate: true, duration: 700, easing: 'easeOutQuart' }
      }
    });
  } catch (err) {
    console.warn('Issue donut could not load:', err);
  }
}



/* =============================================
   DASHBOARD — load real data from backend
============================================= */
async function loadDashboardData() {
  const session = getSession();
  if (!session) return;

  const headers = { 'Authorization': `Bearer ${session.token}` };

  try {
    const [statsRes, compareRes, historyRes] = await Promise.all([
      fetch(`${API_HISTORY_URL}/latest-stats`, { headers }),
      fetch(`${API_HISTORY_URL}/latest-compare`, { headers }),
      fetch(API_HISTORY_URL, { headers }),
    ]);

    const stats = await statsRes.json();
    const compare = await compareRes.json();
    const history = await historyRes.json();

    renderDashboardStats(stats);
    renderDashboardComparison(compare);
    renderDashboardRecentTable((history.history || []).slice(0, 5));
  } catch (err) {
    console.warn('Could not load dashboard data:', err);
  }
}

function renderDashboardStats(stats) {
  const quality = stats.quality_score || 0;
  document.getElementById('dash-quality-score').textContent = quality;
  const ql = qualityLabel(quality);
  const qLabelEl = document.getElementById('dash-quality-label');
  qLabelEl.innerHTML = `<span class="w-1.5 h-1.5 rounded-full" style="background:${ql.ring}"></span>${ql.text}`;
  qLabelEl.className = `text-xs mt-1 flex items-center gap-1 ${ql.color}`;

  const secRisk = stats.security_risk_pct || 0;
  document.getElementById('dash-security-risk').textContent = secRisk;
  const secLabelEl = document.getElementById('dash-security-label');
  const secText = secRisk >= 30 ? 'High Risk' : secRisk >= 10 ? 'Medium Risk' : 'Low Risk';
  const secColor = secRisk >= 30 ? 'text-red-400' : secRisk >= 10 ? 'text-orange-400' : 'text-emerald-400';
  secLabelEl.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-current"></span>${secText}`;
  secLabelEl.className = `text-xs mt-1 flex items-center gap-1 ${secColor}`;

  document.getElementById('dash-bugs-found').textContent = stats.bug_count || 0;
  document.getElementById('dash-performance-issues').textContent = stats.performance_count || 0;
  document.getElementById('dash-files-analyzed').textContent = stats.total_files || 0;

  const critical = Number(stats.critical_count) || 0;
  const high = Number(stats.high_count) || 0;
  const medium = Number(stats.medium_count) || 0;
  const low = Number(stats.low_count) || 0;

  renderDashboardIssueDonut(critical, high, medium, low);
  const total = critical + high + medium + low;
  document.getElementById('dash-issue-total').textContent = total;
  document.getElementById('dash-sev-critical').textContent = critical;
  document.getElementById('dash-sev-high').textContent = high;
  document.getElementById('dash-sev-medium').textContent = medium;
  document.getElementById('dash-sev-low').textContent = low;

  const total2 = total || 1;
  const pct = (n) => (n / total2 * 100).toFixed(1);
  document.getElementById('dash-sev-bar-critical').style.width = pct(critical) + '%';
  document.getElementById('dash-sev-bar-high').style.width = pct(high) + '%';
  document.getElementById('dash-sev-bar-medium').style.width = pct(medium) + '%';
  document.getElementById('dash-sev-bar-low').style.width = pct(low) + '%';

  const catBug = Number(stats.bug_count) || 0;
  const catSecurity = Number(stats.security_count) || 0;
  const catPerformance = Number(stats.performance_count) || 0;
  const catStyle = Number(stats.style_count) || 0;
  const catTotal = (catBug + catSecurity + catPerformance + catStyle) || 1;
  const catPct = (n) => (n / catTotal * 100).toFixed(1);

  document.getElementById('dash-cat-bug').textContent = catBug;
  document.getElementById('dash-cat-security').textContent = catSecurity;
  document.getElementById('dash-cat-performance').textContent = catPerformance;
  document.getElementById('dash-cat-style').textContent = catStyle;

  document.getElementById('dash-cat-bar-bug').style.width = catPct(catBug) + '%';
  document.getElementById('dash-cat-bar-security').style.width = catPct(catSecurity) + '%';
  document.getElementById('dash-cat-bar-performance').style.width = catPct(catPerformance) + '%';
  document.getElementById('dash-cat-bar-style').style.width = catPct(catStyle) + '%';
}

function renderDashboardComparison(compare) {
  const emptyBox = document.getElementById('dash-compare-empty');
  const contentBox = document.getElementById('dash-compare-content');

  if (!compare || compare.available === false || !compare.fixed_code) {
    emptyBox.classList.remove('hidden');
    contentBox.classList.add('hidden');
    return;
  }

  emptyBox.classList.add('hidden');
  contentBox.classList.remove('hidden');

  document.getElementById('dash-compare-lang-icon').innerHTML = langIcon(compare.language);
  document.getElementById('dash-compare-lang-text').textContent = compare.language || '–';

  if (compare.original_code) {
    setHighlightedCode('dash-original-code', compare.original_code, compare.language);
  } else {
    document.getElementById('dash-original-code').textContent = '(original code not available for this entry)';
  }
  setHighlightedCode('dash-optimized-code', compare.fixed_code, compare.language);
  document.getElementById('dash-compare-file').textContent = compare.file_name || 'pasted_code';
  document.getElementById('dash-compare-score').textContent = `${compare.quality_score}/100`;
  document.getElementById('dash-compare-issues').textContent = compare.total_issues;
  document.getElementById('dash-compare-date').textContent = compare.created_at || '–';
}

function renderDashboardRecentTable(rows) {
  const tbody = document.getElementById('recent-analysis-body');

  if (!rows || rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-gray-500 text-sm py-8">No analyses yet. Run one from "New Analysis"!</td></tr>`;
    return;
  }

  const scoreColor = (score) => {
    if (score >= 85) return 'text-emerald-400 bg-emerald-500/10';
    if (score >= 70) return 'text-amber-400 bg-amber-500/10';
    return 'text-red-400 bg-red-500/10';
  };

  tbody.innerHTML = rows.map(row => `
    <tr class="border-b border-border/60 hover:bg-cardhi/50 transition">
      <td class="py-4 pr-4 flex items-center gap-3 text-gray-100 font-semibold text-sm">
        <span class="w-8 h-8 rounded-lg bg-card border border-border/60 flex items-center justify-center shrink-0">${langIcon(row.language)}</span>
        ${row.file_name}
      </td>
      <td class="py-4 pr-4 text-gray-300 capitalize font-medium text-sm">${row.language}</td>
      <td class="py-4 pr-4"><span class="bg-red-500/15 text-red-400 text-sm font-bold px-2.5 py-1 rounded-md">${row.total_issues}</span></td>
      <td class="py-4 pr-4"><span class="${scoreColor(row.quality_score)} text-sm font-bold px-2.5 py-1 rounded-md">${row.quality_score}/100</span></td>
      <td class="py-4 pr-4 text-gray-400 text-sm">${row.created_at}</td>
      <td class="py-4">
        <div class="flex items-center gap-4 text-gray-400">
          <button data-dash-view="${row.id}" class="hover:text-white transition" title="View"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.8"/></svg></button>
          <button data-dash-delete="${row.id}" class="hover:text-red-400 transition" title="Delete"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        </div>
      </td>
    </tr>
  `).join('');

  tbody.querySelectorAll('[data-dash-view]').forEach(btn => {
    btn.addEventListener('click', () => viewHistoricalReport(btn.dataset.dashView));
  });

  tbody.querySelectorAll('[data-dash-delete]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Delete this analysis permanently?')) return;
      const session = getSession();
      try {
        const res = await fetch(`${API_HISTORY_URL}/${btn.dataset.dashDelete}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${session.token}` },
        });
        if (res.ok) {
          loadDashboardData();
          loadHistoryFromBackend();
        } else {
          alert('Could not delete this analysis.');
        }
      } catch (err) {
        alert('Could not reach the backend.');
      }
    });
  });
}

// hook into the existing sidebar nav-item click handler
document.querySelectorAll('[data-nav]').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('[data-nav]').forEach(i => i.classList.remove('active'));
    item.classList.add('active');

    const pageKey = item.dataset.page;
    if (pageKey && pages[pageKey]) {
      showPage(pageKey);
    }
  });
});

/* =============================================
   NEW ANALYSIS PAGE — source tabs (Paste / Upload / Image)
============================================= */
const sourceTabs = document.querySelectorAll('[data-source-tab]');
const editorPanel = document.getElementById('editor-panel');
const uploadPanel = document.getElementById('upload-panel');
const imagePanel = document.getElementById('image-panel');

sourceTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    sourceTabs.forEach(t => t.classList.remove('source-tab-active'));
    tab.classList.add('source-tab-active');

    const mode = tab.dataset.sourceTab;
    editorPanel.classList.toggle('hidden', mode !== 'paste');
    uploadPanel.classList.toggle('hidden', mode !== 'upload');
    imagePanel.classList.toggle('hidden', mode !== 'image');
  });
});

/* =============================================
   NEW ANALYSIS PAGE — code editor (line numbers + stats)
============================================= */
const codeInput = document.getElementById('code-input');
const lineNumbers = document.getElementById('line-numbers');
const statLines = document.getElementById('stat-lines');
const statChars = document.getElementById('stat-chars');
const statSize = document.getElementById('stat-size');
const clearCodeBtn = document.getElementById('clear-code-btn');

function updateEditorStats() {
  const text = codeInput.value;
  const lineCount = text === '' ? 1 : text.split('\n').length;

  lineNumbers.innerHTML = Array.from({ length: lineCount }, (_, i) => i + 1).join('<br>');

  statLines.textContent = text === '' ? 0 : lineCount;
  statChars.textContent = text.length;
  const bytes = new Blob([text]).size;
  statSize.textContent = (bytes / 1024).toFixed(2) + ' KB';

  updateCodeHighlight();
}

function updateCodeHighlight() {
  const highlightCode = document.getElementById('code-highlight-code');
  const highlightLayer = document.getElementById('code-highlight-layer');
  if (!highlightCode || !window.Prism) return;

  // Map our language dropdown values to Prism's language identifiers
  const langSelect = document.getElementById('language-select');
  const prismLangMap = {
    'Python': 'python', 'JavaScript': 'javascript', 'Java': 'java',
    'C++': 'cpp', 'Go': 'go', 'Auto Detect': 'python',
  };
  const prismLang = prismLangMap[langSelect.value] || 'python';

  highlightCode.className = `language-${prismLang}`;
  // A trailing newline keeps the highlighted text height in sync with the textarea
  highlightCode.textContent = codeInput.value + '\n';

  Prism.highlightElement(highlightCode);
  highlightLayer.scrollTop = codeInput.scrollTop;
  highlightLayer.scrollLeft = codeInput.scrollLeft;
}

/* Generic helper: highlights any <pre><code> block given raw code + language.
   Used for Reports, Compare Code, and Dashboard code displays. */
function setHighlightedCode(preElementId, code, language) {
  const preEl = document.getElementById(preElementId);
  if (!preEl) return;

  const prismLangMap = {
    python: 'python', javascript: 'javascript', java: 'java',
    cpp: 'cpp', go: 'go', c: 'c',
  };
  const prismLang = prismLangMap[(language || '').toLowerCase()] || 'python';

  preEl.innerHTML = `<code class="language-${prismLang}"></code>`;
  const codeEl = preEl.querySelector('code');
  codeEl.textContent = code || '';

  if (window.Prism) {
    Prism.highlightElement(codeEl);
  }
}

codeInput.addEventListener('input', updateEditorStats);
codeInput.addEventListener('scroll', () => {
  lineNumbers.scrollTop = codeInput.scrollTop;
  const highlightLayer = document.getElementById('code-highlight-layer');
  if (highlightLayer) {
    highlightLayer.scrollTop = codeInput.scrollTop;
    highlightLayer.scrollLeft = codeInput.scrollLeft;
  }
});

clearCodeBtn.addEventListener('click', () => {
  codeInput.value = '';
  updateEditorStats();
  document.getElementById('language-select').addEventListener('change', updateCodeHighlight);
  codeInput.focus();
});

updateEditorStats();

/* =============================================
   NEW ANALYSIS PAGE — file upload
============================================= */
const fileInput = document.getElementById('file-input');
const browseFileBtn = document.getElementById('browse-file-btn');
const uploadedFileName = document.getElementById('uploaded-file-name');
const uploadPanelEl = document.getElementById('upload-panel');

browseFileBtn.addEventListener('click', () => fileInput.click());
uploadPanelEl.addEventListener('click', (e) => {
  if (e.target === uploadPanelEl) fileInput.click();
});

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) return;
  uploadedFileName.textContent = `Selected: ${file.name}`;

  const reader = new FileReader();
  reader.onload = (e) => {
    codeInput.value = e.target.result;
    updateEditorStats();
    document.querySelector('[data-source-tab="paste"]').click();
  };
  reader.readAsText(file);
});

/* =============================================
   NEW ANALYSIS PAGE — image upload (placeholder)
============================================= */
const imageInput = document.getElementById('image-input');
const browseImageBtn = document.getElementById('browse-image-btn');
const uploadedImageName = document.getElementById('uploaded-image-name');

browseImageBtn.addEventListener('click', () => imageInput.click());
imageInput.addEventListener('change', () => {
  const file = imageInput.files[0];
  if (file) uploadedImageName.textContent = `Selected: ${file.name}`;
});

/* =============================================
   NEW ANALYSIS PAGE — Analyze Code button
   (NOW CALLS THE REAL FLASK BACKEND)
============================================= */

function severityRank(sev) {
  return { Critical: 0, High: 1, Medium: 2, Low: 3 }[sev] ?? 4;
}

let elapsedTimer = null;

document.getElementById('analyze-code-btn').addEventListener('click', async () => {
  const code = codeInput.value.trim();
  if (!code) {
    alert('Please paste some code first.');
    return;
  }

  const langSelect = document.getElementById('language-select');
  const labelToKey = {
    'Auto Detect': 'auto', 'Python': 'python', 'JavaScript': 'javascript',
    'Java': 'java', 'C++': 'cpp', 'Go': 'go',
  };
  const language = labelToKey[langSelect.value] || 'auto';

  const useAi = document.getElementById('use-ai-toggle').checked;

  const btn = document.getElementById('analyze-code-btn');
  const originalHtml = btn.innerHTML;
  const statusBox = document.getElementById('analyze-status');
  const statusText = document.getElementById('analyze-status-text');

  btn.disabled = true;
  statusBox.classList.remove('hidden');
  const codeLineCount = code.split('\n').length;
  let estimatedTime = '1-2 minutes';
  let extraNote = '';
  if (codeLineCount > 200) {
    estimatedTime = '10-15 minutes';
    extraNote = ' Large files are processed in sections for reliability, so please be patient — the analysis is still working in the background.';
  } else if (codeLineCount > 50) {
    estimatedTime = '3-7 minutes';
  }

  statusText.innerHTML = useAi
    ? `<strong>Analyzing ${codeLineCount} lines with AI fix generation</strong><br/>Estimated time: ${estimatedTime}.${extraNote} Please don't close or refresh this tab.`
    : 'Running static analysis...';
  let seconds = 0;
  elapsedTimer = setInterval(() => {
    seconds++;
    btn.innerHTML = `<span class="animate-pulse">Analyzing... ${seconds}s</span>`;
  }, 1000);

  try {
    const session = getSession();
    const headers = { 'Content-Type': 'application/json' };
    if (session) headers['Authorization'] = `Bearer ${session.token}`;

    const res = await fetch(API_ANALYZE_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify({ code, language, use_ai: useAi }),
    });
    const data = await res.json();

    if (!res.ok) {
      alert(data.error || 'Analysis failed. Please try again.');
      return;
    }

    liveAnalysisResult = data;
    renderLiveReport(data);
    renderCompareCode(data, code);
    goToPage('reports');
  } catch (err) {
    alert('Could not reach the backend. Is Flask running on port 5000?');
  } finally {
    clearInterval(elapsedTimer);
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    statusBox.classList.add('hidden');
  }
});

/* Populate the Reports page using a REAL backend response */
function renderLiveReport(data) {

  renderQualityRing(data.original_quality_score ?? data.quality_score);
  
  // Show original vs fixed-code quality scores only after verified re-scan.
  const scoreComparison = document.getElementById('quality-score-comparison');
  if (scoreComparison) {
    const verified =
      Boolean(data.fixed_code) &&
      data.verification_status === 'security_rescan_passed' &&
      Number.isFinite(Number(data.fixed_quality_score));

    scoreComparison.classList.toggle('hidden', !verified);

    if (verified) {
      const originalScore = Number(data.original_quality_score ?? data.quality_score);
      const fixedScore = Number(data.fixed_quality_score);
      const change = fixedScore - originalScore;
      const changeText = change > 0 ? `+${change}` : String(change);

      document.getElementById('original-quality-score').textContent =
        `${originalScore}/100`;
      document.getElementById('fixed-quality-score').textContent =
        `${fixedScore}/100`;

      const changeEl = document.getElementById('quality-score-change');
      changeEl.textContent = `${changeText} points`;
      changeEl.className = change > 0
        ? 'text-sm font-semibold text-green-400'
        : change < 0
          ? 'text-sm font-semibold text-red-400'
          : 'text-sm font-semibold text-gray-400';
    }
  }

  renderSeverityAndCategoryBreakdown(data);
  
  
  // Code Analysis Summary
  const verificationBox = document.getElementById('verification-results');

  if (verificationBox) {
    const analysisStatus = document.getElementById('analysis-status');
    const fixStatus = document.getElementById('fix-verification-status');

    const hasFixedCode = typeof data.fixed_code === 'string'
      && data.fixed_code.trim().length > 0;

    const status = data.verification_status || 'not_run';

    if (analysisStatus) {
      analysisStatus.textContent = 'Analysis completed';
    }

    if (fixStatus) {
      const statusLabels = {
        security_rescan_passed: 'Security re-scan passed',
        rejected_security_check: 'Rejected — security findings remain',
        syntax_and_static_checks_passed: 'Syntax and static checks passed',
        not_run: 'Not verified',
      };

      fixStatus.textContent = statusLabels[status]
        || (hasFixedCode ? 'Verification status unavailable' : 'No verified fix available');
    }

    verificationBox.classList.toggle('hidden', !data.use_ai && !hasFixedCode);
  }


const reportFileName = document.getElementById('report-file-name');
const reportLanguage = document.getElementById('report-language');
const reportLineCount = document.getElementById('report-line-count');
const reportAnalyzedOn = document.getElementById('report-analyzed-on');
const reportAnalysisId = document.getElementById('report-analysis-id');

if (reportFileName) {
  reportFileName.textContent = data.file_name || 'pasted_code';
}

if (reportLanguage) {
  reportLanguage.textContent = data.language || 'Unknown';
}

if (reportLineCount) {
  reportLineCount.textContent = String(
    document.getElementById('code-input')?.value?.split('\n').length || '—'
  );
}

if (reportAnalyzedOn) {
  reportAnalyzedOn.textContent = new Date().toLocaleString();
}

if (reportAnalysisId) {
  const uniqueId = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

  reportAnalysisId.textContent = `#AN-${uniqueId}`;
}


  // AI explanation box
  const aiBox = document.getElementById('ai-explanation-box');
  const aiText = document.getElementById('ai-explanation-text');
  if (data.ai_explanation) {
    aiText.textContent = data.ai_explanation;
    aiBox.classList.remove('hidden');
  } else {
    aiBox.classList.add('hidden');
  }
  const riskyBox = document.getElementById('risky-suggestions-box');
  const riskyList = document.getElementById('risky-suggestions-list');
  if (
    riskyList &&
    riskyBox &&
    Array.isArray(data.risky_suggestions) &&
    data.risky_suggestions.length > 0
  ) {
    riskyList.replaceChildren();

    data.risky_suggestions.forEach((r, idx) => {
      const item = document.createElement('div');

      const heading = document.createElement('div');
      heading.className =
        'text-sm text-amber-200 font-medium mb-1';
      heading.textContent =
        `${r.title || 'Risky suggestion'} (line ${r.line ?? 'Unknown'})`;

      const code = document.createElement('pre');
      code.id = `risky-suggestion-${idx}`;
      code.className =
        'code-panel rounded-lg p-3 text-xs leading-6 overflow-x-auto';

      item.append(heading, code);
      riskyList.appendChild(item);

      setHighlightedCode(
        code.id,
        typeof r.suggestion === 'string' ? r.suggestion : '',
        data.language
      );
    });

    riskyBox.classList.remove('hidden');
  } else {
    if (riskyList) riskyList.replaceChildren();
    if (riskyBox) riskyBox.classList.add('hidden');
  }
  window.currentReportIssues = (data.issues || []).map((issue, idx) => ({
    id: idx + 1,
    title: issue.title,
    category: issue.category,
    severity: issue.severity,
    line: issue.line,
    description: issue.description,
    original: issue.original_snippet || '',
    recommendation: issue.recommendation,
    fixed: data.fixed_code || '',
  })).sort((a, b) => severityRank(a.severity) - severityRank(b.severity));

  updateTabCounts(window.currentReportIssues);

  currentReportTab = 'all';
  document.querySelectorAll('[data-report-tab]').forEach(t => t.classList.remove('report-tab-active'));
  const allTab = document.querySelector('[data-report-tab="all"]');
  if (allTab) allTab.classList.add('report-tab-active');

  renderLiveIssuesList();
  
  // Display findings from the fixed-code re-scan separately.
  const fixedSection = document.getElementById('fixed-issues-section');
  const fixedList = document.getElementById('fixed-issues-list');

  const canShowFixedIssues =
    Boolean(data.fixed_code) &&
    data.verification_status === 'security_rescan_passed' &&
    Array.isArray(data.fixed_issues);

  if (fixedSection && fixedList) {
    fixedSection.classList.toggle('hidden', !canShowFixedIssues);
    fixedList.replaceChildren();

    if (canShowFixedIssues) {
      if (data.fixed_issues.length === 0) {
        const emptyMessage = document.createElement('p');
        emptyMessage.className = 'text-emerald-400 text-sm p-3';
        emptyMessage.textContent =
          'No issues detected by the configured re-scan checks.';
        fixedList.appendChild(emptyMessage);
      } else {
        data.fixed_issues.forEach(issue => {
          const card = document.createElement('div');
          card.className = 'issue-item rounded-lg p-3 flex items-center justify-between gap-3';

          const details = document.createElement('div');

          const title = document.createElement('div');
          title.className = 'text-gray-200 text-sm font-medium';
          title.textContent = issue.title || 'Untitled issue';

          const meta = document.createElement('div');
          meta.className = 'text-gray-500 text-xs mt-0.5';
          const category = issue.category || 'other';
          meta.textContent =
            `${category.charAt(0).toUpperCase() + category.slice(1)} • Line ${issue.line ?? 'Unknown'}`;

          details.append(title, meta);

          const severity = document.createElement('span');
          const level = issue.severity || 'Unknown';
          severity.className =
            'text-xs font-medium px-2 py-0.5 rounded-md shrink-0';
          severity.textContent = level;

          if (severityBadgeClass[level]) {
            severity.classList.add(...severityBadgeClass[level].split(' '));
          } else {
            severity.classList.add('text-gray-400');
          }

          card.append(details, severity);
          fixedList.appendChild(card);
        });
      }
    }
  }


    if (getSession()) {
    loadHistoryFromBackend();
    loadDashboardData();
  }
}

function updateTabCounts(issues) {
  const counts = { all: issues.length, bug: 0, security: 0, performance: 0, style: 0 };
  issues.forEach(i => {
    if (counts[i.category] !== undefined) counts[i.category]++;
  });
  Object.entries(counts).forEach(([key, count]) => {
    const el = document.getElementById(`tab-count-${key}`);
    if (el) el.textContent = count > 0 ? `(${count})` : '';
  });
}

/* =============================================
   COMPARE CODE PAGE — real data from last analysis
============================================= */
let lastOriginalCode = '';
let lastFixedCode = '';

function renderCompareCode(data, originalCode) {
  lastOriginalCode = originalCode || '';
  lastFixedCode = data.fixed_code || '';

  document.getElementById('compare-language').textContent = data.language || '—';
  document.getElementById('compare-filename').textContent = data.file_name || 'pasted_code';
  document.getElementById('compare-date').textContent = `Analyzed on: ${new Date().toLocaleString()}`;

  const originalLines = lastOriginalCode ? lastOriginalCode.split('\n').length : 0;
  document.getElementById('compare-original-lines').textContent = `${originalLines} Lines`;
  if (lastOriginalCode) {
    setHighlightedCode('compare-original-code', lastOriginalCode, data.language);
  } else {
    document.getElementById('compare-original-code').textContent = '(original code not available for this entry)';
  }

  const optimizedLinesLabel = document.getElementById('compare-optimized-lines');

  if (lastFixedCode) {
    const fixedLines = lastFixedCode.split('\n').length;
    optimizedLinesLabel.textContent = `${fixedLines} Lines`;
    setHighlightedCode('compare-optimized-code', lastFixedCode, data.language);
  } else {
    optimizedLinesLabel.textContent = '0 Lines';
    document.getElementById('compare-optimized-code').textContent = data.ai_error
      ? `(AI fix unavailable: ${data.ai_error})`
      : '(No AI fix available — enable "AI Fix" before analyzing to get this)';
  }

  const summaryBox = document.getElementById('compare-summary');
  if (lastFixedCode) {
    summaryBox.innerHTML = `
      <div class="flex items-center gap-2 text-emerald-400 text-sm font-medium">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M8 12l3 3 5-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        AI-Fixed Version Available
      </div>
      <span class="badge-low text-xs font-medium px-2.5 py-1 rounded-md">${data.total_issues} Issues Detected</span>
      <span class="badge-low text-xs font-medium px-2.5 py-1 rounded-md">Quality Score: ${data.quality_score}/100</span>
    `;
  } else {
    summaryBox.innerHTML = `<div class="text-gray-500 text-sm">No AI fix generated for this analysis.</div>`;
  }
}

function downloadTextFile(filename, content) {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

document.getElementById('compare-download-original').addEventListener('click', () => {
  if (!lastOriginalCode) { alert('No original code to download yet.'); return; }
  downloadTextFile('original_code.txt', lastOriginalCode);
});

document.getElementById('compare-download-optimized').addEventListener('click', () => {
  if (!lastFixedCode) { alert('No AI-fixed code available to download yet.'); return; }
  downloadTextFile('optimized_code.txt', lastFixedCode);
});

function renderLiveIssuesList() {
  const list = document.getElementById('report-issues-list');
  const issues = window.currentReportIssues || [];
  const detailsPanel = document.getElementById('issue-detail-title')?.parentElement;

  if (detailsPanel) {
    detailsPanel.classList.toggle('hidden', issues.length === 0);
  }
  const filtered = currentReportTab === 'all' ? issues : issues.filter(i => i.category === currentReportTab);

  const countHeader = document.querySelector('#page-reports .grid.grid-cols-1.lg\\:grid-cols-2 .text-white.font-semibold.text-sm.mb-3');
  if (countHeader) countHeader.textContent = `Issues Found (${filtered.length})`;

  if (filtered.length === 0) {
    list.innerHTML = `<div class="text-gray-500 text-sm p-4">No issues found in this category. 🎉</div>`;
    return;
  }

  list.innerHTML = filtered.map(issue => `
    <div data-issue-id="${issue.id}" class="issue-item rounded-lg p-3 flex items-center justify-between gap-3 ${issue.severity === 'Critical' ? 'issue-item-critical' : ''}">
      <div>
        <div class="text-gray-200 text-sm font-medium">${issue.title}</div>
        <div class="text-gray-500 text-xs mt-0.5">${issue.category.charAt(0).toUpperCase() + issue.category.slice(1)} • Line ${issue.line}</div>
      </div>
      <span class="${severityBadgeClass[issue.severity]} text-xs font-medium px-2 py-0.5 rounded-md shrink-0">${issue.severity}</span>
    </div>
  `).join('');

  list.querySelectorAll('[data-issue-id]').forEach(el => {
    el.addEventListener('click', () => showLiveIssueDetail(Number(el.dataset.issueId)));
  });

  showLiveIssueDetail(filtered[0].id);
}
/* =============================================
   REPORTS PAGE — copy buttons
============================================= */
document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const targetId = btn.dataset.copyTarget;
    const text = document.getElementById(targetId).textContent;
    if (!text || text.trim() === '' || text.includes('not available')) return;

    try {
      await navigator.clipboard.writeText(text);
      const original = btn.innerHTML;
      btn.innerHTML = '✓ Copied';
      setTimeout(() => { btn.innerHTML = original; }, 1500);
    } catch (err) {
      alert('Could not copy to clipboard.');
    }
  });
});

/* =============================================
   REPORTS PAGE — Download PDF / HTML
============================================= */
document.getElementById('report-download-pdf').addEventListener('click', () => {
  if (!liveAnalysisResult) { alert('Run an analysis first.'); return; }

  const data = liveAnalysisResult;
  const issues = window.currentReportIssues || [];
  const htmlContent = buildReportHtml(data, issues);

  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('Please allow pop-ups for this site to download the PDF.');
    return;
  }
  printWindow.document.write(htmlContent);
  printWindow.document.close();

  // Give the new tab a moment to render, then trigger print automatically
  printWindow.onload = () => {
    setTimeout(() => printWindow.print(), 300);
  };
});

function buildReportHtml(data, issues) {
  const sev = data.severity_summary || { Critical: 0, High: 0, Medium: 0, Low: 0 };
  const { text: qualityText, color: qualityHex } = htmlQualityLabel(data.quality_score);
  const severityColors = { Critical: '#ef4444', High: '#f59e0b', Medium: '#eab308', Low: '#38bdf8' };

  const issuesHtml = issues.map(issue => `
    <div style="border:1px solid #26233f;border-radius:10px;padding:16px;margin-bottom:12px;background:#121123;break-inside:avoid;">
      <div style="display:flex;justify-content:space-between;align-items:start;gap:12px;">
        <strong style="color:#f1f0fa;font-size:14px;">${escapeHtml(issue.title)}</strong>
        <span style="background:${severityColors[issue.severity] || '#666'}22;color:${severityColors[issue.severity] || '#999'};padding:3px 10px;border-radius:6px;font-size:11px;font-weight:600;white-space:nowrap;">${issue.severity}</span>
      </div>
      <div style="color:#7d7b96;font-size:12px;margin:6px 0 10px;">${issue.category.charAt(0).toUpperCase() + issue.category.slice(1)} • Line ${issue.line}</div>
      <p style="font-size:13px;color:#c4c2d6;margin:0 0 8px;line-height:1.6;">${escapeHtml(issue.description)}</p>
      ${issue.original ? `<div style="font-size:11px;color:#7d7b96;margin-bottom:4px;">Code Snippet</div><pre style="background:#0b0a17;border:1px solid #211f38;border-radius:6px;padding:10px;font-size:12px;color:#c4c2d6;overflow-x:auto;margin:0 0 10px;white-space:pre-wrap;">${escapeHtml(issue.original)}</pre>` : ''}
      <p style="font-size:13px;color:#a78bfa;margin:0;"><strong>Recommendation:</strong> ${escapeHtml(issue.recommendation)}</p>
    </div>
  `).join('');

  const fixedCodeSection = data.fixed_code ? `
    <div style="margin-top:24px;">
      <h2 style="color:#f1f0fa;font-size:16px;margin-bottom:12px;">AI-Fixed Code</h2>
      <pre style="background:#0b0a17;border:1px solid #211f38;border-radius:10px;padding:16px;font-size:12px;color:#c4c2d6;overflow-x:auto;white-space:pre-wrap;">${escapeHtml(data.fixed_code)}</pre>
    </div>
  ` : '';

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Code Analysis Report - ${escapeHtml(data.file_name || 'pasted_code')}</title>
<style>
  * { box-sizing: border-box; }
  @page { margin: 20mm 15mm; }
  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #07060f;
    color: #e5e5f0;
    padding: 32px;
    max-width: 960px;
    margin: 0 auto;
    line-height: 1.5;
  }
  h1 { color: #a78bfa; font-size: 24px; margin: 0 0 4px; }
  h2 { color: #f1f0fa; font-size: 16px; }
  .meta { color: #7d7b96; font-size: 13px; margin-bottom: 24px; }
  .summary-grid { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
  .card { background: #121123; border: 1px solid #211f38; border-radius: 10px; padding: 16px; flex: 1; min-width: 160px; break-inside: avoid; }
  .card .label { color: #7d7b96; font-size: 12px; margin-bottom: 6px; }
  .card .value { font-size: 22px; font-weight: 700; color: #fff; }
  .ai-box { background: #121123; border-left: 4px solid #6d5cf5; border-radius: 8px; padding: 16px; margin-bottom: 24px; break-inside: avoid; }
  .ai-box .tag { color: #a78bfa; font-weight: 600; font-size: 13px; margin-bottom: 6px; }
  .ai-box p { font-size: 13px; color: #c4c2d6; margin: 0; }
  .footer { text-align: center; color: #4a4869; font-size: 11px; margin-top: 32px; }
  .print-btn {
    position: fixed; top: 16px; right: 16px; background: #6d5cf5; color: white;
    border: none; padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
    cursor: pointer; font-family: inherit;
  }
  @media print {
    .print-btn { display: none; }
    body { background: white; color: #111; }
    .card, .ai-box, div[style*="background:#121123"] { background: #f9f9f9 !important; border-color: #ddd !important; }
    h1, h2, strong, .card .value { color: #111 !important; }
    p, .meta { color: #444 !important; }
    pre { background: #f0f0f0 !important; color: #222 !important; border-color: #ddd !important; }
  }
</style>
</head>
<body>
  <button class="print-btn" onclick="window.print()">🖨 Print / Save as PDF</button>

  <h1>AI Code Analysis Report</h1>
  <div class="meta">
    ${escapeHtml(data.file_name || 'pasted_code')} • ${escapeHtml(data.language)} • Generated ${new Date().toLocaleString()}
  </div>

  <div class="summary-grid">
    <div class="card">
      <div class="label">Quality Score</div>
      <div class="value" style="color:${qualityHex};">${data.quality_score}<span style="font-size:13px;color:#7d7b96;">/100</span></div>
      <div style="font-size:12px;color:${qualityHex};margin-top:4px;">${qualityText}</div>
    </div>
    <div class="card">
      <div class="label">Total Issues</div>
      <div class="value">${data.total_issues}</div>
    </div>
    <div class="card">
      <div class="label">Critical / High</div>
      <div class="value">${sev.Critical || 0} / ${sev.High || 0}</div>
    </div>
  </div>

  ${data.ai_explanation ? `
  <div class="ai-box">
    <div class="tag">✦ AI Summary</div>
    <p>${escapeHtml(data.ai_explanation)}</p>
  </div>` : ''}

  <h2>Issues Found (${issues.length})</h2>
  ${issuesHtml}

  ${fixedCodeSection}

  <div class="footer">Generated by AI Code Analysis &amp; Optimizer</div>
</body>
</html>`;
}

document.getElementById('report-download-html').addEventListener('click', () => {
  if (!liveAnalysisResult) { alert('Run an analysis first.'); return; }

  const data = liveAnalysisResult;
  const issues = window.currentReportIssues || [];
  const htmlContent = buildReportHtml(data, issues);

  const blob = new Blob([htmlContent], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `report_${(data.file_name || 'analysis').replace(/\.[^/.]+$/, '')}.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

function htmlQualityLabel(score) {
  if (score >= 90) return { text: 'Excellent Quality', color: '#22c55e' };
  if (score >= 75) return { text: 'Good Quality', color: '#22c55e' };
  if (score >= 50) return { text: 'Needs Improvement', color: '#f59e0b' };
  return { text: 'Poor Quality', color: '#ef4444' };
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function showLiveIssueDetail(issueId) {
  const issue = (window.currentReportIssues || []).find(i => i.id === issueId);
  if (!issue) return;

  document.querySelectorAll('#report-issues-list [data-issue-id]').forEach(el => {
    el.classList.toggle('issue-item-active', Number(el.dataset.issueId) === issueId);
  });

  document.getElementById('issue-detail-title').textContent = issue.title;
  document.getElementById('issue-detail-meta').textContent = `${issue.category.charAt(0).toUpperCase() + issue.category.slice(1)} • Line ${issue.line}`;
  const sevBadge = document.getElementById('issue-detail-severity');
  sevBadge.textContent = issue.severity;
  sevBadge.className = `${severityBadgeClass[issue.severity]} text-xs font-medium px-2 py-0.5 rounded-md`;
  document.getElementById('issue-detail-description').textContent = issue.description;
  document.getElementById('issue-detail-recommendation').textContent = issue.recommendation;

  const currentLang = (liveAnalysisResult && liveAnalysisResult.language) || 'python';

  if (issue.original) {
    setHighlightedCode('issue-detail-original', issue.original, currentLang);
  } else {
    document.getElementById('issue-detail-original').textContent = '(snippet not available yet)';
  }

  if (issue.fixed) {
    setHighlightedCode('issue-detail-fixed', issue.fixed, currentLang);
  } else {
    document.getElementById('issue-detail-fixed').textContent =
      liveAnalysisResult && liveAnalysisResult.ai_error
        ? `(AI fix unavailable: ${liveAnalysisResult.ai_error})`
        : '(AI fix unavailable: backend returned no error details)';
  }
}

/* =============================================
   ANALYSIS HISTORY PAGE — real data from backend
============================================= */

let analysisHistoryData = [];

const LANGUAGE_ICONS = {
  python: `<svg width="20" height="20" viewBox="0 0 24 24"><path fill="#3776AB" d="M11.9 1c-1 0-1.9.1-2.7.2-2.4.4-2.8 1.3-2.8 2.9v2.1h5.6v.7H4.3c-1.6 0-3 1-3.5 2.8-.5 2.1-.5 3.4 0 5.5.4 1.6 1.3 2.8 2.9 2.8h1.9v-2.5c0-1.8 1.6-3.4 3.5-3.4h5.6c1.5 0 2.7-1.2 2.7-2.7V4.1c0-1.4-1.2-2.5-2.7-2.8-.9-.2-1.9-.3-2.8-.3zM8.9 2.6c.6 0 1 .5 1 1s-.5 1-1 1-1-.5-1-1 .4-1 1-1z"/><path fill="#FFD43B" d="M17.1 6.9v2.4c0 1.9-1.6 3.5-3.5 3.5H8c-1.5 0-2.7 1.3-2.7 2.7v5.1c0 1.4 1.2 2.3 2.7 2.7 1.8.5 3.5.6 5.6 0 1.4-.4 2.7-1.2 2.7-2.7v-2.1h-5.6v-.7h8.4c1.6 0 2.2-1.1 2.8-2.8.5-1.7.5-3.4 0-5.5-.4-1.5-1.2-2.8-2.8-2.8h-2zm-3.2 13.2c.6 0 1 .5 1 1s-.5 1-1 1-1-.5-1-1 .4-1 1-1z"/></svg>`,
  javascript: `<svg width="20" height="20" viewBox="0 0 24 24"><rect width="24" height="24" rx="3" fill="#F7DF1E"/><path fill="#000" d="M16 17.5c.4.7 1 1.2 1.9 1.2.8 0 1.3-.4 1.3-1 0-.7-.5-.9-1.4-1.3l-.5-.2c-1.4-.6-2.3-1.3-2.3-2.9 0-1.5 1.1-2.6 2.8-2.6 1.2 0 2.1.4 2.7 1.6l-1.5.9c-.3-.6-.6-.8-1.2-.8-.5 0-.9.3-.9.8 0 .6.4.8 1.2 1.2l.5.2c1.6.7 2.6 1.4 2.6 3 0 1.8-1.4 2.8-3.3 2.8-1.9 0-3-.9-3.6-2.1l1.7-.8zM8.5 17.6c.3.5.6 1 1.3 1s1.1-.3 1.1-1.3V11h2v6.4c0 2-1.2 2.9-2.9 2.9-1.6 0-2.5-.8-3-1.8l1.5-.9z"/></svg>`,
  java: `<svg width="20" height="20" viewBox="0 0 24 24"><path fill="#f89820" d="M8.8 17.6s-1.3.8.9 1c2.7.3 4.1.3 7-.2 0 0 .8.5 1.9.9-6.7 2.9-15.2-.1-9.8-1.7zm-.8-3.6s-1.4 1 .8 1.3c2.9.3 5.2.3 9.1-.4 0 0 .5.5 1.4.8-8.1 2.4-17.2.2-11.3-1.7z"/><path fill="#f89820" d="M15 9.1c1.6 1.9-.4 3.5-.4 3.5s4-2 2.1-4.6c-1.7-2.4-3-3.6 4.1-7.7 0 0-11.2 2.8-5.8 8.8z"/><path fill="#f89820" d="M20.7 20.4s.9.7-1 1.3c-3.7 1.1-15.4 1.4-18.7 0-1.2-.5.9-1.1 1.6-1.3.7-.2 1.1-.1 1.1-.1-1.2-.9-8 1.7-3.4 2.5 12.4 2.1 22.6-1 20.4-2.4zM9.4 10.8s-5.6 1.3-2 1.8c1.5.2 4.5.1 7.3-.1 2.3-.2 4.6-.6 4.6-.6s-.8.3-1.4.7c-5.6 1.5-16.3.8-13.2-.7 2.6-1.3 4.7-1.1 4.7-1.1zm8.5 4.7c5.7-3 3-5.9 1.2-5.5-.4.1-.6.2-.6.2s.2-.3.5-.4c3.9-1.4 6.9 4-1.2 5.9 0-.1.1-.1.1-.2z"/></svg>`,
  cpp: `<svg width="20" height="20" viewBox="0 0 24 24"><path fill="#00599C" d="M22.4 7.3c0-.4-.2-.8-.4-1-.2-.1-9.4-5.4-9.6-5.5-.3-.1-.6-.1-.9 0-.2.1-9.4 5.4-9.6 5.5-.3.2-.4.6-.4 1v11c0 .4.2.8.4 1 .2.1 9.4 5.4 9.6 5.5.2.1.4.1.5.1s.3 0 .5-.1c.2-.1 9.4-5.4 9.6-5.5.3-.2.4-.6.4-1v-11z"/><path fill="#fff" d="M12 17.5c-3 0-5.4-2.4-5.4-5.5s2.4-5.5 5.4-5.5c1.8 0 3.4.9 4.4 2.3l-2.3 1.3c-.5-.7-1.3-1.2-2.1-1.2-1.5 0-2.7 1.4-2.7 3.1s1.2 3.1 2.7 3.1c.9 0 1.6-.4 2.2-1.2l2.3 1.3c-1 1.4-2.6 2.3-4.5 2.3z"/><path fill="#fff" d="M18.9 11.2h-1v1h1v1h1v-1h1v-1h-1v-1h-1v1zm3.4 0h-1v1h1v1h1v-1h1v-1h-1v-1h-1v1z"/></svg>`,
  go: `<svg width="20" height="20" viewBox="0 0 24 24"><path fill="#00ACD7" d="M1.8 12.3c0-.1.1-.2.2-.2h4.4c.1 0 .2.1.1.2l-.3.5c0 .1-.2.2-.3.2H1.5c-.1 0-.2-.1-.1-.2l.4-.5zM0 13.8c0-.1.1-.2.2-.2h5.5c.1 0 .2.1.1.3l-.3.5c0 .1-.2.2-.3.2H0c-.1 0-.1-.1-.1-.2l.1-.6zM3.1 15.3c0-.1.1-.2.2-.2h3.9c.1 0 .1.1.1.2l-.1.5c0 .1-.1.2-.2.2H3.4c-.1 0-.2-.1-.1-.2l-.2-.5z"/><path fill="#00ACD7" d="M15.6 12.1c-1.2.3-2 .5-3.2.8-.3.1-.3.1-.5-.2-.3-.3-.5-.5-.9-.7-1.2-.6-2.4-.4-3.5.3-1.3.8-2 2-2 3.6 0 1.5 1 2.8 2.5 3 1.3.2 2.4-.2 3.3-1.2.2-.2.4-.5.6-.8H8.6c-.3 0-.4-.2-.3-.5.2-.5.6-1.3.8-1.7.1-.1.2-.3.4-.3h5.6c-.1.7-.1 1.5-.2 2.2-.3 1.5-.9 2.9-1.9 4-1.6 1.9-3.6 2.4-6 2-2.1-.4-3.6-1.6-4.1-3.7-.4-1.8 0-3.4 1.1-4.9 1.2-1.6 2.7-2.4 4.6-2.7 1.6-.3 3.1-.1 4.4.9.9.6 1.5 1.5 1.8 2.6-.2 0-.2.1-.3.1z"/></svg>`,
};

function langIcon(lang) {
  return LANGUAGE_ICONS[lang] || `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M7 3h7l4 4v14a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z" stroke="#888" stroke-width="1.6"/></svg>`;
}

async function loadHistoryFromBackend() {
  const session = getSession();
  const tbody = document.getElementById('history-table-body');

  if (!session) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-gray-500 text-sm py-8">Please log in to see your analysis history.</td></tr>`;
    document.getElementById('history-count').textContent = '';
    return;
  }

  tbody.innerHTML = `<tr><td colspan="4" class="text-center text-gray-500 text-sm py-8">Loading...</td></tr>`;

  try {
    const res = await fetch(API_HISTORY_URL, {
      headers: { 'Authorization': `Bearer ${session.token}` },
    });
    const data = await res.json();

    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center text-red-400 text-sm py-8">${data.error || 'Could not load history.'}</td></tr>`;
      return;
    }

    analysisHistoryData = (data.history || []).map(row => ({
      id: row.id,
      file: row.file_name,
      lang: row.language,
      score: row.quality_score,
      issues: row.total_issues,
      date: row.created_at,
    }));

    renderHistoryTable();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-red-400 text-sm py-8">Could not reach the backend.</td></tr>`;
  }
}

function renderHistoryTable() {
  const tbody = document.getElementById('history-table-body');
  const searchVal = (document.getElementById('history-search').value || '').toLowerCase();
  const langVal = (document.getElementById('history-lang-filter').value || '').toLowerCase();

  const filtered = analysisHistoryData.filter(row => {
    const matchesSearch = (row.file || '').toLowerCase().includes(searchVal);
    const matchesLang = !langVal || (row.lang || '').toLowerCase() === langVal;
    return matchesSearch && matchesLang;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-gray-500 text-sm py-8">No analyses yet. Run one from "New Analysis"!</td></tr>`;
    document.getElementById('history-count').textContent = '';
    return;
  }

  const scoreColorClass = (score) => {
    if (score >= 75) return 'text-emerald-400';
    if (score >= 50) return 'text-amber-400';
    return 'text-red-400';
  };

  tbody.innerHTML = filtered.map(row => `
    <tr class="border-b border-border/60 hover:bg-cardhi/60 transition">
      <td class="py-3 px-5">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-card border border-border flex items-center justify-center shrink-0">
            ${langIcon(row.lang)}
          </div>
          <div>
            <div class="text-gray-200 font-medium">${row.file}</div>
            <div class="text-xs ${scoreColorClass(row.score)}">${row.score}/100 • ${row.issues} issues</div>
          </div>
        </div>
      </td>
      <td class="py-3 px-4 text-gray-400 capitalize">${row.lang}</td>
      <td class="py-3 px-4 text-gray-500">${row.date}</td>
      <td class="py-3 px-5">
        <div class="flex items-center gap-2">
          <button data-view-report="${row.id}" class="text-xs font-medium px-3 py-1.5 rounded-lg border border-purple-500/40 text-purple-light hover:bg-purple-500/10 flex items-center gap-1.5">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.8"/></svg>
            View Report
          </button>
          <button data-compare-report="${row.id}" class="text-xs font-medium px-3 py-1.5 rounded-lg border border-border text-gray-300 hover:bg-cardhi flex items-center gap-1.5">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M8 9l-4 3 4 3M16 9l4 3-4 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Compare
          </button>
        </div>
      </td>
    </tr>
  `).join('');

  document.getElementById('history-count').textContent = `Showing ${filtered.length} of ${analysisHistoryData.length} reports`;

  tbody.querySelectorAll('[data-view-report]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await viewHistoricalReport(btn.dataset.viewReport);
    });
  });

  tbody.querySelectorAll('[data-compare-report]').forEach(btn => {
    btn.addEventListener('click', async () => {
      await viewHistoricalCompare(btn.dataset.compareReport);
    });
  });
}


async function viewHistoricalReport(analysisId) {
  const session = getSession();
  if (!session) return;

  try {
    const res = await fetch(`${API_HISTORY_URL}/${analysisId}`, {
      headers: { 'Authorization': `Bearer ${session.token}` },
    });
    const data = await res.json();

    if (!res.ok) {
      alert(data.error || 'Could not load this report.');
      return;
    }

    liveAnalysisResult = data;
    renderLiveReport(data);
    renderCompareCode(data, data.original_code || '');  // original code isn't stored separately in history yet

    document.querySelectorAll('[data-nav]').forEach(i => i.classList.remove('active'));
    const reportsNav = document.querySelector('[data-page="reports"]');
    if (reportsNav) reportsNav.classList.add('active');
    showPage('reports');
  } catch (err) {
    alert('Could not reach the backend.');
  }
}

async function viewHistoricalCompare(analysisId) {
  const session = getSession();
  if (!session) return;

  try {
    const res = await fetch(`${API_HISTORY_URL}/${analysisId}`, {
      headers: { 'Authorization': `Bearer ${session.token}` },
    });
    const data = await res.json();

    if (!res.ok) {
      alert(data.error || 'Could not load this report.');
      return;
    }

    liveAnalysisResult = data;
    renderLiveReport(data);
    renderCompareCode(data, data.original_code || ''); // original code isn't stored separately in history yet

    document.querySelectorAll('[data-nav]').forEach(i => i.classList.remove('active'));
    const compareNav = document.querySelector('[data-page="compare-code"]');
    if (compareNav) compareNav.classList.add('active');
    showPage('compare-code');
  } catch (err) {
    alert('Could not reach the backend.');
  }
}


document.getElementById('history-search').addEventListener('input', renderHistoryTable);
document.getElementById('history-lang-filter').addEventListener('change', renderHistoryTable);

// Load history whenever the user navigates to the Analysis History page
const historyNavLink = document.querySelector('[data-page="analysis-history"]');
if (historyNavLink) {
  historyNavLink.addEventListener('click', loadHistoryFromBackend);
}

/* =============================================
   REPORTS PAGE — issues data + details panel
   (static demo data — used as fallback when there's no live result yet)
============================================= */
const reportIssues = [
  {
    id: 1, title: 'Hardcoded value detected', category: 'security', severity: 'Critical',
    line: 23, description: 'Hardcoding sensitive information such as passwords, API keys, or secrets in the source code can lead to security vulnerabilities.',
    original: `21  def connect():
22      username = "admin"
23      password = "admin123"  # Hardcoded password
24      db = mysql.connect(host="localhost", user=username,
25              password=password)`,
    recommendation: 'Use environment variables or secure credential management instead of hardcoding.',
    fixed: `21  import os
22  def connect():
23      username = os.getenv("DB_USER")
24      password = os.getenv("DB_PASSWORD")
25      db = mysql.connect(host="localhost", user=username, password=password)`,
  },
  {
    id: 2, title: 'SQL Injection vulnerability', category: 'security', severity: 'High',
    line: 45, description: 'Building SQL queries via string concatenation allows attackers to inject arbitrary SQL and access or modify data they should not.',
    original: `17  query = "SELECT * FROM users WHERE username = '" + username + "'"
18  cursor.execute(query)`,
    recommendation: 'Use parameterized queries so user input is never directly concatenated into SQL.',
    fixed: `17  query = "SELECT * FROM users WHERE username = %s"
18  cursor.execute(query, (username,))`,
  },
  {
    id: 3, title: 'Inefficient loop detected', category: 'performance', severity: 'High',
    line: 67, description: 'A nested loop here runs in O(n²) time, which will slow down significantly as input size grows.',
    original: `for i in range(len(nums)):
    for j in range(i+1, len(nums)):
        if nums[i] + nums[j] == 0:
            result.append([nums[i], nums[j]])`,
    recommendation: 'Use a hash set to track seen values and reduce this to a single O(n) pass.',
    fixed: `seen = set()
for num in nums:
    complement = -num
    if complement in seen:
        result.append((num, complement))
    else:
        seen.add(num)`,
  },
  {
    id: 4, title: "Unused variable 'temp'", category: 'style', severity: 'Medium',
    line: 12, description: "The variable 'temp' is declared but never used, which adds clutter and can confuse future readers.",
    original: `temp = calculate_value()
return result`,
    recommendation: 'Remove the unused variable, or use it if it was meant to hold intermediate state.',
    fixed: `return result`,
  },
  {
    id: 5, title: 'Function is too long (45 lines)', category: 'style', severity: 'Medium',
    line: 89, description: 'This function handles too many responsibilities in one place, making it harder to test and maintain.',
    original: `def process_everything(data):
    # 45 lines of mixed validation, transformation and saving...`,
    recommendation: 'Split into smaller functions: validate_data(), transform_data(), save_data().',
    fixed: `def process_everything(data):
    validate_data(data)
    transformed = transform_data(data)
    save_data(transformed)`,
  },
  {
    id: 6, title: 'Inefficient list comprehension', category: 'performance', severity: 'Low',
    line: 101, description: 'A list comprehension is used purely for its side effects, which is misleading and wastes memory.',
    original: `[process(item) for item in items]`,
    recommendation: 'Use a plain for-loop when you only care about side effects, not the resulting list.',
    fixed: `for item in items:
    process(item)`,
  },
  {
    id: 7, title: 'Missing docstring in function', category: 'style', severity: 'Low',
    line: 5, description: 'Public functions without docstrings are harder for other developers to understand and use correctly.',
    original: `def connect():
    ...`,
    recommendation: 'Add a docstring describing parameters, return value and any exceptions raised.',
    fixed: `def connect():
    """Establish and return a MySQL database connection."""
    ...`,
  },
  {
    id: 8, title: 'Broad exception handling', category: 'security', severity: 'High',
    line: 134, description: 'Catching all exceptions with a bare except can hide real bugs and security issues.',
    original: `try:
    do_something()
except:
    pass`,
    recommendation: 'Catch specific exception types and handle or log them appropriately.',
    fixed: `try:
    do_something()
except (ValueError, ConnectionError) as e:
    log.error(e)`,
  },
];

const severityBadgeClass = {
  Critical: 'badge-critical',
  High: 'badge-high',
  Medium: 'badge-medium',
  Low: 'badge-low',
};

let currentReportTab = 'all';

function renderReportIssuesList() {
  const list = document.getElementById('report-issues-list');
  const filtered = currentReportTab === 'all'
    ? reportIssues
    : reportIssues.filter(i => i.category === currentReportTab);

  list.innerHTML = filtered.map(issue => `
    <div data-issue-id="${issue.id}" class="issue-item rounded-lg p-3 flex items-center justify-between gap-3 ${issue.severity === 'Critical' ? 'issue-item-critical' : ''}">
      <div>
        <div class="text-gray-200 text-sm font-medium">${issue.title}</div>
        <div class="text-gray-500 text-xs mt-0.5">${issue.category.charAt(0).toUpperCase() + issue.category.slice(1)} • Line ${issue.line}</div>
      </div>
      <span class="${severityBadgeClass[issue.severity]} text-xs font-medium px-2 py-0.5 rounded-md shrink-0">${issue.severity}</span>
    </div>
  `).join('');

  list.querySelectorAll('[data-issue-id]').forEach(el => {
    el.addEventListener('click', () => showIssueDetail(Number(el.dataset.issueId)));
  });

  // auto-select the first issue in the filtered list
  if (filtered.length > 0) showIssueDetail(filtered[0].id);
}

function showIssueDetail(issueId) {
  const issue = reportIssues.find(i => i.id === issueId);
  if (!issue) return;

  document.querySelectorAll('#report-issues-list [data-issue-id]').forEach(el => {
    el.classList.toggle('issue-item-active', Number(el.dataset.issueId) === issueId);
  });

  document.getElementById('issue-detail-title').textContent = issue.title;
  document.getElementById('issue-detail-meta').textContent = `${issue.category.charAt(0).toUpperCase() + issue.category.slice(1)} • Line ${issue.line}`;
  const sevBadge = document.getElementById('issue-detail-severity');
  sevBadge.textContent = issue.severity;
  sevBadge.className = `${severityBadgeClass[issue.severity]} text-xs font-medium px-2 py-0.5 rounded-md`;
  document.getElementById('issue-detail-description').textContent = issue.description;
  document.getElementById('issue-detail-original').textContent = issue.original;
  document.getElementById('issue-detail-recommendation').textContent = issue.recommendation;
  document.getElementById('issue-detail-fixed').textContent = issue.fixed;
}

document.querySelectorAll('[data-report-tab]').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('[data-report-tab]').forEach(t => t.classList.remove('report-tab-active'));
    tab.classList.add('report-tab-active');
    currentReportTab = tab.dataset.reportTab;

    // Use live backend data if we have it, otherwise fall back to the static demo data
    if (liveAnalysisResult) {
      renderLiveIssuesList();
    } else {
      renderReportIssuesList();
    }
  });
});

document.getElementById('report-back-btn').addEventListener('click', () => {
  document.querySelectorAll('[data-nav]').forEach(i => i.classList.remove('active'));
  const historyNav = document.querySelector('[data-page="analysis-history"]');
  if (historyNav) historyNav.classList.add('active');
  showPage('analysis-history');
});

renderReportIssuesList();

/* ---------- Small ring charts on the Reports page (quality + security) ---------- */
let qualityRingChart = null;

function qualityLabel(score) {
  if (score >= 90) return { text: 'Excellent Quality', color: 'text-emerald-400', bg: 'bg-emerald-500/10', ring: '#22c55e' };
  if (score >= 75) return { text: 'Good Quality', color: 'text-emerald-400', bg: 'bg-emerald-500/10', ring: '#22c55e' };
  if (score >= 50) return { text: 'Needs Improvement', color: 'text-amber-400', bg: 'bg-amber-500/10', ring: '#f59e0b' };
  return { text: 'Poor Quality', color: 'text-red-400', bg: 'bg-red-500/10', ring: '#ef4444' };
}

function renderQualityRing(score) {
  const canvas = document.getElementById('reportQualityRing');
  const { text, color, ring, bg } = qualityLabel(score);

  document.getElementById('report-quality-score').textContent = score;
  document.getElementById('report-quality-ring-label').textContent = score;
  const labelEl = document.getElementById('report-quality-label');
  labelEl.textContent = text;
  labelEl.className = `text-xs font-medium mt-2 inline-flex items-center gap-1.5 px-2 py-1 rounded-md ${color} ${bg}`;

  try {
    if (qualityRingChart) qualityRingChart.destroy();
    qualityRingChart = new Chart(canvas, {
      type: 'doughnut',
      data: { datasets: [{ data: [score, 100 - score], backgroundColor: [ring, '#1c1a2e'], borderWidth: 0 }] },
      options: { responsive: false, cutout: '72%', plugins: { legend: { display: false }, tooltip: { enabled: false } } }
    });
  } catch (err) {
    console.warn('Quality ring could not load:', err);
  }
}

function renderSeverityAndCategoryBreakdown(data) {
  const sev = data.severity_summary || { Critical: 0, High: 0, Medium: 0, Low: 0 };
  const critical = sev.Critical || 0;
  const high = sev.High || 0;
  const medium = sev.Medium || 0;
  const low = sev.Low || 0;
  const total = critical + high + medium + low;

  document.getElementById('severity-critical-count').textContent = critical;
  document.getElementById('severity-high-count').textContent = high;
  document.getElementById('severity-medium-count').textContent = medium;
  document.getElementById('severity-low-count').textContent = low;
  document.getElementById('severity-total-label').textContent = `${total} total`;

  const pct = (n) => total > 0 ? (n / total * 100).toFixed(1) : 0;
  document.getElementById('severity-bar-critical').style.width = pct(critical) + '%';
  document.getElementById('severity-bar-high').style.width = pct(high) + '%';
  document.getElementById('severity-bar-medium').style.width = pct(medium) + '%';
  document.getElementById('severity-bar-low').style.width = pct(low) + '%';

  const categoryCounts = { bug: 0, security: 0, performance: 0, style: 0 };
  (data.issues || []).forEach(i => {
    if (categoryCounts[i.category] !== undefined) categoryCounts[i.category]++;
  });
  document.getElementById('category-bug-count').textContent = categoryCounts.bug;
  document.getElementById('category-security-count').textContent = categoryCounts.security;
  document.getElementById('category-performance-count').textContent = categoryCounts.performance;
  document.getElementById('category-style-count').textContent = categoryCounts.style;
}

/* =============================================
   HELP & SUPPORT PAGE — FAQ accordion + contact form
============================================= */
const faqData = [
  { q: 'How does the AI code analysis work?', a: 'We parse your code, run it through static analysis rules and an AI model trained on common bugs, security issues and performance patterns, then generate a report with fixes.' },
  { q: 'Which programming languages are supported?', a: 'We currently support 50+ languages including Python, JavaScript, Java, C++, Go and more. Check "View supported languages" on the New Analysis page for the full list.' },
  { q: 'Is my code stored or shared with anyone?', a: 'Your code is only used to generate your analysis report and is never shared with third parties.' },
  { q: 'How do I upgrade to Pro?', a: 'Click "Upgrade Now" in the sidebar to see Pro plans with advanced analysis and priority scans.' },
];

function renderFaqList() {
  const list = document.getElementById('faq-list');
  list.innerHTML = faqData.map((item, i) => `
    <div class="border-b border-border pb-2">
      <div data-faq-toggle="${i}" class="faq-question flex items-center justify-between py-2 text-sm text-gray-200 font-medium">
        <span>${item.q}</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" class="faq-chevron shrink-0 transition-transform"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
      <div data-faq-answer="${i}" class="hidden text-xs text-gray-500 pb-2 leading-relaxed">${item.a}</div>
    </div>
  `).join('');

  list.querySelectorAll('[data-faq-toggle]').forEach(el => {
    el.addEventListener('click', () => {
      const idx = el.dataset.faqToggle;
      const answer = list.querySelector(`[data-faq-answer="${idx}"]`);
      const chevron = el.querySelector('.faq-chevron');
      answer.classList.toggle('hidden');
      chevron.style.transform = answer.classList.contains('hidden') ? 'rotate(0deg)' : 'rotate(180deg)';
    });
  });
}
renderFaqList();

document.getElementById('support-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const msg = document.getElementById('support-form-message');
  msg.textContent = "Thanks! We've received your message and will get back to you soon.";
  msg.classList.remove('hidden');
  e.target.reset();
});

/* =============================================
   DASHBOARD — clickable shortcuts to other pages
============================================= */
function goToPage(pageKey) {
  document.querySelectorAll('[data-nav]').forEach(i => i.classList.remove('active'));
  const navLink = document.querySelector(`[data-page="${pageKey}"]`);
  if (navLink) navLink.classList.add('active');
  showPage(pageKey);
}

document.getElementById('dashboard-code-comparison-link').addEventListener('click', () => {
  goToPage('compare-code');
});

document.getElementById('topbar-new-analysis-btn').addEventListener('click', () => {
  goToPage('new-analysis');
});

document.getElementById('issue-summary-view-all').addEventListener('click', (e) => {
  e.preventDefault();
  goToPage('reports');
});

document.getElementById('recent-analysis-view-all').addEventListener('click', (e) => {
  e.preventDefault();
  goToPage('analysis-history');
});
