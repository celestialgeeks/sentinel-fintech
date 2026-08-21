/* ============================================================
   SENTINEL — Deck JavaScript
   Navigation, animations, and interactive visuals
   ============================================================ */

// ============================================================
// Slide Navigation & State
// ============================================================
const slides = Array.from(document.querySelectorAll('.slide'));
const totalSlides = slides.length;
let currentSlide = 0;
const progressFill = document.getElementById('progressFill');
const currentSlideEl = document.getElementById('currentSlide');
const totalSlidesEl = document.getElementById('totalSlides');
const speakerNotes = document.getElementById('speakerNotes');
const notesContent = document.getElementById('notesContent');

totalSlidesEl.textContent = totalSlides;

const speakerNotesData = [
  `Welcome. Sentinel is an AI-powered FinTech compliance platform built as a B.Tech Major Project at IPS Academy, Indore. It unifies three critical pillars — transaction screening, fraud detection, and merchant onboarding — on a single event-streaming backbone. Today I'll walk you through the problem, our solution, architecture, and results.`,
  `The compliance crisis is real. UPI alone does 15 billion transactions a month. Legacy rule engines hit 94% false positives. Synthetic identity fraud surged 311% in one year. Regulators like RBI and OFAC now demand real-time monitoring with explainability. The average major bank fine is $2.7 billion. We're drowning in volume and noise.`,
  `Why do current systems fail? Three categories: Legacy rule engines are rigid and miss aliasing. Legacy ML pipelines use static features and miss fraud rings. Commercial RegTech SaaS is closed, expensive, and unexplainable. The market is fragmented. Sentinel is open, unified, and explainable by design.`,
  `Our five objectives: One, unify AML, fraud, and KYB. Two, cut false positives by 50% using vector matching and LLM entity resolution. Three, detect fraud rings with GNNs at 95%+ AUC. Four, onboard low-risk merchants in under 5 minutes via RAG. Five, deliver a production-grade open alternative to closed SaaS.`,
  `Sentinel has three pillars. Pillar 1: Transaction Screening with 98% recall. Pillar 2: Fraud Detection with 97.5% accuracy via GNNs. Pillar 3: Merchant Approval in under 5 minutes. All three share a Kafka event bus so risk context flows in real time — screening hits enrich fraud profiles, fraud signals tighten merchant scoring.`,
  `Six-layer architecture. Client layer talks to FastAPI gateway. Kafka event bus connects screening engine, fraud engine, and merchant engine. Data layer: PostgreSQL for ACID, Milvus for vectors, Neo4j for graphs. 10 Docker services, 42 tests passing, 52% coverage.`,
  `Tech stack: FastAPI, Python 3.11, Kafka, Redis, PostgreSQL, Milvus, Neo4j. AI with LangChain, LlamaIndex, HuggingFace. ML with XGBoost, PyTorch Geometric. OCR dual-engine. Infra with Docker, Kubernetes, Prometheus, Grafana. GitHub Actions CI/CD.`,
  `Pillar 1: Transaction Screening. Five stages — ingest, NER with LLM entity resolution, vector fuzzy match in Milvus, AML rule engine, hybrid decision. The demo shows "Mohammed Ahmed" flagged against "Mohammed Al-Ahmed" at 0.94 similarity. 47K screened today, 12 hits, 891 false positives blocked. OpenSanctions Pairs benchmark: 98.23% F1.`,
  `Pillar 2: Fraud Detection. Two layers — detection with GNN on Neo4j for fraud rings, plus XGBoost for tabular signals. The differentiator: agentic triage. An autonomous LLM agent pre-investigates high-risk alerts, correlates across transactions, devices, graph neighborhoods, and hands a summarized risk dossier to human analysts. 97.5% accuracy vs 93.2% traditional ML.`,
  `Pillar 3: Merchant Onboarding. Kanban flow: auto-approve, manual review, auto-reject. RAG extracts facts from incorporation docs, tax IDs, bank statements. Dynamic risk scoring combines document confidence, behavioral priors, network signals. 1,247 onboarded today, average 4 minutes 12 seconds. Full audit trail for regulators.`,
  `Five phases over 20 weeks. Phase 1: Foundation — repo, Docker, schemas, FastAPI. Phase 2: Screening Engine — AML rules, entity resolution, vector matching. Phase 3: Fraud Detection — behavioral profiling, GNN rings, agentic triage. Phase 4: Merchant Approval — KYB/KYC, RAG, risk scoring. Phase 5: Integration — E2E pipeline, CI/CD, monitoring, docs.`,
  `Results: 98% AML recall, 60% false positive reduction. 97.5% fraud accuracy vs 93.2% baseline. Sub-5-minute merchant onboarding. 42 tests, 52% coverage, clean Docker deploy. Research backed by arXiv papers with 200+ citations each. Federal Reserve and IJPREMS references.`,
  `Impact: Open-source alternative to closed SaaS. Explainable by design. Unifies fragmented market. Limitations: synthetic data testing, LLM latency costs, GNN cold-start needs labeled data. Future: Flink + vLLM for real-time inference, federated learning, analyst copilot, FedRAMP pathway. GitHub: celestialgeeks/sentinel-fintech. Open to collaboration.`
];

function updateSlide() {
  slides.forEach((slide, i) => {
    slide.classList.toggle('active', i === currentSlide);
  });
  currentSlideEl.textContent = currentSlide + 1;
  progressFill.style.width = `${((currentSlide + 1) / totalSlides) * 100}%`;

  // Trigger reveal animations
  const activeSlide = slides[currentSlide];
  const reveals = activeSlide.querySelectorAll('.reveal');
  reveals.forEach((el, i) => {
    el.style.transitionDelay = `${i * 100}ms`;
    requestAnimationFrame(() => el.classList.add('visible'));
  });

  // Update speaker notes
  notesContent.textContent = speakerNotesData[currentSlide] || '';

  // Initialize slide-specific visuals
  if (currentSlide === 7) initPipeline();
  if (currentSlide === 8) initFraudGraph();
  if (currentSlide === 9) initKanban();
}

function nextSlide() {
  if (currentSlide < totalSlides - 1) {
    currentSlide++;
    updateSlide();
  }
}

function prevSlide() {
  if (currentSlide > 0) {
    currentSlide--;
    updateSlide();
  }
}

function goToSlide(n) {
  if (n >= 0 && n < totalSlides) {
    currentSlide = n;
    updateSlide();
  }
}

// Keyboard navigation
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  switch (e.key) {
    case 'ArrowRight':
    case ' ':
    case 'PageDown':
      e.preventDefault();
      nextSlide();
      break;
    case 'ArrowLeft':
    case 'PageUp':
      e.preventDefault();
      prevSlide();
      break;
    case 'Home':
      e.preventDefault();
      goToSlide(0);
      break;
    case 'End':
      e.preventDefault();
      goToSlide(totalSlides - 1);
      break;
    case 'Escape':
      speakerNotes.classList.remove('open');
      break;
    case 'n':
    case 'N':
      speakerNotes.classList.toggle('open');
      break;
  }
});

// Touch/swipe support
let touchStartX = 0;
document.addEventListener('touchstart', (e) => { touchStartX = e.changedTouches[0].screenX; });
document.addEventListener('touchend', (e) => {
  const diff = e.changedTouches[0].screenX - touchStartX;
  if (Math.abs(diff) > 50) {
    diff > 0 ? prevSlide() : nextSlide();
  }
});

// ============================================================
// Slide 8: Pipeline Animation
// ============================================================
let pipelineInterval = null;
function initPipeline() {
  const stages = document.querySelectorAll('#pipelineStages .stage');
  const flow = document.getElementById('txFlow');
  if (!stages.length) return;

  // Reset
  stages.forEach(s => s.classList.remove('active', 'complete'));
  stages[0].classList.add('active');
  flow.style.opacity = '0';
  flow.style.left = '0%';

  let stageIdx = 0;
  pipelineInterval = setInterval(() => {
    stages[stageIdx].classList.remove('active');
    stages[stageIdx].classList.add('complete');
    stageIdx = (stageIdx + 1) % stages.length;
    stages[stageIdx].classList.add('active');

    // Restart flow animation
    flow.style.animation = 'none';
    flow.offsetHeight; // reflow
    flow.style.animation = 'flow-transaction 3s ease-in-out infinite';
  }, 3000);
}

function cleanupPipeline() {
  if (pipelineInterval) clearInterval(pipelineInterval);
  pipelineInterval = null;
}

// ============================================================
// Slide 9: Fraud Graph (Force-Directed)
// ============================================================
function initFraudGraph() {
  const canvas = document.getElementById('fraudGraph');
  if (!canvas || canvas.__initialized) return;

  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);
  canvas.style.width = rect.width + 'px';
  canvas.style.height = rect.height + 'px';

  // Graph data
  const nodes = [
    { id: 0, x: 0.5, y: 0.3, ring: true, label: 'A' },
    { id: 1, x: 0.3, y: 0.15, ring: true, label: 'B' },
    { id: 2, x: 0.7, y: 0.15, ring: true, label: 'C' },
    { id: 3, x: 0.5, y: 0.45, ring: true, label: 'D' },
    { id: 4, x: 0.2, y: 0.5, ring: false, label: 'E' },
    { id: 5, x: 0.8, y: 0.5, ring: false, label: 'F' },
    { id: 6, x: 0.35, y: 0.7, ring: false, label: 'G' },
    { id: 7, x: 0.65, y: 0.7, ring: false, label: 'H' },
    { id: 8, x: 0.1, y: 0.3, ring: false, label: 'I' },
    { id: 9, x: 0.9, y: 0.3, ring: false, label: 'J' },
  ];
  const edges = [
    [0,1], [0,2], [0,3], [1,4], [1,8], [2,5], [2,9], [3,6], [3,7],
    [4,8], [5,9], [6,7], [0,4], [0,5]
  ];

  let time = 0;
  function draw() {
    const w = rect.width, h = rect.height;
    ctx.clearRect(0, 0, w, h);

    // Draw edges
    edges.forEach(([a, b]) => {
      const n1 = nodes[a], n2 = nodes[b];
      ctx.beginPath();
      ctx.moveTo(n1.x * w, n1.y * h);
      ctx.lineTo(n2.x * w, n2.y * h);
      ctx.strokeStyle = 'rgba(107, 122, 153, 0.3)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });

    // Draw nodes
    nodes.forEach(node => {
      const px = node.x * w, py = node.y * h;
      const pulse = node.ring ? Math.sin(time * 3) * 3 : 0;
      const r = 14 + pulse;

      // Glow for ring nodes
      if (node.ring) {
        const gradient = ctx.createRadialGradient(px, py, 0, px, py, r + 10);
        gradient.addColorStop(0, 'rgba(255, 59, 92, 0.4)');
        gradient.addColorStop(1, 'rgba(255, 59, 92, 0)');
        ctx.beginPath();
        ctx.arc(px, py, r + 10, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fillStyle = node.ring ? '#FF3B5C' : '#00E5A8';
      ctx.fill();
      ctx.strokeStyle = node.ring ? '#FF3B5C' : '#00E5A8';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Label
      ctx.fillStyle = '#0A0E1A';
      ctx.font = 'bold 10px JetBrains Mono';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.label, px, py + 1);
    });

    time += 0.016;
    requestAnimationFrame(draw);
  }
  draw();
  canvas.__initialized = true;
}

// ============================================================
// Slide 10: Kanban Animation
// ============================================================
const merchants = [
  { name: 'Apex Trading Co', country: '🇮🇳', docs: 4, risk: 15, decision: 'approved', col: 'approved' },
  { name: 'Meridian Payments', country: '🇸🇬', docs: 4, risk: 22, decision: 'approved', col: 'approved' },
  { name: 'Nordic Fintech AB', country: '🇸🇪', docs: 4, risk: 18, decision: 'approved', col: 'approved' },
  { name: 'Sahara Commerce', country: '🇦🇪', docs: 3, risk: 45, decision: 'review', col: 'review' },
  { name: 'Pacific Rim Ltd', country: '🇭🇰', docs: 3, risk: 52, decision: 'review', col: 'review' },
  { name: 'Andes Capital', country: '🇨🇱', docs: 2, risk: 68, decision: 'review', col: 'review' },
  { name: 'Shadow Holdings', country: '🇻🇬', docs: 1, risk: 92, decision: 'rejected', col: 'rejected' },
  { name: 'Phantom Ventures', country: '🇵🇦', docs: 1, risk: 88, decision: 'rejected', col: 'rejected' },
  { name: 'Ghost Traders Inc', country: '🇧🇸', docs: 0, risk: 95, decision: 'rejected', col: 'rejected' },
];

function createMerchantCard(m) {
  const card = document.createElement('div');
  card.className = 'merchant-card';
  card.dataset.name = m.name;
  card.innerHTML = `
    <div class="merchant-name">${m.name} <span style="font-family: var(--font-body); font-size: 0.7rem; font-weight: 400; color: var(--steel);">${m.country}</span></div>
    <div class="merchant-meta">
      <span>Docs: ${m.docs}/4 verified</span>
      <span>·</span>
      <span>Risk: ${m.risk}/100</span>
    </div>
    <div class="merchant-docs">
      ${Array.from({length: 4}, (_, i) => `<span class="doc-badge ${i < m.docs ? 'verified' : 'pending'}">${i < m.docs ? '✓' : '○'}</span>`).join('')}
    </div>
    <div class="risk-gauge"><div class="risk-fill ${m.risk < 30 ? 'low' : m.risk < 60 ? 'med' : 'high'}" style="width: ${m.risk}%"></div></div>
    <span class="merchant-decision ${m.decision}">${m.decision.toUpperCase()}</span>
  `;
  return card;
}

function initKanban() {
  const cols = {
    approved: document.getElementById('colApproved'),
    review: document.getElementById('colReview'),
    rejected: document.getElementById('colRejected'),
  };
  Object.values(cols).forEach(c => { if (c) c.innerHTML = ''; });

  merchants.forEach(m => {
    if (cols[m.col]) cols[m.col].appendChild(createMerchantCard(m));
  });

  // Update counts
  document.getElementById('cntApproved').textContent = merchants.filter(m => m.col === 'approved').length;
  document.getElementById('cntReview').textContent = merchants.filter(m => m.col === 'review').length;
  document.getElementById('cntRejected').textContent = merchants.filter(m => m.col === 'rejected').length;
}

function animatePipeline() {
  const btn = document.getElementById('playPipeline');
  if (!btn) return;

  btn.disabled = true;
  btn.textContent = '⟳ Running...';

  // Simulate a few merchants moving through pipeline
  const reviewMerchants = merchants.filter(m => m.col === 'review').slice(0, 2);
  let delay = 0;

  reviewMerchants.forEach((m, i) => {
    setTimeout(() => {
      // Move from review to approved
      m.col = 'approved';
      m.decision = 'approved';
      initKanban();

      // Animate the moved card
      const cards = document.querySelectorAll('#colApproved .merchant-card');
      cards.forEach(card => {
        if (card.dataset.name === m.name) {
          card.classList.add('moving');
          setTimeout(() => card.classList.remove('moving'), 600);
        }
      });
    }, delay);
    delay += 1200;
  });

  setTimeout(() => {
    btn.disabled = false;
    btn.textContent = '▶ Play Pipeline';
  }, delay + 500);
}

document.getElementById('playPipeline')?.addEventListener('click', animatePipeline);

// ============================================================
// IntersectionObserver for reveal animations
// ============================================================
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

// ============================================================
// Print support
// ============================================================
window.addEventListener('beforeprint', () => {
  // Show all slides for printing
  slides.forEach(s => s.classList.add('active'));
});
window.addEventListener('afterprint', () => {
  slides.forEach((s, i) => s.classList.toggle('active', i === currentSlide));
});

// ============================================================
// Cleanup on slide change
// ============================================================
const originalUpdateSlide = updateSlide;
updateSlide = function() {
  cleanupPipeline();
  originalUpdateSlide();
};

// Initialize first slide
updateSlide();