/*
 * On-device comics carousel renderer (HTML5 Canvas port of
 * src/generate/comics_carousel.py).
 *
 * Runs inside a WebView (in the app) or in a headless browser (for
 * verification). Exposes window.renderComics(data) -> Promise<{ [name]: dataURL }>.
 *
 * Fonts are expected to already be registered by the host HTML via @font-face:
 *   'BebasNeue'  (display)   'Oswald'  (regular/small)   'OswaldBold' (bold)
 *
 * `data` shape (all cover images are pre-inlined as data: URIs by the RN side,
 * so the canvas is never tainted and toDataURL() works):
 *   {
 *     streetDate: "July 01, 2026",
 *     top:        [{ title, coverUrl, publisher }, ... up to 10],
 *     picks:      [{ title, coverUrl, publisher }, ...],
 *     collectors: [{ title, coverUrl, reason }, ... up to 4],
 *   }
 */
(function () {
  const W = 1080, H = 1350;

  const BG       = [3, 3, 10];
  const ORANGE   = [255, 140, 0];
  const WHITE    = [255, 255, 255];
  const GRAY_DIM = [75, 75, 90];
  const GOLD     = [255, 215, 0];

  const PUBLISHER_COLORS = {
    dc:           [0, 102, 255],
    marvel:       [204, 0, 0],
    image:        [255, 102, 0],
    'dark horse': [0, 170, 68],
    idw:          [255, 204, 0],
    default:      [120, 120, 120],
  };
  const PUBLISHER_MAP = {
    'dc comics':         'dc',
    'marvel':            'marvel',
    'image comics':      'image',
    'dark horse comics': 'dark horse',
    'idw publishing':    'idw',
  };
  const pubKey   = (p) => PUBLISHER_MAP[(p || '').toLowerCase().trim()] || 'default';
  const pubColor = (p) => PUBLISHER_COLORS[pubKey(p)] || PUBLISHER_COLORS.default;

  const REASON_DESCRIPTIONS = {
    '#1 ISSUE': 'Great jumping-on point',
    'FACSIMILE': 'Classic issue reprinted',
    'ANNIVERSARY': 'Milestone issue',
    'MILESTONE': 'Milestone issue',
    'FIRST APPEARANCE': 'Key character debut',
    '1:100 RATIO': 'Very rare - 1 per 100',
    '1:50 RATIO': 'Rare - 1 per 50 ordered',
    '1:25 RATIO': 'Limited - ask your LCS',
    '1:10 RATIO': 'Incentive variant',
    'FOIL VARIANT': 'Special cover treatment',
    'VIRGIN COVER': 'No logo - collector fave',
    'CONNECTING CVR': 'Part of a set',
    'SKETCH COVER': 'Art-focused variant',
    'VARIANT': 'Ask your LCS for details',
  };

  // ---- color helpers -----------------------------------------------------
  const rgb  = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${(a / 255).toFixed(4)})`;

  // ---- font helper (mirrors _font in the Python) -------------------------
  function font(name, size) {
    if (name === 'display') return `${size}px BebasNeue`;
    if (name === 'bold')    return `${size}px OswaldBold`;
    return `${size}px Oswald`; // regular / small
  }

  // ---- primitive drawing (PIL-style bounding-box semantics) --------------
  function rect(ctx, x1, y1, x2, y2, fill) {
    ctx.fillStyle = fill;
    ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
  }
  function rectOutline(ctx, x1, y1, x2, y2, color, width) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.strokeRect(x1 + width / 2, y1 + width / 2, x2 - x1 - width, y2 - y1 - width);
  }
  function line(ctx, x1, y1, x2, y2, color, width) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = 'butt';
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }
  // ellipse from a PIL bounding box [x1,y1,x2,y2]
  function ell(ctx, x1, y1, x2, y2, { fill, outline, width } = {}) {
    const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
    const rx = Math.abs(x2 - x1) / 2, ry = Math.abs(y2 - y1) / 2;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (outline) { ctx.strokeStyle = outline; ctx.lineWidth = width || 1; ctx.stroke(); }
  }
  // text with PIL-style anchors: 'mm' center/middle, 'rm' right/middle, else left/top
  function text(ctx, x, y, str, fontStr, fill, anchor) {
    ctx.font = fontStr;
    ctx.fillStyle = fill;
    if (anchor === 'mm')      { ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; }
    else if (anchor === 'rm') { ctx.textAlign = 'right';  ctx.textBaseline = 'middle'; }
    else                      { ctx.textAlign = 'left';   ctx.textBaseline = 'top'; }
    ctx.fillText(str, x, y);
  }
  function textWidth(ctx, str, fontStr) {
    ctx.font = fontStr;
    return ctx.measureText(str).width;
  }

  // ---- seeded PRNG (visual parity with random.Random) --------------------
  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---- background --------------------------------------------------------
  function stars(ctx) {
    const rnd = mulberry32(42);
    for (let i = 0; i < 320; i++) {
      const x = Math.floor(rnd() * W);
      const y = Math.floor(rnd() * H);
      const r = [1, 1, 1, 2][Math.floor(rnd() * 4)];
      const a = 80 + Math.floor(rnd() * 140);
      ell(ctx, x - r, y - r, x + r, y + r, {
        fill: rgba([200 + Math.floor(rnd() * 55), 210 + Math.floor(rnd() * 45), 255], a),
      });
    }
  }
  function nebula(ctx) {
    ell(ctx, 0, 0, 680, 560, { fill: rgba([10, 20, 80], 18) });
    ell(ctx, 600, 30, W, 540, { fill: rgba([20, 10, 60], 12) });
  }
  function base(ctx) {
    rect(ctx, 0, 0, W, H, rgb(BG));
    stars(ctx);
    nebula(ctx);
  }

  // ---- header / footer ---------------------------------------------------
  function header(ctx, title) {
    rect(ctx, 0, 0, W, 162, rgba([3, 3, 10], 242));
    text(ctx, W / 2, 32, 'THE WATCHTOWER', font('small', 34), rgba(ORANGE, 180), 'mm');
    text(ctx, W / 2, 112, title, font('display', 96), rgb(WHITE), 'mm');
    const ruleY = 158;
    rect(ctx, 50, ruleY, W - 50, ruleY + 3, rgba(ORANGE, 100));
    return ruleY + 3;
  }
  function footer(ctx, dateStr, showLegend) {
    const fy = H - 72;
    rect(ctx, 0, fy, W, H, rgba([3, 3, 10], 210));
    rect(ctx, 0, fy, W, fy + 3, rgba(ORANGE, 80));
    if (showLegend) {
      const items = [['DC', 'dc'], ['MARVEL', 'marvel'], ['IMAGE', 'image'],
                     ['DARK HORSE', 'dark horse'], ['IDW', 'idw']];
      let x = 28; const dot = 13; const lf = font('small', 24);
      for (const [label, key] of items) {
        const color = PUBLISHER_COLORS[key];
        const cy = fy + 28;
        ell(ctx, x, cy, x + dot, cy + dot, { fill: rgb(color) });
        text(ctx, x + dot + 6, cy - 1, label, lf, rgb(GRAY_DIM), 'lt');
        x += dot + 8 + textWidth(ctx, label, lf) + 16;
      }
    }
    text(ctx, W - 32, fy + 36, dateStr, font('display', 36), rgba(GRAY_DIM, 180), 'rm');
    text(ctx, W - 32, H - 14, '@the.watch_tower', font('small', 22), rgba(GRAY_DIM, 80), 'rm');
  }

  // ---- cover placement ---------------------------------------------------
  function placeCover(ctx, img, box, borderColor, num, label) {
    const [x1, y1, x2, y2] = box.map((v) => Math.round(v));
    const bw = 4;
    rectOutline(ctx, x1, y1, x2, y2, rgb(borderColor), bw);
    const iw = x2 - x1 - bw * 2, ih = y2 - y1 - bw * 2, ix = x1 + bw, iy = y1 + bw;

    if (img && img.width) {
      const ow = img.width, oh = img.height;
      const targetRatio = iw / ih, srcRatio = ow / oh;
      let sx = 0, sy = 0, sw = ow, sh = oh;
      if (srcRatio > targetRatio) { sw = Math.round(oh * targetRatio); sx = Math.round((ow - sw) / 2); }
      else { sh = Math.round(ow / targetRatio); }
      ctx.drawImage(img, sx, sy, sw, sh, ix, iy, iw, ih);
    } else {
      rect(ctx, ix, iy, ix + iw, iy + ih, rgb([12, 12, 22]));
      const fs = Math.max(20, Math.floor(iw / 10));
      const f = font('bold', fs);
      const lines = wrapWords(ctx, label || '', f, iw - 10);
      const lh = Math.max(24, Math.floor(iw / 10)) + 4;
      let sy2 = iy + Math.floor((ih - lines.length * lh) / 2) + lh / 2;
      for (const ln of lines) { text(ctx, ix + iw / 2, sy2, ln, f, rgb([70, 70, 90]), 'mm'); sy2 += lh; }
    }
    if (num) {
      const bs = 42;
      rect(ctx, x1 + bw + 3, y1 + bw + 3, x1 + bw + 3 + bs, y1 + bw + 3 + bs, rgb([0, 0, 0]));
      text(ctx, x1 + bw + 3 + bs / 2, y1 + bw + 3 + bs / 2, String(num), font('display', bs - 8), rgb(WHITE), 'mm');
    }
  }

  function wrapWords(ctx, str, fontStr, maxW) {
    const words = (str || '').split(/\s+/).filter(Boolean);
    const lines = []; let line = '';
    for (const w of words) {
      const test = (line + ' ' + w).trim();
      if (textWidth(ctx, test, fontStr) > maxW && line) { lines.push(line); line = w; }
      else line = test;
    }
    if (line) lines.push(line);
    return lines;
  }

  function titleCaption(ctx, box, str) {
    const [x1, y1, x2, y2] = box.map((v) => Math.round(v));
    const cw = x2 - x1;
    const fs = Math.max(15, Math.floor(cw / 13));
    const f = font('bold', fs);
    const words = (str || '').split(/\s+/).filter(Boolean);
    const lines = []; let line = '';
    for (const w of words) {
      const test = (line + ' ' + w).trim();
      if (textWidth(ctx, test, f) > cw - 16 && line) { lines.push(line); line = w; if (lines.length === 2) break; }
      else line = test;
    }
    if (line && lines.length < 2) lines.push(line);
    const placed = lines.reduce((n, l) => n + l.split(/\s+/).length, 0);
    if (placed < words.length && lines.length) {
      let last = lines[lines.length - 1];
      while (last && textWidth(ctx, last + '...', f) > cw - 16) last = last.slice(0, -1).trimEnd();
      lines[lines.length - 1] = last ? last + '...' : '...';
    }
    const lh = fs + 4;
    const barH = lh * lines.length + 12;
    const barTop = Math.max(y1, y2 - barH - 4);
    rect(ctx, x1 + 4, barTop, x2 - 4, y2 - 4, rgba([0, 0, 0], 200));
    const cx = (x1 + x2) / 2;
    lines.forEach((ln, i) => text(ctx, cx, barTop + 8 + i * lh + lh / 2, ln, f, rgba(WHITE, 245), 'mm'));
  }

  function overlayPill(ctx, box, reason, color) {
    const [x1, , , y2] = box.map((v) => Math.round(v));
    const x2 = Math.round(box[2]);
    const cxPill = (x1 + x2) / 2;
    const rf = font('bold', 26), df = font('regular', 22);
    const desc = REASON_DESCRIPTIONS[reason] || '';
    const tw = textWidth(ctx, reason, rf);
    const px1 = cxPill - tw / 2 - 14, px2 = cxPill + tw / 2 + 14;
    const pillH = 32;
    const stripH = pillH + (desc ? 30 : 0) + 20;
    const stripY = y2 - stripH - 6;
    const pillY = stripY + 8;
    rect(ctx, x1 + 4, stripY, x2 - 4, y2 - 4, rgba([0, 0, 0], 185));
    rect(ctx, px1, pillY, px2, pillY + pillH, rgba(color, 55));
    rectOutline(ctx, px1, pillY, px2, pillY + pillH, rgba(color, 220), 2);
    text(ctx, cxPill, pillY + pillH / 2, reason, rf, rgba(color, 240), 'mm');
    if (desc) text(ctx, cxPill, pillY + pillH + 14, desc, df, rgba([210, 210, 210], 200), 'mm');
  }

  // ---- the space station -------------------------------------------------
  function drawStation(ctx, topY, scale) {
    const cx = W / 2;
    const s = (v) => Math.round(v * scale);
    const C1 = [38, 40, 54], C2 = [28, 30, 42], C3 = [18, 20, 30];
    const PANEL = [14, 16, 24], EDGE = [65, 68, 88];

    const rings = [
      [topY + s(120), s(140), s(36)],
      [topY + s(228), s(158), s(42)],
      [topY + s(320), s(132), s(34)],
      [topY + s(398), s(110), s(28)],
    ];
    for (const [gy, gr, grv] of rings) {
      for (const [add, alpha] of [[100, 4], [65, 10], [35, 18], [10, 28]]) {
        ell(ctx, cx - gr - add, gy - grv - add / 3, cx + gr + add, gy + grv + add / 3, { fill: rgba([255, 120, 0], alpha) });
      }
    }
    const box = (x1, y1, x2, y2, fill, edge = true) => {
      rect(ctx, x1, y1, x2, y2, rgb(fill));
      if (edge) { line(ctx, x1, y1, x2, y1, rgb(EDGE), 1); line(ctx, x1, y1, x1, y2, rgb(EDGE), 1); }
    };
    const panels = (x1, y1, x2, h, n = 3, gap = 3) => {
      const pw = Math.floor((x2 - x1 - gap * (n - 1)) / n);
      for (let i = 0; i < n; i++) { const px = x1 + i * (pw + gap); rect(ctx, px, y1, px + pw, y1 + h, rgb(PANEL)); }
    };
    const ring = (gy, gr, grv, width, alphaFill = 25) => {
      ell(ctx, cx - gr - 4, gy - grv - 4, cx + gr + 4, gy + grv + 4, { fill: rgb(C3) });
      ell(ctx, cx - gr, gy - grv, cx + gr, gy + grv, { outline: rgb(ORANGE), width });
      ell(ctx, cx - gr + 9, gy - grv + 4, cx + gr - 9, gy + grv - 4, { outline: rgba([200, 100, 0], 140), width: 2 });
      ell(ctx, cx - gr, gy - grv, cx + gr, gy + grv, { fill: rgba([255, 120, 0], alphaFill) });
      for (let deg = 0; deg < 360; deg += 45) {
        const a = deg * Math.PI / 180;
        const bx = Math.round(cx + gr * Math.cos(a));
        const by = Math.round(gy + Math.round(grv * 0.6) * Math.sin(a));
        ell(ctx, bx - 3, by - 3, bx + 3, by + 3, { fill: rgb(EDGE) });
      }
    };

    line(ctx, cx, topY, cx, topY - s(52), rgba([180, 200, 255], 200), s(4));
    line(ctx, cx - s(20), topY - s(28), cx + s(20), topY - s(28), rgba([150, 165, 200], 180), s(3));
    ell(ctx, cx - s(8), topY - s(60), cx + s(8), topY - s(44), { fill: rgb([255, 150, 0]) });
    ell(ctx, cx - s(22), topY - s(74), cx + s(22), topY - s(30), { fill: rgba([255, 120, 0], 40) });

    ell(ctx, cx - s(62), topY - s(10), cx + s(62), topY + s(20), { fill: rgb(C1) });
    box(cx - s(62), topY, cx + s(62), topY + s(26), C1);
    for (let i = 0; i < 3; i++) { const lx = cx - s(40) + i * s(40); line(ctx, lx, topY - s(8), lx, topY + s(26), rgb(PANEL), 1); }

    box(cx - s(30), topY + s(26), cx + s(30), topY + s(86), C2);
    for (const wy of [topY + s(34), topY + s(52), topY + s(70)]) panels(cx - s(24), wy, cx + s(24), s(12), 2);

    ring(...rings[0], s(7), 30);
    box(cx - s(70), topY + s(128), cx + s(70), topY + s(160), C1);
    panels(cx - s(58), topY + s(138), cx + s(58), s(13), 4, 4);
    for (const rx of [cx - s(62), cx - s(44), cx + s(44), cx + s(62)]) ell(ctx, rx - 3, topY + s(131), rx + 3, topY + s(137), { fill: rgb(EDGE) });
    for (const sign of [-1, 1]) {
      const s1 = cx + sign * s(70), s2 = cx + sign * s(120);
      rect(ctx, Math.min(s1, s2), topY + s(138), Math.max(s1, s2), topY + s(150), rgb(C3));
      const p1 = cx + sign * s(120), p2 = cx + sign * s(158);
      rect(ctx, Math.min(p1, p2), topY + s(132), Math.max(p1, p2), topY + s(156), rgb(C2));
      panels(Math.min(p1, p2) + 3, topY + s(138), Math.max(p1, p2) - 3, s(10), 2);
    }

    ring(...rings[1], s(8), 32);
    box(cx - s(118), topY + s(238), cx + s(118), topY + s(306), C1);
    const rng = mulberry32(999);
    for (const wy of [topY + s(248), topY + s(263), topY + s(278), topY + s(293)]) {
      rect(ctx, cx - s(102), wy, cx + s(102), wy + s(9), rgb(C3));
      for (let i = 0; i < 5; i++) { const wx = cx - s(96) + i * s(42); const lit = rng() > 0.35; rect(ctx, wx, wy + 1, wx + s(34), wy + s(7), rgb(lit ? [48, 68, 108] : PANEL)); }
    }
    for (let rx = cx - s(108); rx < cx + s(112); rx += s(20)) {
      ell(ctx, rx - 2, topY + s(240), rx + 2, topY + s(244), { fill: rgb(EDGE) });
      ell(ctx, rx - 2, topY + s(302), rx + 2, topY + s(306), { fill: rgb(EDGE) });
    }
    for (const sign of [-1, 1]) {
      const mx1 = cx + sign * s(118), mx2 = cx + sign * s(238);
      const my1 = topY + s(242), my2 = topY + s(300);
      rect(ctx, Math.min(mx1, mx2), my1, Math.max(mx1, mx2), my2, rgb(C2));
      line(ctx, Math.min(mx1, mx2), my1, Math.max(mx1, mx2), my1, rgb(EDGE), 2);
      panels(Math.min(mx1, mx2) + 4, my1 + 8, Math.max(mx1, mx2) - 4, s(12), 2, 3);
      panels(Math.min(mx1, mx2) + 4, my1 + 26, Math.max(mx1, mx2) - 4, s(12), 2, 3);
      panels(Math.min(mx1, mx2) + 4, my1 + 44, Math.max(mx1, mx2) - 4, s(12), 2, 3);
      for (let ci = 0; ci < 3; ci++) { const cy2 = my1 + 8 + ci * s(17); rect(ctx, Math.min(mx1, mx2) + 4, cy2, Math.max(mx1, mx2) - 4, cy2 + s(13), rgb([16, 26, 60])); }
    }

    ring(...rings[2], s(6), 22);
    box(cx - s(42), topY + s(306), cx + s(42), topY + s(370), C2);
    for (const wy of [topY + s(316), topY + s(334), topY + s(352)]) panels(cx - s(34), wy, cx + s(34), s(11), 2);
    box(cx - s(84), topY + s(370), cx + s(84), topY + s(416), C1);
    for (const wy of [topY + s(378), topY + s(392), topY + s(406)]) rect(ctx, cx - s(70), wy, cx + s(70), wy + s(8), rgb(C3));

    ring(...rings[3], s(5), 15);
    box(cx - s(34), topY + s(416), cx + s(34), topY + s(458), C2);
    ell(ctx, cx - s(24), topY + s(448), cx + s(24), topY + s(466), { fill: rgb(C3) });
  }

  // ---- slides ------------------------------------------------------------
  function coverSlide(ctx, streetDate) {
    base(ctx);
    ell(ctx, 0, 0, 680, 560, { fill: rgba([10, 20, 80], 18) });
    ell(ctx, 600, 30, W, 540, { fill: rgba([20, 10, 60], 12) });

    const stationTop = 35;
    drawStation(ctx, stationTop, 0.88);
    const stationBottom = stationTop + Math.round(470 * 0.88);

    // fade behind the text area
    for (let y = stationBottom - 60; y < H; y++) {
      const t = Math.min(1, (y - (stationBottom - 60)) / 320);
      line(ctx, 0, y, W, y, rgba([3, 3, 10], Math.round(180 * Math.pow(t, 0.6))), 1);
    }

    const textAreaTop = stationBottom - 40;
    const textAreaH = H - textAreaTop - 40;
    const textMid = textAreaTop + textAreaH / 2;
    const lineH = 158;
    const totalH = lineH * 2 + 20 + 60 + 14 + 40;
    const blockTop = textMid - totalH / 2;

    text(ctx, W / 2, blockTop + lineH / 2, 'NEW COMIC', font('display', 158), rgb(WHITE), 'mm');
    text(ctx, W / 2, blockTop + lineH + 16 + lineH / 2, 'BOOK DAY', font('display', 158), rgb(WHITE), 'mm');
    const dateY = blockTop + lineH * 2 + 40;
    text(ctx, W / 2, dateY, streetDate.toUpperCase(), font('display', 72), rgba(ORANGE, 210), 'mm');
    text(ctx, W / 2, dateY + 54, 'THE WATCHTOWER', font('small', 34), rgba(GRAY_DIM, 200), 'mm');
    text(ctx, W - 36, H - 16, '@the.watch_tower', font('small', 22), rgba(GRAY_DIM, 80), 'rm');
  }

  function top10Slide(ctx, issues, dateStr) {
    base(ctx);
    const hb = header(ctx, 'TOP 10 NEW COMICS THIS WEEK');
    const pad = 10, gt = hb + 14, gb = H - 78;
    const topH = Math.round((gb - gt) * 0.5);
    const mid = Math.floor(W / 2 - pad / 2);
    const cells = [[pad, gt, mid, gt + topH], [mid + pad, gt, W - pad, gt + topH]];
    cells.forEach((box, i) => {
      if (i < issues.length) {
        const it = issues[i];
        placeCover(ctx, it._img, box, pubColor(it.publisher), i + 1, it.title);
        titleCaption(ctx, box, it.title);
      }
    });
    const bt = gt + topH + pad, botH = gb - bt, cols = 4, rows = 2;
    const cw = Math.floor((W - pad * (cols + 1)) / cols);
    const ch = Math.floor((botH - pad * (rows - 1)) / rows);
    for (let idx = 0; idx < 8; idx++) {
      const col = idx % cols, row = Math.floor(idx / cols);
      const x1 = pad + col * (cw + pad), y1 = bt + row * (ch + pad);
      const ii = idx + 2;
      if (ii < issues.length) {
        const it = issues[ii];
        placeCover(ctx, it._img, [x1, y1, x1 + cw, y1 + ch], pubColor(it.publisher), ii + 1, it.title);
        titleCaption(ctx, [x1, y1, x1 + cw, y1 + ch], it.title);
      }
    }
    footer(ctx, dateStr, true);
  }

  function picksSlide(ctx, picks, dateStr) {
    base(ctx);
    const hb = header(ctx, "WATCHTOWER'S PICKS OF THE WEEK");
    const pad = 10, gt = hb + 14, gb = H - 78, n = picks.length;
    if (n === 0) {
      text(ctx, W / 2, H / 2, 'NO PICKS THIS WEEK', font('bold', 72), rgba(GRAY_DIM, 180), 'mm');
    } else if (n === 1) {
      const cw = Math.round(W * 0.6), x1 = Math.floor((W - cw) / 2);
      placeCover(ctx, picks[0]._img, [x1, gt, x1 + cw, gb], pubColor(picks[0].publisher), 1, picks[0].title);
    } else {
      const cols = 2, rows = Math.ceil(n / 2);
      const cw = Math.floor((W - pad * (cols + 1)) / cols);
      const ch = Math.floor((gb - gt - pad * (rows - 1)) / rows);
      picks.forEach((it, idx) => {
        const col = idx % cols, row = Math.floor(idx / cols);
        let x1 = pad + col * (cw + pad); const y1 = gt + row * (ch + pad);
        if (n % 2 === 1 && idx === n - 1) x1 = Math.floor((W - cw) / 2);
        placeCover(ctx, it._img, [x1, y1, x1 + cw, y1 + ch], pubColor(it.publisher), idx + 1, it.title);
      });
    }
    footer(ctx, dateStr, false);
  }

  function collectorsSlide(ctx, items, dateStr) {
    base(ctx);
    const hb = header(ctx, "COLLECTOR'S CORNER");
    text(ctx, W / 2, hb + 22, 'KEY ISSUES & RARE VARIANTS THIS WEEK', font('small', 30), rgba(ORANGE, 140), 'mm');
    const pad = 14, gt = hb + 50, gb = H - 78;
    items = items.slice(0, 4);
    const n = items.length;
    if (n === 0) {
      text(ctx, W / 2, H / 2, 'NOTHING THIS WEEK', font('bold', 60), rgba(GRAY_DIM, 180), 'mm');
    } else {
      const cols = Math.min(n, 2), rows = Math.ceil(n / cols);
      const cw = Math.floor((W - pad * (cols + 1)) / cols);
      const ch = Math.floor((gb - gt - pad * (rows - 1)) / rows);
      items.forEach((item, idx) => {
        const col = idx % cols, row = Math.floor(idx / cols);
        let x1 = pad + col * (cw + pad); const y1 = gt + row * (ch + pad);
        if (n % 2 === 1 && idx === n - 1) x1 = Math.floor((W - cw) / 2);
        const reason = item.reason || '';
        let borderColor;
        if (['RATIO', 'FOIL', 'VIRGIN', 'VARIANT', 'SKETCH'].some((k) => reason.includes(k))) borderColor = GOLD;
        else if (['#1 ISSUE', 'FIRST APPEARANCE', 'FACSIMILE'].includes(reason)) borderColor = [0, 200, 100];
        else borderColor = ORANGE;
        const box = [x1, y1, x1 + cw, y1 + ch];
        placeCover(ctx, item._img, box, borderColor, 0, item.title);
        overlayPill(ctx, box, reason, borderColor);
      });
    }
    footer(ctx, dateStr, false);
  }

  // ---- image loading + orchestration ------------------------------------
  function loadImage(src) {
    return new Promise((resolve) => {
      if (!src) return resolve(null);
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    });
  }

  async function attachImages(list) {
    if (!list) return;
    await Promise.all(list.map(async (it) => { it._img = await loadImage(it.coverUrl); }));
  }

  function newCanvas() {
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    return c;
  }

  // Canvas does NOT trigger web-font loading on its own, so force-load the
  // three families before any drawing or the headings fall back to serif.
  async function ensureFonts() {
    if (!document.fonts || !document.fonts.load) return;
    try {
      await Promise.all([
        document.fonts.load('96px BebasNeue'),
        document.fonts.load('34px Oswald'),
        document.fonts.load('bold 34px OswaldBold'),
      ]);
      await document.fonts.ready;
    } catch (e) { /* fall back to system fonts */ }
  }

  async function renderComics(data) {
    await ensureFonts();
    await Promise.all([attachImages(data.top), attachImages(data.picks), attachImages(data.collectors)]);
    const out = {};

    let c = newCanvas(); coverSlide(c.getContext('2d'), data.streetDate); out['slide_01_cover'] = c.toDataURL('image/jpeg', 0.95);
    c = newCanvas(); top10Slide(c.getContext('2d'), data.top || [], data.streetDate.toUpperCase()); out['slide_02_top10'] = c.toDataURL('image/jpeg', 0.95);
    c = newCanvas(); picksSlide(c.getContext('2d'), data.picks || [], data.streetDate.toUpperCase()); out['slide_03_picks'] = c.toDataURL('image/jpeg', 0.95);
    if ((data.collectors || []).length) {
      c = newCanvas(); collectorsSlide(c.getContext('2d'), data.collectors, data.streetDate.toUpperCase()); out['slide_04_collectors'] = c.toDataURL('image/jpeg', 0.95);
    }
    return out;
  }

  window.renderComics = renderComics;
})();
