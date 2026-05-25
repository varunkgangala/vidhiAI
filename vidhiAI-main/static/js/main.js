// VidhiAI – main.js

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initUploadZone();
  initAnalyzeForm();
  animateScoreRings();
  initTableRowLinks();
  autoDismissFlash();
});

// ── Tab switching (analyze page) ──
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById(target);
      if (panel) panel.classList.add('active');
    });
  });
}

// ── Drag & drop upload zone ──
function initUploadZone() {
  const zone = document.querySelector('.upload-zone');
  if (!zone) return;

  const input = zone.querySelector('input[type="file"]');
  const label = zone.querySelector('.upload-filename');

  if (input) {
    input.addEventListener('change', () => {
      if (input.files[0] && label) {
        label.textContent = '📄 ' + input.files[0].name;
        label.style.color = 'var(--navy)';
        label.style.fontWeight = '600';
      }
    });
  }

  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files[0] && input) {
      input.files = e.dataTransfer.files;
      if (label) {
        label.textContent = '📄 ' + e.dataTransfer.files[0].name;
        label.style.color = 'var(--navy)';
        label.style.fontWeight = '600';
      }
    }
  });
}

// ── Show loading overlay on form submit ──
function initAnalyzeForm() {
  const form = document.getElementById('analyzeForm');
  const overlay = document.getElementById('loadingOverlay');
  if (!form || !overlay) return;

  const steps = [
    'Extracting contract text…',
    'Fetching applicable laws…',
    'Building compliance prompt…',
    'Running AI analysis…',
    'Generating report…'
  ];
  let stepIdx = 0;
  const stepEl = overlay.querySelector('#loadingStep');

  form.addEventListener('submit', e => {
    // Basic validation
    const file = document.getElementById('contractFile');
    const text = document.getElementById('contractText');
    const activeTab = document.querySelector('.tab-btn.active');
    const isUploadTab = activeTab && activeTab.dataset.tab === 'tab-upload';

    if (isUploadTab) {
      if (!file || !file.files[0]) {
        e.preventDefault();
        alert('Please select a file to upload.');
        return;
      }
    } else {
      if (!text || text.value.trim().length < 50) {
        e.preventDefault();
        alert('Please paste at least 50 characters of contract text.');
        return;
      }
    }

    overlay.classList.add('show');
    if (stepEl) {
      const interval = setInterval(() => {
        stepIdx = (stepIdx + 1) % steps.length;
        stepEl.textContent = steps[stepIdx];
      }, 1200);
      form._interval = interval;
    }
  });
}

// ── Animate SVG compliance score rings ──
function animateScoreRings() {
  document.querySelectorAll('.score-ring').forEach(ring => {
    const fill = ring.querySelector('.fill');
    if (!fill) return;
    const score = parseInt(ring.dataset.score || '0', 10);
    const r = 55;
    const circumference = 2 * Math.PI * r;
    const fraction = score / 100;
    fill.style.strokeDasharray = `${circumference * fraction} ${circumference}`;
  });
}

// ── Make table rows clickable ──
function initTableRowLinks() {
  document.querySelectorAll('tr[data-href]').forEach(row => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', () => { window.location = row.dataset.href; });
  });
}

// ── Auto-dismiss flash messages after 5s ──
function autoDismissFlash() {
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s, max-height 0.5s';
      el.style.opacity = '0';
      el.style.maxHeight = '0';
      el.style.padding = '0';
      el.style.margin = '0';
    }, 5000);
  });
}

// ── Confirm delete ──
function confirmDelete(formId) {
  if (confirm('Are you sure you want to delete this report? This cannot be undone.')) {
    document.getElementById(formId).submit();
  }
}
