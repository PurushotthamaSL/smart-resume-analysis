// Dashboard interactivity: Chart.js visualization, skill filtering, and dynamic role gap inspection

document.addEventListener('DOMContentLoaded', () => {
  initProgressBars();
  initRadarChart();
  initRoleSelection();
  initSkillFilters();
});

// 0. Dynamic Progress Bars Animation
function initProgressBars() {
  document.querySelectorAll('.role-progress-bar').forEach(bar => {
    const pct = parseFloat(bar.dataset.progress || '0');
    bar.style.width = `${pct}%`;
  });
}

// 1. Chart.js Radar Chart
function initRadarChart() {
  const radarCanvas = document.getElementById('roleRadarChart');
  if (!radarCanvas || !window.dashboardData || !window.dashboardData.matches) return;

  const matches = window.dashboardData.matches.slice(0, 5);
  if (matches.length === 0) return;

  const labels = matches.map(m => m.job_title);
  const dataScores = matches.map(m => m.match_percentage);

  new Chart(radarCanvas, {
    type: 'radar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Candidate Match %',
          data: dataScores,
          backgroundColor: 'rgba(99, 102, 241, 0.25)',
          borderColor: '#818cf8',
          pointBackgroundColor: '#38bdf8',
          pointBorderColor: '#ffffff',
          pointHoverBackgroundColor: '#ffffff',
          pointHoverBorderColor: '#818cf8',
          borderWidth: 2,
          pointRadius: 4,
        },
        {
          label: 'Target Benchmark (100%)',
          data: labels.map(() => 100),
          backgroundColor: 'transparent',
          borderColor: 'rgba(148, 163, 184, 0.2)',
          borderDash: [4, 4],
          borderWidth: 1,
          pointRadius: 0,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            color: '#94a3b8',
            font: { size: 11, family: 'Inter' }
          }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#f8fafc',
          bodyColor: '#cbd5e1',
          borderColor: '#334155',
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: function(ctx) {
              return `${ctx.dataset.label}: ${ctx.raw}%`;
            }
          }
        }
      },
      scales: {
        r: {
          angleLines: { color: 'rgba(255, 255, 255, 0.08)' },
          grid: { color: 'rgba(255, 255, 255, 0.08)' },
          pointLabels: {
            color: '#cbd5e1',
            font: { size: 11, weight: '500' }
          },
          suggestedMin: 20,
          suggestedMax: 100,
          ticks: {
            color: '#64748b',
            backdropColor: 'transparent',
            stepSize: 20
          }
        }
      }
    }
  });
}

// 2. Interactive Role Selection & Skill Gap Breakdown
function initRoleSelection() {
  const roleCards = document.querySelectorAll('.role-card');
  if (roleCards.length > 0) {
    // Select the first role by default
    const firstRole = roleCards[0];
    const roleId = firstRole.dataset.roleId;
    selectRole(roleId);
  }
}

function selectRole(roleId) {
  const card = document.getElementById(`role-card-${roleId}`);
  if (!card) return;

  // Toggle visual active state
  document.querySelectorAll('.role-card').forEach(c => {
    c.classList.remove('bg-indigo-950/40', 'border-indigo-500/50', 'shadow-lg', 'shadow-indigo-900/20');
    c.classList.add('bg-slate-900/50', 'border-slate-800');
  });

  card.classList.remove('bg-slate-900/50', 'border-slate-800');
  card.classList.add('bg-indigo-950/40', 'border-indigo-500/50', 'shadow-lg', 'shadow-indigo-900/20');

  // Extract data from card attributes
  const title = card.dataset.roleTitle || 'Target Role';
  const matchPct = card.dataset.matchPct || '0';
  let matched = [];
  let missing = [];
  let matchedPref = [];

  try {
    matched = JSON.parse(card.dataset.matched || '[]');
  } catch (e) { matched = []; }

  try {
    missing = JSON.parse(card.dataset.missing || '[]');
  } catch (e) { missing = []; }

  try {
    matchedPref = JSON.parse(card.dataset.matchedPref || '[]');
  } catch (e) { matchedPref = []; }

  // Update Gap Analysis Section
  const gapTitle = document.getElementById('gap-role-title');
  const gapBadge = document.getElementById('gap-role-match-badge');
  const matchedCount = document.getElementById('gap-matched-count');
  const missingCount = document.getElementById('gap-missing-count');
  const matchedTags = document.getElementById('gap-matched-tags');
  const missingTags = document.getElementById('gap-missing-tags');
  const preferredTags = document.getElementById('gap-preferred-tags');

  if (gapTitle) gapTitle.textContent = title;
  if (gapBadge) {
    gapBadge.textContent = `${matchPct}% Fit`;
    if (parseFloat(matchPct) >= 75) {
      gapBadge.className = 'px-3 py-1 rounded-lg text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
    } else if (parseFloat(matchPct) >= 50) {
      gapBadge.className = 'px-3 py-1 rounded-lg text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30';
    } else {
      gapBadge.className = 'px-3 py-1 rounded-lg text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30';
    }
  }

  if (matchedCount) matchedCount.textContent = matched.length;
  if (missingCount) missingCount.textContent = missing.length;

  // Render Matched Tags
  if (matchedTags) {
    if (matched.length > 0) {
      matchedTags.innerHTML = matched.map(skill => `
        <span class="px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-800/80 flex items-center space-x-1.5">
          <i class="fa-solid fa-check text-[10px] text-emerald-400"></i>
          <span>${skill}</span>
        </span>
      `).join('');
    } else {
      matchedTags.innerHTML = '<span class="text-xs text-slate-500">None of the core required skills were detected.</span>';
    }
  }

  // Render Missing Tags
  if (missingTags) {
    if (missing.length > 0) {
      missingTags.innerHTML = missing.map(skill => `
        <span class="px-2.5 py-1 rounded-lg text-xs font-medium bg-rose-950/60 text-rose-300 border border-rose-800/80 flex items-center space-x-1.5">
          <i class="fa-solid fa-xmark text-[10px] text-rose-400"></i>
          <span>${skill}</span>
        </span>
      `).join('');
    } else {
      missingTags.innerHTML = '<span class="text-xs text-emerald-400 font-medium">All required skills are met!</span>';
    }
  }

  // Render Preferred Tags
  if (preferredTags) {
    if (matchedPref.length > 0) {
      preferredTags.innerHTML = matchedPref.map(skill => `
        <span class="px-2.5 py-1 rounded-lg text-xs font-medium bg-cyan-950/60 text-cyan-300 border border-cyan-800/80 flex items-center space-x-1.5">
          <i class="fa-solid fa-star text-[10px] text-cyan-400"></i>
          <span>${skill}</span>
        </span>
      `).join('');
    } else {
      preferredTags.innerHTML = '<span class="text-xs text-slate-500">No bonus preferred skills matched for this role.</span>';
    }
  }
}

// 3. Extracted Skills Search & Filter
function initSkillFilters() {
  const searchInput = document.getElementById('skill-search');
  const filterBtns = document.querySelectorAll('.skill-filter-btn');
  const skillPills = document.querySelectorAll('.skill-pill');

  let activeCategory = 'all';
  let searchQuery = '';

  function filterSkills() {
    skillPills.forEach(pill => {
      const name = pill.dataset.skillName || '';
      const cat = pill.dataset.skillCategory || '';

      const matchesCat = (activeCategory === 'all' || cat === activeCategory);
      const matchesSearch = (!searchQuery || name.includes(searchQuery));

      if (matchesCat && matchesSearch) {
        pill.classList.remove('hidden');
      } else {
        pill.classList.add('hidden');
      }
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      filterSkills();
    });
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => {
        b.classList.remove('bg-indigo-600', 'text-white');
        b.classList.add('bg-slate-800', 'text-slate-400');
      });

      btn.classList.remove('bg-slate-800', 'text-slate-400');
      btn.classList.add('bg-indigo-600', 'text-white');

      activeCategory = btn.dataset.cat;
      filterSkills();
    });
  });
}
