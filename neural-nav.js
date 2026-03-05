(function () {
  const canvas = document.getElementById('nn-canvas');
  const ctx = canvas.getContext('2d');
  let dpr = window.devicePixelRatio || 1;
  let time = 0;

  const sections = [
    // Layer 0 — input node
    [
      { id: null, label: 'Sureh San', isDeco: true },
    ],
    // Layer 1
    [
      { id: 'about',      label: 'About',      url: 'about.html' },
      { id: 'education',  label: 'Education',  url: 'education.html' },
      { id: 'experience', label: 'Experience', url: 'experience.html' },
    ],
    // Layer 2
    [
      { id: 'projects',     label: 'Projects',     url: 'projects.html' },
      { id: 'competitions', label: 'Competitions', url: 'competitions.html' },
      { id: 'publications', label: 'Publications', url: 'publications.html' },
      { id: 'honors',       label: 'Honors',       url: 'honors.html' },
    ],
    // Layer 3
    [
      { id: 'certifications', label: 'Certifications', url: 'certifications.html' },
      { id: 'skills',         label: 'Skills',         url: 'skills.html' },
      { id: 'mytech',         label: 'My Tech',        url: 'mytech.html' },
      { id: 'contact',        label: 'Contact',        url: 'contact.html' },
    ],
    // Layer 4 — output nodes
    [
      { id: null, label: 'Engineer',   isDeco: true },
      { id: null, label: 'Researcher', isDeco: true },
      { id: null, label: 'Tinkerer',   isDeco: true },
    ],
  ];

  let allNodes = [];
  let connections = [];
  let particles = [];
  let hoveredNode = null;

  const NODE_RADIUS = 5;
  const HIT_RADIUS = 24;

  /* ---------- layout ---------- */

  function resize() {
    dpr = window.devicePixelRatio || 1;
    const container = canvas.parentElement;
    const w = container.clientWidth;
    const h = container.clientHeight;

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    layout(w, h);
  }

  function layout(w, h) {
    allNodes = [];
    connections = [];

    const px = w < 500 ? 40 : 90;
    const py = 28;
    const usableW = w - px * 2;
    const usableH = h - py * 2;
    const layerCount = sections.length;

    sections.forEach((layer, li) => {
      const x = px + (usableW * li) / (layerCount - 1);
      const n = layer.length;

      layer.forEach((sec, ni) => {
        const y = py + usableH * (ni + 0.5) / n;
        allNodes.push({
          ...sec,
          x, y,
          layer: li,
          isDeco: !!sec.isDeco,
        });
      });
    });

    // fully-connected edges between adjacent layers
    for (let li = 0; li < sections.length - 1; li++) {
      const from = allNodes.filter(n => n.layer === li);
      const to   = allNodes.filter(n => n.layer === li + 1);
      from.forEach(a => to.forEach(b => connections.push({ from: a, to: b })));
    }

    seedParticles();
  }

  /* ---------- color helpers ---------- */

  function lerpColor(t) {
    // cyan → blue → purple across layers
    const r = Math.round(80 + t * 160);
    const g = Math.round(220 - t * 120);
    const b = Math.round(255 - t * 30);
    return { r, g, b };
  }

  function connColor(conn, alpha) {
    const t = (conn.from.layer + conn.to.layer) / (2 * (sections.length - 1));
    const c = lerpColor(t);
    return 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + alpha + ')';
  }

  /* ---------- particles ---------- */

  function seedParticles() {
    particles = [];
    // exactly one particle per connection, staggered so they don't move in sync
    connections.forEach((c, i) => {
      particles.push({
        conn: c,
        t: i / connections.length,  // evenly stagger start positions
        speed: 0.0025 + Math.random() * 0.0015,
        size: 1.4 + Math.random() * 1.2,
      });
    });
  }

  /* ---------- draw ---------- */

  function draw() {
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;
    ctx.clearRect(0, 0, w, h);
    time += 0.016;

    // connections — gradient lines
    connections.forEach(c => {
      const lit = hoveredNode && (hoveredNode === c.from || hoveredNode === c.to);
      const grad = ctx.createLinearGradient(c.from.x, c.from.y, c.to.x, c.to.y);
      grad.addColorStop(0, connColor(c, lit ? 0.3 : 0.07));
      grad.addColorStop(1, connColor({ from: c.to, to: c.to }, lit ? 0.3 : 0.07));
      ctx.beginPath();
      ctx.moveTo(c.from.x, c.from.y);
      ctx.lineTo(c.to.x, c.to.y);
      ctx.strokeStyle = grad;
      ctx.lineWidth   = lit ? 1.4 : 0.7;
      ctx.stroke();
    });

    // particles — glowing dots
    particles.forEach(p => {
      const { from, to } = p.conn;
      const x = from.x + (to.x - from.x) * p.t;
      const y = from.y + (to.y - from.y) * p.t;
      const layerT = (from.layer + (to.layer - from.layer) * p.t) / (sections.length - 1);
      const c = lerpColor(layerT);
      const pulse = 0.6 + 0.4 * Math.sin(time * 4 + p.t * 6);

      // glow
      const glow = ctx.createRadialGradient(x, y, 0, x, y, p.size * 4);
      glow.addColorStop(0, 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + (0.3 * pulse) + ')');
      glow.addColorStop(1, 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',0)');
      ctx.beginPath();
      ctx.arc(x, y, p.size * 4, 0, Math.PI * 2);
      ctx.fillStyle = glow;
      ctx.fill();

      // core
      ctx.beginPath();
      ctx.arc(x, y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + (0.7 + 0.3 * pulse) + ')';
      ctx.fill();
    });

    // nodes
    allNodes.forEach(node => {
      const hov = hoveredNode === node;
      const isEndpoint = node.isDeco && node.label;
      const r = NODE_RADIUS;
      const layerT = node.layer / (sections.length - 1);
      const c = lerpColor(layerT);
      const pulse = 0.7 + 0.3 * Math.sin(time * 2.5 + node.layer * 1.2);

      // outer glow — always on for endpoints, on hover for clickable
      if (isEndpoint || hov) {
        const glowR = isEndpoint ? 18 + 4 * Math.sin(time * 2 + node.layer) : 20;
        const g = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, glowR);
        g.addColorStop(0, 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + (isEndpoint ? 0.2 * pulse : 0.18) + ')');
        g.addColorStop(1, 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',0)');
        ctx.beginPath();
        ctx.arc(node.x, node.y, glowR, 0, Math.PI * 2);
        ctx.fillStyle = g;
        ctx.fill();
      }

      // ring
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 1.5, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + (hov || isEndpoint ? 0.5 : 0.15) + ')';
      ctx.lineWidth = 1;
      ctx.stroke();

      // circle fill
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      const fillAlpha = isEndpoint ? 0.6 * pulse : hov ? 0.9 : 0.35;
      ctx.fillStyle = isEndpoint || hov
        ? 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + fillAlpha + ')'
        : 'rgba(255,255,255,' + fillAlpha + ')';
      ctx.fill();

      // label
      if (node.label) {
        if (isEndpoint) {
          ctx.font      = '600 11.5px "Segoe UI",sans-serif';
          ctx.fillStyle = 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + (0.55 + 0.25 * pulse) + ')';
        } else {
          ctx.font      = hov ? '600 12px "Segoe UI",sans-serif'
                               : '400 11px "Segoe UI",sans-serif';
          ctx.fillStyle = hov ? '#fff' : 'rgba(255,255,255,0.5)';
        }
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(node.label, node.x, node.y + r + 8);
      }
    });
  }

  /* ---------- animation loop ---------- */

  function tick() {
    particles.forEach(p => {
      p.t += p.speed;
      if (p.t >= 1) {
        p.t = 0; // restart on the same edge
      }
    });

    draw();
    requestAnimationFrame(tick);
  }

  /* ---------- interaction ---------- */

  function nodeAt(mx, my) {
    return allNodes.find(n => {
      if (n.isDeco) return false;
      const dx = n.x - mx, dy = n.y - my;
      return Math.sqrt(dx * dx + dy * dy) < HIT_RADIUS;
    });
  }

  canvas.addEventListener('mousemove', e => {
    const r = canvas.getBoundingClientRect();
    const node = nodeAt(e.clientX - r.left, e.clientY - r.top);
    if (node !== hoveredNode) {
      hoveredNode = node;
      canvas.style.cursor = node ? 'pointer' : 'default';
    }
  });

  canvas.addEventListener('click', e => {
    const r = canvas.getBoundingClientRect();
    const node = nodeAt(e.clientX - r.left, e.clientY - r.top);
    if (node && node.url) {
      window.location.href = node.url;
    }
  });

  canvas.addEventListener('mouseleave', () => {
    hoveredNode = null;
    canvas.style.cursor = 'default';
  });

  // touch support
  canvas.addEventListener('touchstart', e => {
    const touch = e.touches[0];
    const r = canvas.getBoundingClientRect();
    const node = nodeAt(touch.clientX - r.left, touch.clientY - r.top);
    if (node && node.url) {
      e.preventDefault();
      window.location.href = node.url;
    }
  }, { passive: false });

  /* ---------- init ---------- */

  window.addEventListener('resize', resize);
  resize();
  tick();
})();
