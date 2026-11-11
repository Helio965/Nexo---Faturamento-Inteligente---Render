/* COM-001: navegação e estrutura de avaliações independem do CDN de gráficos. */
(function () {
  'use strict';
  document.documentElement.classList.add('landing-enhanced');
  var toggle = document.getElementById('landing-menu-toggle');
  var navigation = document.getElementById('landing-navigation');
  if (toggle && navigation) {
    var mobile = window.matchMedia('(max-width: 992px)');
    function setMenu(open) {
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      navigation.hidden = mobile.matches && !open;
    }
    function syncMenu() {
      toggle.hidden = !mobile.matches;
      setMenu(false);
    }
    toggle.addEventListener('click', function () {
      setMenu(toggle.getAttribute('aria-expanded') !== 'true');
    });
    navigation.addEventListener('click', function (event) {
      if (event.target.closest('a')) setMenu(false);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        setMenu(false);
        toggle.focus();
      }
    });
    document.addEventListener('click', function (event) {
      var header = toggle.closest('.nexo-header');
      if (header && !header.contains(event.target)) setMenu(false);
    });
    if (mobile.addEventListener) mobile.addEventListener('change', syncMenu);
    else if (mobile.addListener) mobile.addListener(syncMenu);
    syncMenu();
  }

  function initReviews(root) {
    if (!root) return;
    if (root.nexoReviews) return root.nexoReviews.refresh();
    var previous = root.querySelector('[data-review-prev]');
    var next = root.querySelector('[data-review-next]');
    var indicators = root.querySelector('[data-review-indicators]');
    var status = root.querySelector('[data-review-status]');
    var empty = root.querySelector('[data-review-empty]');
    var controls = root.querySelector('.review-controls');
    var slides = [], index = 0;
    function show(selected) {
      if (!slides.length) return;
      index = (selected + slides.length) % slides.length;
      slides.forEach(function (slide, position) {
        slide.hidden = position !== index;
        slide.setAttribute('role', 'group');
        slide.setAttribute('aria-roledescription', 'depoimento');
        slide.setAttribute('aria-label', (position + 1) + ' de ' + slides.length);
      });
      if (indicators) Array.prototype.forEach.call(indicators.children, function (dot, position) {
        dot.setAttribute('aria-current', position === index ? 'true' : 'false');
      });
      if (status) status.textContent = 'Depoimento ' + (index + 1) + ' de ' + slides.length;
    }
    function refresh() {
      slides = Array.prototype.slice.call(root.querySelectorAll('[data-review-slide]'));
      index = Math.min(index, Math.max(0, slides.length - 1));
      if (empty) empty.hidden = slides.length > 0;
      [previous, next].forEach(function (button) {
        if (!button) return;
        button.hidden = slides.length < 2;
        button.disabled = slides.length < 2;
      });
      if (controls) controls.hidden = slides.length < 2;
      if (indicators) {
        indicators.replaceChildren();
        slides.forEach(function (_, position) {
          var dot = document.createElement('button');
          dot.type = 'button';
          dot.className = 'review-dot';
          dot.textContent = String(position + 1);
          dot.setAttribute('aria-label', 'Ir para depoimento ' + (position + 1));
          dot.addEventListener('click', function () { show(position); });
          indicators.appendChild(dot);
        });
        indicators.hidden = slides.length < 2;
      }
      if (slides.length) show(index);
      else if (status) status.textContent = '';
    }
    if (previous) previous.addEventListener('click', function () { show(index - 1); });
    if (next) next.addEventListener('click', function () { show(index + 1); });
    root.nexoReviews = { refresh: refresh };
    refresh();
    return root.nexoReviews;
  }
  window.NexoLanding = { initReviews: initReviews };
  document.querySelectorAll('[data-review-carousel]').forEach(initReviews);
})();

/* ============================================================
   NEXO — Landing Page · JS de mockups Plotly
   ============================================================
   Renderiza 3 gráficos demonstrativos:
     #hero-chart            comparação horizontal em Como funciona
     #demo-chart-evolucao   linha multissérie (5 meses de compras x vendas)
     #demo-chart-top        barra horizontal (top produtos do período)

   Tema espelha o design system NEXO (dark + paleta Hélio):
     - fundo transparente
     - tipografia Inter
     - paleta: roxo #a855f7, âmbar #f59e0b, info #38bdf8
     - tooltips dark com borda roxa

   Dados são FICTÍCIOS (loja de tintas demonstrativa "Tintas Almeida").
   ============================================================ */

(function () {
  'use strict';
  var rendered = false;
  function startCharts() {
  if (rendered || typeof window.Plotly === 'undefined') return;
  rendered = true;

  function drawChart(el, data, layout, config) {
    function fallback() {
      el.replaceChildren();
      el.removeAttribute('data-chart-ready');
      var note = document.querySelector('[data-chart-fallback-for="' + el.id + '"]');
      if (note) note.hidden = false;
    }
    try {
      Promise.resolve(window.Plotly.newPlot(el, data, layout, config)).then(function () {
        el.setAttribute('data-chart-ready', 'true');
        var note = document.querySelector('[data-chart-fallback-for="' + el.id + '"]');
        if (note) note.hidden = true;
      }, fallback);
    } catch (error) { fallback(); }
  }

  /* ---- Paleta NEXO (mesma do nexo.css) ---- */
  var NEXO = {
    purple:   '#a855f7',
    purpleD:  '#7c3aed',
    green:    '#22c55e',
    amber:    '#f59e0b',
    info:     '#38bdf8',
    text:     '#e8e9f0',
    textMut:  '#9aa0b7',
    textDim:  '#6a7088',
    grid:     'rgba(255,255,255,0.06)',
    surface:  '#181824'
  };

  /* ---- Layout base reaproveitado pelos 3 gráficos ---- */
  function baseLayout(extra) {
    return Object.assign({
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor:  'rgba(0,0,0,0)',
      font: { family: 'Inter, sans-serif', color: NEXO.textMut, size: 11.5 },
      margin: { l: 48, r: 16, t: 10, b: 36 },
      xaxis: { gridcolor: NEXO.grid, zerolinecolor: NEXO.grid, automargin: true, fixedrange: true },
      yaxis: { gridcolor: NEXO.grid, zerolinecolor: NEXO.grid, automargin: true, fixedrange: true },
      showlegend: false,
      hoverlabel: {
        bgcolor: NEXO.surface,
        bordercolor: NEXO.purple,
        font: { color: NEXO.text, family: 'Inter, sans-serif', size: 11.5 }
      }
    }, extra || {});
  }

  var baseConfig = {
    displayModeBar: false,
    responsive: true,
    scrollZoom: false,
    editable: false,
    staticPlot: false
  };

  /* ============================================================
     1) hero-chart — comparação horizontal em Como funciona.
        A faixa hachurada é apenas a diferença estimada do período,
        sem representar estoque físico, lucro ou prejuízo contábil.
     ============================================================ */
  (function () {
    var el = document.getElementById('hero-chart');
    if (!el) return;
    var labels = ['Compras', 'Vendas'];
    var values = [156300, 142800];

    drawChart(el, [{
      type: 'bar',
      orientation: 'h',
      x: values,
      y: labels,
      marker: { color: [NEXO.info, NEXO.purple] },
      width: 0.44,
      hovertemplate: '<b>%{y}</b><br>R$ %{x:,.0f}<extra></extra>'
    }, {
      type: 'bar',
      orientation: 'h',
      x: [13500],
      y: ['Vendas'],
      base: [142800],
      width: 0.44,
      marker: {
        color: 'rgba(245,158,11,0.08)',
        line: { color: NEXO.amber, width: 1 },
        pattern: { shape: '/', fgcolor: NEXO.amber, size: 5, solidity: 0.25 }
      },
      hovertemplate: 'Diferença estimada: R$ 13.500<extra></extra>'
    }], baseLayout({
      height: 200,
      barmode: 'overlay',
      margin: { l: 8, r: 8, t: 26, b: 30 },
      xaxis: {
        range: [0, 215000],
        tickvals: [0, 50000, 100000, 150000],
        ticktext: ['0', '50 mil', '100 mil', '150 mil'],
        tickfont: { size: 10, color: NEXO.textMut },
        gridcolor: NEXO.grid,
        zerolinecolor: NEXO.grid,
        fixedrange: true
      },
      yaxis: {
        categoryorder: 'array', categoryarray: labels, autorange: 'reversed',
        showticklabels: false, showgrid: false, zeroline: false,
        fixedrange: true
      },
      annotations: labels.map(function (label, index) {
        return {
          x: 0, y: label, xref: 'x', yref: 'y', xanchor: 'left',
          yshift: 24, showarrow: false,
          text: label + '  <b>R$ ' + values[index].toLocaleString('pt-BR') + '</b>',
          font: { size: 11, color: NEXO.textMut }
        };
      }).concat([{
        x: 160000, y: 'Vendas', xref: 'x', yref: 'y',
        xanchor: 'left', showarrow: false, text: 'R$ 13.500',
        font: { family: 'JetBrains Mono, monospace', size: 10, color: NEXO.amber }
      }])
    }), Object.assign({}, baseConfig, { staticPlot: true }));
  })();

  /* ============================================================
     2) demo-chart-evolucao — linha multissérie de 5 meses
        Compras (azul) vs Faturamento (roxo)
     ============================================================ */
  (function () {
    var el = document.getElementById('demo-chart-evolucao');
    if (!el) return;
    var meses    = ['Dez/25', 'Jan/26', 'Fev/26', 'Mar/26', 'Abr/26'];
    var compras  = [138400, 124900, 149600, 152300, 156300];
    var vendas   = [132100, 119800, 138200, 141600, 142800];

    drawChart(el, [
      {
        type: 'scatter', mode: 'lines+markers',
        name: 'Compras',
        x: meses, y: compras,
        line: { color: NEXO.info, width: 2.5 },
        marker: { color: NEXO.info, size: 7, line: { color: '#0c0c14', width: 2 } },
        hovertemplate: '<b>%{x}</b><br>Compras: R$ %{y:,.0f}<extra></extra>'
      },
      {
        type: 'scatter', mode: 'lines+markers',
        name: 'Vendas',
        x: meses, y: vendas,
        line: { color: NEXO.purple, width: 2.5 },
        marker: { color: NEXO.purple, size: 7, line: { color: '#0c0c14', width: 2 } },
        hovertemplate: '<b>%{x}</b><br>Vendas: R$ %{y:,.0f}<extra></extra>'
      }
    ], baseLayout({
      height: 220,
      showlegend: true,
      legend: {
        orientation: 'h', y: 1.16, x: 0.5, xanchor: 'center',
        font: { color: NEXO.textMut, size: 11 }
      },
      xaxis: { tickvals: meses, ticktext: ['Dez', 'Jan', 'Fev', 'Mar', 'Abr'], fixedrange: true, showgrid: false },
      yaxis: { gridcolor: NEXO.grid, tickvals: [120000, 130000, 140000, 150000], ticktext: ['120 mil', '130 mil', '140 mil', '150 mil'], fixedrange: true, automargin: true },
      margin: { l: 58, r: 16, t: 38, b: 30 }
    }), Object.assign({}, baseConfig, { staticPlot: false }));
  })();

  /* ============================================================
     3) demo-chart-top — barra horizontal: top produtos do período
        (em faturamento R$)
     ============================================================ */
  (function () {
    var el = document.getElementById('demo-chart-top');
    if (!el) return;
    var produtos = [
      'Massa Corrida Premium PVA 18L',
      'Tinta Acrílica Fosca 18L',
      'Esmalte Sintético Brilhante 3,6L',
      'Tinta Látex Branca 18L',
      'Selador Acrílico 18L'
    ];
    var valores = [28450, 24800, 19200, 16500, 12700];

    drawChart(el, [{
      type: 'bar',
      orientation: 'h',
      x: valores,
      y: [4, 3, 2, 1, 0],
      width: 0.5,
      customdata: produtos,
      marker: { color: NEXO.purple },
      text: valores.map(function (value) { return 'R$ ' + value.toLocaleString('pt-BR'); }),
      textposition: 'outside',
      textfont: { size: 11, color: NEXO.text },
      cliponaxis: false,
      hovertemplate: '<b>%{customdata}</b><br>R$ %{x:,.0f}<extra></extra>'
    }], baseLayout({
      height: 290,
      margin: { l: 0, r: 8, t: 26, b: 8 },
      xaxis: {
        range: [0, 38500], showticklabels: false, showgrid: false,
        zeroline: false, fixedrange: true
      },
      yaxis: {
        range: [-0.55, 4.55], showticklabels: false, showgrid: false,
        zeroline: false, fixedrange: true
      },
      annotations: produtos.map(function (produto, index) {
        return {
          x: 0, y: 4 - index, xref: 'x', yref: 'y', xanchor: 'left',
          yshift: 21, showarrow: false, text: produto,
          font: { size: 10.5, color: NEXO.textMut }
        };
      })
    }), Object.assign({}, baseConfig, { staticPlot: false }));
  })();
  }
  var loader = document.getElementById('nexo-plotly');
  if (typeof window.Plotly !== 'undefined') startCharts();
  else if (loader) loader.addEventListener('load', startCharts, { once: true });
})();
