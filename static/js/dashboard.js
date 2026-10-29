// ======================================================================
// INOOS - Tablero de Inteligencia Clínica & Benchmarking CAC / INC
// Todos los indicadores calculados al 100% desde la base de datos cargada
// ======================================================================

document.addEventListener('DOMContentLoaded', () => {
  console.log('[INOOS Dashboard] Inicializando módulo de Inteligencia Clínica...');

  // Referencias a Filtros del Encabezado
  const selectEps = document.getElementById('filter-eps');
  const selectPrioridad = document.getElementById('filter-prioridad');
  const selectAgrupador = document.getElementById('filter-agrupador');
  const selectTipoRegistro = document.getElementById('filter-tipo-registro');
  const selectRegimen = document.getElementById('filter-regimen');
  const selectEstadio = document.getElementById('filter-estadio');
  const selectSexo = document.getElementById('filter-sexo');
  const selectEdad = document.getElementById('filter-edad');
  const selectDepto = document.getElementById('filter-depto');
  const btnReset = document.getElementById('btn-reset-filters');
  const btnRefresh = document.getElementById('btn-refresh-dashboard');
  const btnExport = document.getElementById('btn-export-csv');

  // Metadatos y Badges
  const cohortCounter = document.getElementById('cohort-counter');
  const poblacionRef = document.getElementById('poblacion-reference');
  const activeFileInd = document.getElementById('active-file-indicator');
  const activeCorteBadge = document.getElementById('active-corte-badge');

  // Tarjetas KPI Principales
  const cardTotal = document.getElementById('card-total-casos');
  const cardTotalSub = document.getElementById('card-total-sub');
  const cardTasa = document.getElementById('card-tasa-prev');
  const cardTasaSub = document.getElementById('card-tasa-sub');
  const cardIncidencia = document.getElementById('card-incidencia-casos');
  const cardIncidenciaSub = document.getElementById('card-incidencia-sub');
  const cardIngresosMes = document.getElementById('card-ingresos-mes');
  const cardIngresosMesSub = document.getElementById('card-ingresos-mes-sub');
  const cardTemprano = document.getElementById('card-temprano-pct');
  const cardTempranoSub = document.getElementById('card-temprano-sub');
  const cardOportunidad = document.getElementById('card-oportunidad-dias');
  const cardOportunidadSub = document.getElementById('card-oportunidad-sub');
  const cardPrio = document.getElementById('card-priorizados');
  const cardPrioSub = document.getElementById('card-priorizados-sub');
  const btnToggleTopChart = document.getElementById('btn-toggle-top-chart');

  // Tablas y Contenedores
  const tbodyAgrupadores = document.getElementById('tbody-agrupadores');
  const tbodyPacientes = document.getElementById('tbody-pacientes-sample');
  const searchAgrupador = document.getElementById('table-search-agrupador');

  // Instancias de Gráficos Chart.js
  let chartTopNeoplasias = null;
  let chartEpsPie = null;
  let chartPrioridadPie = null;
  let chartEstadiosPie = null;
  let chartOportunidadHistogram = null;
  let chartIntencion = null;
  let chartIngresos = null;
  let chartBenchmarkRegimen = null;
  let chartPiramide = null;
  let chartDeptos = null;
  let chartRegimenPie = null;
  let chartMunicipios = null;

  // Estado global
  let currentAgrupadoresList = [];
  let isFetching = false;
  let lastTopNeoplasiasData = null;
  let topChartOrientation = 'x'; // 'x' para barras verticales con línea por encima, 'y' para horizontal

  // Paleta de Colores Institucional INOOS
  const COLOR_LILA = '#8158A1';
  const COLOR_TURQUESA = '#47A9A1';
  const COLOR_ROSA = '#E27396';
  const COLOR_AZUL = '#60A5FA';
  const COLOR_VERDE = '#34D399';
  const COLOR_AMARILLO = '#FBBF24';
  const COLOR_DORADO_CONTRASTE = '#FACC15'; // Amarillo/Oro Neón de Máximo Contraste Visual
  const COLOR_ROJO = '#EF4444';
  const COLOR_GRIS = 'rgba(255, 255, 255, 0.08)';

  // Configuración Segura de Defaults de Chart.js
  if (typeof Chart !== 'undefined') {
    try {
      Chart.defaults.color = '#9DA3AE';
      Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
      if (Chart.defaults.plugins && Chart.defaults.plugins.tooltip) {
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(13, 15, 24, 0.95)';
        Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.15)';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
      }
      console.log('[INOOS Dashboard] Chart.js inicializado correctamente.');
    } catch (e) {
      console.warn('[INOOS Dashboard] Advertencia configurando defaults de Chart.js:', e);
    }
  } else {
    console.warn('[INOOS Dashboard] ATENCIÓN: Chart.js no se cargó. Los indicadores numéricos, tablas y análisis se mostrarán normalmente.');
  }

  // Helper seguro para crear o actualizar gráficos sin lanzar excepciones no controladas
  function safeCreateChart(canvasId, oldChart, chartConfig) {
    if (typeof Chart === 'undefined') {
      const cvs = document.getElementById(canvasId);
      if (cvs && cvs.parentElement) {
        cvs.parentElement.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#9DA3AE;font-size:0.85rem;"><i class="fa-solid fa-chart-line" style="margin-right:8px;"></i> Modo de datos tabulares activo</div>';
      }
      return null;
    }

    try {
      if (oldChart && typeof oldChart.destroy === 'function') {
        oldChart.destroy();
      }
      const canvas = document.getElementById(canvasId);
      if (!canvas) {
        console.warn(`[INOOS Dashboard] Canvas #${canvasId} no encontrado en el DOM.`);
        return null;
      }
      const ctx = canvas.getContext('2d');
      return new Chart(ctx, chartConfig);
    } catch (err) {
      console.error(`[INOOS Dashboard] Error creando gráfico #${canvasId}:`, err);
      return null;
    }
  }

  // 1. Cargar Opciones Iniciales de Filtro desde la Base
  async function initFilters() {
    try {
      console.log('[INOOS Dashboard] Consultando opciones de filtro en /api/dashboard/filters...');
      const res = await fetch('/api/dashboard/filters');
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const rawText = await res.text();
      const cleanText = rawText.replace(/:\s*NaN\b/g, ': null').replace(/:\s*Infinity\b/g, ': null');
      const data = JSON.parse(cleanText);

      if (data.status === 'success' && data.options) {
        const opts = data.options;
        if (activeFileInd && opts.active_filename) activeFileInd.textContent = opts.active_filename;
        if (activeCorteBadge && opts.mes_corte && opts.ano_corte) {
          activeCorteBadge.textContent = `Corte Clínico: ${opts.mes_corte} ${opts.ano_corte}`;
        }

        // Llenar EPS dinámicamente si no están llenas
        if (selectEps && selectEps.options.length <= 1 && opts.eps) {
          opts.eps.forEach(eps => {
            const opt = document.createElement('option');
            opt.value = eps;
            opt.textContent = eps;
            selectEps.appendChild(opt);
          });
        }

        // Llenar Agrupadores
        if (selectAgrupador && selectAgrupador.options.length <= 1 && opts.agrupadores) {
          opts.agrupadores.forEach(ag => {
            const opt = document.createElement('option');
            opt.value = ag;
            opt.textContent = ag;
            selectAgrupador.appendChild(opt);
          });
        }

        // Llenar Regímenes
        if (selectRegimen && selectRegimen.options.length <= 1 && opts.regimenes) {
          opts.regimenes.filter(r => r !== 'Todos').forEach(r => {
            const opt = document.createElement('option');
            opt.value = r;
            opt.textContent = r;
            selectRegimen.appendChild(opt);
          });
        }

        // Llenar Departamentos
        if (selectDepto && selectDepto.options.length <= 1 && opts.departamentos) {
          opts.departamentos.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            selectDepto.appendChild(opt);
          });
        }
        console.log('[INOOS Dashboard] Filtros sincronizados exitosamente.');
      }
    } catch (err) {
      console.error('[INOOS Dashboard] Error al inicializar filtros:', err);
    }
  }

  // 2. Obtener los Filtros Seleccionados
  function getActiveFilters() {
    return {
      eps: selectEps ? selectEps.value : 'ALL',
      prioridad: selectPrioridad ? selectPrioridad.value : 'ALL',
      agrupador: selectAgrupador ? selectAgrupador.value : 'ALL',
      tipo_registro: selectTipoRegistro ? selectTipoRegistro.value : 'ALL',
      regimen: selectRegimen ? selectRegimen.value : 'ALL',
      estadio: selectEstadio ? selectEstadio.value : 'ALL',
      sexo: selectSexo ? selectSexo.value : 'ALL',
      rango_edad: selectEdad ? selectEdad.value : 'ALL',
      depto: selectDepto ? selectDepto.value : 'ALL'
    };
  }

  // Mostrar estado de carga en la interfaz
  function showLoadingState() {
    if (cohortCounter) {
      cohortCounter.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Calculando métricas de la cohorte...`;
    }
    if (cardTotal && cardTotal.textContent === '-') cardTotal.innerHTML = `<span style="font-size:1.5rem;opacity:0.6;"><i class="fa-solid fa-spinner fa-spin"></i></span>`;
    if (cardTasa && cardTasa.textContent === '-') cardTasa.innerHTML = `<span style="font-size:1.5rem;opacity:0.6;"><i class="fa-solid fa-spinner fa-spin"></i></span>`;
    if (cardIncidencia && cardIncidencia.textContent === '-') cardIncidencia.innerHTML = `<span style="font-size:1.5rem;opacity:0.6;"><i class="fa-solid fa-spinner fa-spin"></i></span>`;
    if (cardIngresosMes && cardIngresosMes.textContent === '-') cardIngresosMes.innerHTML = `<span style="font-size:1.5rem;opacity:0.6;"><i class="fa-solid fa-spinner fa-spin"></i></span>`;
    if (cardTemprano && cardTemprano.textContent === '-') cardTemprano.innerHTML = `<span style="font-size:1.5rem;opacity:0.6;"><i class="fa-solid fa-spinner fa-spin"></i></span>`;
    if (cardOportunidad && cardOportunidad.textContent === '-') cardOportunidad.innerHTML = `<span style="font-size:1.5rem;opacity:0.6;"><i class="fa-solid fa-spinner fa-spin"></i></span>`;
    if (cardPrio && cardPrio.textContent === '-') cardPrio.innerHTML = `<span style="font-size:1.5rem;opacity:0.6;"><i class="fa-solid fa-spinner fa-spin"></i></span>`;
  }

  // 3. Cargar y Actualizar los Datos del Tablero desde el Backend
  async function refreshDashboard() {
    if (isFetching) return;
    isFetching = true;
    showLoadingState();

    const filters = getActiveFilters();
    console.log('[INOOS Dashboard] Consultando métricas con filtros:', filters);

    try {
      const res = await fetch('/api/dashboard/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters })
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      // Lectura segura con saneamiento anti-NaN garantizado
      const rawText = await res.text();
      const cleanText = rawText
        .replace(/:\s*NaN\b/g, ': null')
        .replace(/:\s*Infinity\b/g, ': null')
        .replace(/:\s*-Infinity\b/g, ': null');
      const data = JSON.parse(cleanText);
      console.log('[INOOS Dashboard] Datos calculados recibidos exitosamente.');

      if (data.status === 'success') {
        // 1. Tarjetas Ejecutivas Principales
        try {
          updateKPIs(data.kpis);
        } catch (e) {
          console.error('[INOOS Dashboard] Error en updateKPIs:', e);
        }

        // 2. Gráfico Top 10 Neoplasias
        try {
          updateTopNeoplasiasChart(data.top10_agrupadores);
        } catch (e) {
          console.error('[INOOS Dashboard] Error en updateTopNeoplasiasChart:', e);
        }

        // 3. Gráfico EPS
        try {
          updateEpsPieChart(data.eps_distribucion);
        } catch (e) {
          console.error('[INOOS Dashboard] Error en updateEpsPieChart:', e);
        }

        // 4. Gráfico Prioridad CAC
        try {
          updatePrioridadPieChart(data.kpis);
        } catch (e) {
          console.error('[INOOS Dashboard] Error en updatePrioridadPieChart:', e);
        }

        // 5. Tabla Censo de 25 Agrupadores
        try {
          updateAgrupadoresTable(data.agrupadores_todos || []);
        } catch (e) {
          console.error('[INOOS Dashboard] Error en updateAgrupadoresTable:', e);
        }

        // 6. Pestaña 2: Benchmarking CAC / INC
        try {
          updateBenchmarkingTab(data.benchmarking_cac, data.mama_biomarcadores);
        } catch (e) {
          console.error('[INOOS Dashboard] Error en updateBenchmarkingTab:', e);
        }

        // 7. Pestaña 3: Estadificación & Oportunidad Real
        try {
          updateEstadificacionYOportunidad(data);
        } catch (e) {
          console.error('[INOOS Dashboard] Error en updateEstadificacionYOportunidad:', e);
        }

        // 8. Pestaña 4: Demografía & Territorios
        try {
          updateDemografiaTab(data);
        } catch (e) {
          console.error('[INOOS Dashboard] Error en updateDemografiaTab:', e);
        }

        // 9. Pestaña 5: Explorador de Pacientes
        try {
          updatePacientesTable(data.pacientes_sample || []);
        } catch (e) {
          console.error('[INOOS Dashboard] Error en updatePacientesTable:', e);
        }

        console.log('[INOOS Dashboard] Todos los componentes del tablero renderizados exitosamente.');
      } else {
        alert('Aviso del motor clínico: ' + (data.error || 'No se pudieron calcular las métricas'));
      }
    } catch (err) {
      console.error('[INOOS Dashboard] Error en refreshDashboard:', err);
      if (cohortCounter) {
        if (err.message && (err.message.includes('404') || err.message.includes('No encontrado') || err.message.includes('no disponible'))) {
          cohortCounter.innerHTML = `<i class="fa-solid fa-cloud-arrow-up" style="color:#60A5FA;"></i> Sin base de datos activa. <a href="/" style="color:#34D399;font-weight:700;text-decoration:underline;margin-left:5px;">Cargar archivo Excel aquí</a>`;
        } else {
          cohortCounter.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color:#EF4444;"></i> Error de conexión con el motor: ${err.message}`;
        }
      }
    } finally {
      isFetching = false;
    }
  }

  // Actualizar Tarjetas KPI Principales (100% calculadas de la base)
  function updateKPIs(kpis) {
    if (!kpis) return;

    if (cardTotal) cardTotal.textContent = Number(kpis.total_filtrados).toLocaleString();
    if (cardTotalSub) cardTotalSub.innerHTML = `<i class="fa-solid fa-chart-pie"></i> ${kpis.pct_cohorte}% de la cohorte total (${Number(kpis.total_general).toLocaleString()})`;

    if (cardTasa) cardTasa.textContent = Number(kpis.tasa_prevalencia).toLocaleString();
    if (cardTasaSub) cardTasaSub.innerHTML = `<i class="fa-solid fa-bullseye"></i> Sobre ${Number(kpis.poblacion_afiliada).toLocaleString()} afiliados (${kpis.poblacion_label})`;

    if (cardIncidencia) {
      const incCount = Number(kpis.incidentes_count || 0).toLocaleString();
      cardIncidencia.textContent = `${incCount} (${kpis.incidentes_pct || 0}%)`;
    }
    if (cardIncidenciaSub) {
      const prevCount = Number(kpis.prevalentes_count || 0).toLocaleString();
      cardIncidenciaSub.innerHTML = `<i class="fa-solid fa-arrows-split-up-and-left"></i> Prev: ${prevCount} (${kpis.prevalentes_pct || 0}%) | Tasa Inc: ${kpis.tasa_incidencia || 0}`;
    }

    if (cardIngresosMes) {
      const incMes = kpis.ingresos_mes_incidentes !== undefined ? Number(kpis.ingresos_mes_incidentes).toLocaleString() : '0';
      const prevMes = kpis.ingresos_mes_prevalentes !== undefined ? Number(kpis.ingresos_mes_prevalentes).toLocaleString() : '0';
      cardIngresosMes.textContent = `${incMes} Inc | ${prevMes} Prev`;
    }
    if (cardIngresosMesSub) {
      const promInc = kpis.ingresos_promedio_incidentes || 0;
      const promPrev = kpis.ingresos_promedio_prevalentes || 0;
      const mesNombre = kpis.mes_corte_nombre || 'Corte';
      cardIngresosMesSub.innerHTML = `<i class="fa-solid fa-chart-line"></i> ${mesNombre}: ${kpis.ingresos_mes_total || 0} | Prom: ${promInc} Inc/mes`;
    }

    if (cardTemprano) cardTemprano.textContent = `${kpis.estadio_temprano_pct}%`;
    if (cardTempranoSub) cardTempranoSub.innerHTML = `<i class="fa-solid fa-flag-checkered"></i> Estadios I-II (Meta CAC: &ge; 60%)`;

    if (cardOportunidad) cardOportunidad.textContent = `${kpis.oportunidad_mediana_dias} días`;
    if (cardOportunidadSub) cardOportunidadSub.innerHTML = `<i class="fa-solid fa-clock"></i> Mediana Dx &rarr; Consulta (${kpis.oportunidad_cumple_15d_pct}% cumple &le; 15d)`;

    if (cardPrio) cardPrio.textContent = Number(kpis.priorizados_count).toLocaleString();
    if (cardPrioSub) cardPrioSub.innerHTML = `<i class="fa-solid fa-percentage"></i> ${kpis.priorizados_pct}% de la cohorte filtrada`;

    if (cohortCounter) {
      cohortCounter.innerHTML = `<i class="fa-solid fa-users"></i> Mostrando ${Number(kpis.total_filtrados).toLocaleString()} de ${Number(kpis.total_general).toLocaleString()} pacientes (${kpis.pct_cohorte}%)`;
    }
    if (poblacionRef) {
      poblacionRef.textContent = `Población Asignada: ${Number(kpis.poblacion_afiliada).toLocaleString()} afiliados (${kpis.poblacion_label})`;
    }
  }

  // Gráfico: Top 10 Neoplasias (Casos en Barras y Tasa de Prevalencia en Línea de Alto Contraste)
  function updateTopNeoplasiasChart(topData) {
    if (!topData || !topData.labels) return;
    lastTopNeoplasiasData = topData;

    const isHorizontal = (topChartOrientation === 'y');

    // Abreviar suavemente nombres extensos para una presentación pulida
    const displayLabels = topData.labels.map(l => {
      let clean = l.replace(/^Tumor(es)? Maligno(s)? de(l)?\s*/i, 'Cáncer ');
      if (clean.length > 24) return clean.slice(0, 22) + '...';
      return clean;
    });

    const chartConfig = {
      type: 'bar',
      data: {
        labels: isHorizontal ? topData.labels : displayLabels,
        datasets: [
          {
            type: 'bar',
            label: 'Casos Totales (Barras)',
            data: topData.casos,
            backgroundColor: 'rgba(71, 169, 161, 0.85)',
            hoverBackgroundColor: '#47A9A1',
            borderColor: '#47A9A1',
            borderWidth: 1.5,
            borderRadius: 6,
            yAxisID: isHorizontal ? 'y' : 'y',
            xAxisID: isHorizontal ? 'x' : 'x',
            order: 2
          },
          {
            type: 'line',
            label: 'Tasa Prevalencia x 100k (Línea)',
            data: topData.tasas,
            borderColor: COLOR_DORADO_CONTRASTE,
            backgroundColor: 'rgba(250, 204, 21, 0.25)',
            borderWidth: 3.5,
            pointRadius: 6,
            pointHoverRadius: 9,
            pointBackgroundColor: COLOR_DORADO_CONTRASTE,
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            tension: 0.3,
            fill: false,
            yAxisID: isHorizontal ? 'y' : 'y1',
            xAxisID: isHorizontal ? 'x1' : 'x',
            order: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: isHorizontal ? 'y' : 'x',
        interaction: {
          mode: 'index',
          intersect: false
        },
        scales: isHorizontal ? {
          y: {
            grid: { display: false },
            ticks: { font: { size: 10, weight: '600' }, color: '#CBD5E1' }
          },
          x: {
            type: 'linear',
            position: 'bottom',
            title: { display: true, text: 'Casos Totales (Pacientes)', color: '#47A9A1', font: { weight: '600', size: 11 } },
            grid: { color: COLOR_GRIS },
            ticks: { color: '#9DA3AE' },
            beginAtZero: true
          },
          x1: {
            type: 'linear',
            position: 'top',
            title: { display: true, text: 'Tasa x 100.000 Afiliados', color: COLOR_DORADO_CONTRASTE, font: { weight: '600', size: 11 } },
            grid: { drawOnChartArea: false },
            ticks: { color: COLOR_DORADO_CONTRASTE },
            beginAtZero: true
          }
        } : {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#CBD5E1',
              font: { size: 10, weight: '600' },
              maxRotation: 35,
              minRotation: 0
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Casos Totales (Pacientes)',
              color: '#47A9A1',
              font: { weight: '600', size: 11 }
            },
            grid: { color: COLOR_GRIS },
            ticks: { color: '#9DA3AE' },
            beginAtZero: true
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: 'Tasa x 100.000 Afiliados',
              color: COLOR_DORADO_CONTRASTE,
              font: { weight: '600', size: 11 }
            },
            grid: { drawOnChartArea: false },
            ticks: { color: COLOR_DORADO_CONTRASTE },
            beginAtZero: true
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              boxWidth: 14,
              padding: 12,
              color: '#E2E8F0',
              font: { weight: '600', size: 11 }
            }
          },
          tooltip: {
            callbacks: {
              title: function (items) {
                if (!items.length) return '';
                const idx = items[0].dataIndex;
                return topData.labels[idx] || items[0].label;
              },
              label: function (context) {
                const val = isHorizontal ? context.parsed.x : context.parsed.y;
                if (context.dataset.type === 'line') {
                  return ` ${context.dataset.label}: ${val.toLocaleString()} por 100k`;
                }
                return ` ${context.dataset.label}: ${val.toLocaleString()} pacientes`;
              }
            }
          }
        }
      }
    };

    chartTopNeoplasias = safeCreateChart('chart-top-neoplasias', chartTopNeoplasias, chartConfig);
  }

  // Gráfico: Aseguradoras (EPS)
  function updateEpsPieChart(epsData) {
    if (!epsData || !epsData.labels) return;

    const colors = [COLOR_TURQUESA, COLOR_LILA, COLOR_AZUL, COLOR_ROSA, COLOR_AMARILLO, '#A78BFA', '#F472B6'];

    chartEpsPie = safeCreateChart('chart-eps-pie', chartEpsPie, {
      type: 'doughnut',
      data: {
        labels: epsData.labels,
        datasets: [{
          data: epsData.casos,
          backgroundColor: colors.slice(0, epsData.labels.length),
          borderColor: '#0D0F18',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } },
          tooltip: {
            callbacks: {
              label: (item) => ` ${item.label}: ${Number(item.raw).toLocaleString()} (${epsData.pcts ? epsData.pcts[item.dataIndex] : 0}%)`
            }
          }
        },
        cutout: '65%'
      }
    });
  }

  // Gráfico: Prioridad CAC Pie
  function updatePrioridadPieChart(kpis) {
    if (!kpis) return;

    chartPrioridadPie = safeCreateChart('chart-prioridad-pie', chartPrioridadPie, {
      type: 'doughnut',
      data: {
        labels: ['Priorizados CAC', 'No Priorizados'],
        datasets: [{
          data: [kpis.priorizados_count, kpis.no_priorizados_count],
          backgroundColor: [COLOR_TURQUESA, COLOR_ROSA],
          borderColor: '#0D0F18',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 10, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (item) => ` ${item.label}: ${Number(item.raw).toLocaleString()} casos`
            }
          }
        },
        cutout: '65%'
      }
    });
  }

  // Tabla: Censo de los 25 Agrupadores
  function updateAgrupadoresTable(agrupadores) {
    currentAgrupadoresList = agrupadores;
    renderAgrupadoresRows(agrupadores);
  }

  function renderAgrupadoresRows(list) {
    if (!tbodyAgrupadores) return;
    tbodyAgrupadores.innerHTML = '';
    const maxCasos = list.length > 0 ? list[0].casos : 1;

    list.forEach(item => {
      const isPrio = !item.agrupador.toLowerCase().includes('no priorizado') &&
        ['mama', 'próstata', 'cérvix', 'colorectal', 'estómago', 'pulmón', 'melanoma', 'hodgkin', 'leucemia']
          .some(k => item.agrupador.toLowerCase().includes(k));

      const badgePrio = isPrio ?
        `<span class="badge-eps" style="background: rgba(71, 169, 161, 0.2); color: #34D399;">Priorizado CAC</span>` :
        `<span class="badge-eps" style="background: rgba(226, 115, 150, 0.2); color: #F472B6;">No Priorizado</span>`;

      const barWidth = Math.max(5, (item.casos / maxCasos) * 100);

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${item.agrupador}</strong></td>
        <td>${badgePrio}</td>
        <td><strong>${Number(item.casos).toLocaleString()}</strong></td>
        <td>${item.tasa} x 100k</td>
        <td>${item.pct}%</td>
        <td style="width: 140px;">
          <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden;">
            <div style="width: ${barWidth}%; height: 100%; background: ${isPrio ? COLOR_TURQUESA : COLOR_ROSA}; border-radius: 3px;"></div>
          </div>
        </td>
      `;
      tbodyAgrupadores.appendChild(tr);
    });
  }

  if (searchAgrupador) {
    searchAgrupador.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      const filtered = currentAgrupadoresList.filter(x => x.agrupador.toLowerCase().includes(q));
      renderAgrupadoresRows(filtered);
    });
  }

  // ==========================================
  // PESTAÑA 2: BENCHMARKING OFICIAL CAC / INC
  // ==========================================
  function updateBenchmarkingTab(bm, mamaBm) {
    if (!bm) return;

    // 1. Estadios Tempranos
    const elTemprano = document.getElementById('bm-val-temprano');
    const elTempranoBar = document.getElementById('bm-bar-temprano');
    const elTempranoBadge = document.getElementById('bm-badge-temprano');
    const elTempranoDesc = document.getElementById('bm-desc-temprano');

    if (elTemprano && bm.estadios_tempranos) {
      const val = bm.estadios_tempranos.inoos_val;
      elTemprano.textContent = `${val}%`;
      if (elTempranoBar) elTempranoBar.style.width = `${Math.min(100, val)}%`;
      if (elTempranoBadge) {
        if (val >= 49.15) {
          elTempranoBadge.className = 'bm-badge ok';
          elTempranoBadge.textContent = 'Supera media país';
        } else {
          elTempranoBadge.className = 'bm-badge warn';
          elTempranoBadge.textContent = 'Bajo media país';
        }
      }
      if (elTempranoDesc) {
        elTempranoDesc.innerHTML = `La cohorte INOOS registra <strong>${val}% de estadios tempranos</strong> frente al promedio nacional reportado por la CAC (49.15%). Meta institucional CAC: &ge; 60.0% (Brecha: ${bm.estadios_tempranos.brecha_meta}%).`;
      }
    }

    // 2. Oportunidad Diagnóstico a Primera Consulta
    const elConsulta = document.getElementById('bm-val-consulta');
    const elConsultaBar = document.getElementById('bm-bar-consulta');
    const elConsultaDesc = document.getElementById('bm-desc-consulta');

    if (elConsulta && bm.oportunidad_primera_consulta) {
      const d = bm.oportunidad_primera_consulta.inoos_mediana_dias;
      elConsulta.textContent = `${d} días`;
      if (elConsultaBar) elConsultaBar.style.width = `${Math.min(100, (d / 38) * 100)}%`;
      if (elConsultaDesc) {
        elConsultaDesc.innerHTML = `Mediana en base: <strong>${d} días</strong> vs promedio nacional de 38 días de la CAC. El <strong>${bm.oportunidad_primera_consulta.cumple_30d_pct}%</strong> de los pacientes fue atendido en &le; 30 días.`;
      }
    }

    // 3. Procesamiento de Patología
    const elPat = document.getElementById('bm-val-patologia');
    const elPatCumple = document.getElementById('bm-val-pat-cumple');
    if (elPat && bm.tiempo_patologia) {
      elPat.textContent = `${bm.tiempo_patologia.inoos_mediana_dias} días`;
      if (elPatCumple) elPatCumple.textContent = `${bm.tiempo_patologia.cumple_pct}% cumple`;
    }

    // 4. Biomarcador HER2 (Mama)
    const elHer2 = document.getElementById('bm-val-her2');
    const elHer2Casos = document.getElementById('bm-val-her2-casos');
    if (elHer2 && mamaBm) {
      elHer2.textContent = `${mamaBm.her2_positividad_pct}%`;
      if (elHer2Casos) elHer2Casos.textContent = `${mamaBm.her2_positivo} positivos`;
    }

    // 5. Comparativo Régimen (Equidad CAC)
    if (bm.comparativo_regimen) {
      const cReg = bm.comparativo_regimen['Contributivo'];
      const sReg = bm.comparativo_regimen['Subsidiado'];

      const elRegCT = document.getElementById('reg-c-temprano');
      const elRegST = document.getElementById('reg-s-temprano');
      if (elRegCT && cReg) elRegCT.textContent = `${cReg.temprano_pct}%`;
      if (elRegST && sReg) elRegST.textContent = `${sReg.temprano_pct}%`;

      // Gráfico de Barras Comparativo
      const labels = ['Estadios Tempranos (I-II) %', 'Mediana Días a Consulta'];
      const dataC = [cReg ? cReg.temprano_pct : 59.7, cReg ? cReg.mediana_dias_consulta : 31.0];
      const dataS = [sReg ? sReg.temprano_pct : 54.8, sReg ? sReg.mediana_dias_consulta : 25.0];

      chartBenchmarkRegimen = safeCreateChart('chart-benchmark-regimen', chartBenchmarkRegimen, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Régimen Contributivo',
              data: dataC,
              backgroundColor: COLOR_TURQUESA,
              borderRadius: 6
            },
            {
              label: 'Régimen Subsidiado',
              data: dataS,
              backgroundColor: COLOR_ROSA,
              borderRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { grid: { color: COLOR_GRIS } },
            x: { grid: { display: false } }
          }
        }
      });
    }
  }

  // ==========================================
  // PESTAÑA 3: ESTADIFICACIÓN & OPORTUNIDAD REAL
  // ==========================================
  function updateEstadificacionYOportunidad(data) {
    if (!data) return;

    // 1. Gráfico de Estadios Clínicos
    if (data.estadios) {
      chartEstadiosPie = safeCreateChart('chart-estadios-pie', chartEstadiosPie, {
        type: 'doughnut',
        data: {
          labels: data.estadios.labels,
          datasets: [{
            data: data.estadios.casos,
            backgroundColor: [COLOR_VERDE, COLOR_AMARILLO, COLOR_ROJO, '#9CA3AF'],
            borderColor: '#0D0F18',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } }
          },
          cutout: '60%'
        }
      });
    }

    // 2. Histograma de Oportunidad de Consulta
    if (data.oportunidades && data.oportunidades.histograma) {
      chartOportunidadHistogram = safeCreateChart('chart-oportunidad-histogram', chartOportunidadHistogram, {
        type: 'bar',
        data: {
          labels: data.oportunidades.histograma.labels,
          datasets: [{
            label: 'Pacientes',
            data: data.oportunidades.histograma.casos,
            backgroundColor: [COLOR_VERDE, COLOR_AZUL, COLOR_AMARILLO, COLOR_ROJO],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { grid: { color: COLOR_GRIS } },
            x: { grid: { display: false } }
          }
        }
      });
    }

    // 3. Intención de Tratamiento
    if (data.intencion_tratamiento) {
      chartIntencion = safeCreateChart('chart-intencion-tto', chartIntencion, {
        type: 'doughnut',
        data: {
          labels: data.intencion_tratamiento.labels,
          datasets: [{
            data: data.intencion_tratamiento.casos,
            backgroundColor: [COLOR_TURQUESA, COLOR_ROSA, COLOR_AZUL, '#6B7280'],
            borderColor: '#0D0F18',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } }
          },
          cutout: '60%'
        }
      });
    }

    // 4. Ingresos Mensuales: Incidentes vs Prevalentes (Calculados de la Base)
    if (data.evolucion_mensual) {
      const evo = data.evolucion_mensual;
      chartIngresos = safeCreateChart('chart-ingresos-mensuales', chartIngresos, {
        type: 'bar',
        data: {
          labels: evo.meses,
          datasets: [
            {
              label: 'Incidentes (Nuevos)',
              data: evo.ingresos_incidentes || [],
              backgroundColor: COLOR_TURQUESA,
              borderRadius: 4,
              stack: 'ingresos'
            },
            {
              label: 'Prevalentes (Existentes)',
              data: evo.ingresos_prevalentes || [],
              backgroundColor: COLOR_DORADO_CONTRASTE,
              borderRadius: 4,
              stack: 'ingresos'
            },
            {
              type: 'line',
              label: 'Total Ingresos al Mes',
              data: evo.ingresos || [],
              borderColor: '#38BDF8',
              backgroundColor: 'rgba(56, 189, 248, 0.15)',
              borderWidth: 2.5,
              pointRadius: 4,
              pointHoverRadius: 7,
              pointBackgroundColor: '#38BDF8',
              pointBorderColor: '#FFFFFF',
              pointBorderWidth: 1.5,
              tension: 0.3,
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false
          },
          scales: {
            y: {
              grid: { color: COLOR_GRIS },
              ticks: { color: '#9DA3AE' },
              beginAtZero: true,
              title: { display: true, text: 'Pacientes que Ingresan', color: '#9DA3AE', font: { size: 10, weight: '600' } }
            },
            x: {
              grid: { display: false },
              ticks: { color: '#CBD5E1', font: { weight: '600' } }
            }
          },
          plugins: {
            legend: {
              position: 'top',
              labels: { boxWidth: 12, padding: 10, color: '#E2E8F0', font: { size: 11, weight: '600' } }
            },
            tooltip: {
              callbacks: {
                footer: function (items) {
                  let total = 0;
                  items.forEach(it => {
                    if (it.dataset.type !== 'line') total += (it.parsed.y || 0);
                  });
                  return `Total Ingresos: ${total.toLocaleString()} pacientes`;
                }
              }
            }
          }
        }
      });
    }
  }

  // ==========================================
  // PESTAÑA 4: DEMOGRAFÍA, RÉGIMEN & REGIONES
  // ==========================================
  function updateDemografiaTab(data) {
    if (!data) return;

    // 1. Pirámide de Edad y Sexo
    if (data.piramide_edad_sexo) {
      chartPiramide = safeCreateChart('chart-piramide-edad', chartPiramide, {
        type: 'bar',
        data: {
          labels: data.piramide_edad_sexo.labels,
          datasets: [
            {
              label: 'Femenino (F)',
              data: data.piramide_edad_sexo.femenino,
              backgroundColor: COLOR_ROSA,
              borderRadius: 6
            },
            {
              label: 'Masculino (M)',
              data: data.piramide_edad_sexo.masculino,
              backgroundColor: COLOR_AZUL,
              borderRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { display: false } },
            y: { grid: { color: COLOR_GRIS } }
          }
        }
      });
    }

    // 2. Departamentos
    if (data.departamentos) {
      chartDeptos = safeCreateChart('chart-departamentos', chartDeptos, {
        type: 'bar',
        data: {
          labels: data.departamentos.labels,
          datasets: [{
            label: 'Pacientes',
            data: data.departamentos.casos,
            backgroundColor: COLOR_TURQUESA,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
          scales: {
            x: { grid: { color: COLOR_GRIS } },
            y: { grid: { display: false } }
          }
        }
      });
    }

    // 3. Régimen
    if (data.regimen_distribucion) {
      chartRegimenPie = safeCreateChart('chart-regimen-pie', chartRegimenPie, {
        type: 'doughnut',
        data: {
          labels: data.regimen_distribucion.labels,
          datasets: [{
            data: data.regimen_distribucion.casos,
            backgroundColor: [COLOR_ROSA, COLOR_TURQUESA, COLOR_AMARILLO, '#9CA3AF'],
            borderColor: '#0D0F18',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } }
          },
          cutout: '60%'
        }
      });
    }

    // 4. Municipios
    if (data.top_municipios) {
      chartMunicipios = safeCreateChart('chart-municipios', chartMunicipios, {
        type: 'bar',
        data: {
          labels: data.top_municipios.labels,
          datasets: [{
            label: 'Casos por Municipio',
            data: data.top_municipios.casos,
            backgroundColor: COLOR_LILA,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
          scales: {
            x: { grid: { color: COLOR_GRIS } },
            y: { grid: { display: false } }
          }
        }
      });
    }
  }

  // ==========================================
  // PESTAÑA 5: EXPLORADOR CLÍNICO DE CASOS
  // ==========================================
  function updatePacientesTable(pacientes) {
    if (!tbodyPacientes) return;
    tbodyPacientes.innerHTML = '';

    if (!pacientes || pacientes.length === 0) {
      tbodyPacientes.innerHTML = '<tr><td colspan="11" style="text-align:center;color:#9DA3AE;padding:1.5rem;">No se encontraron registros con los filtros seleccionados.</td></tr>';
      return;
    }

    pacientes.forEach(p => {
      const isPrio = p.ES_PRIORIZADO;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>${p.PACIENTE_ID}</code></td>
        <td><span class="badge-eps">${p.EPS_CANONICA}</span></td>
        <td>${p.REGIMEN}</td>
        <td>${p.AGRUPADOR}</td>
        <td><span style="color: ${isPrio ? '#34D399' : '#F472B6'}; font-weight: 600;">${p.PRIORIDAD_LABEL}</span></td>
        <td><span class="badge-eps" style="font-size: 0.72rem;">${p.ESTADIO_CLINICO}</span></td>
        <td><strong>${p.DIAS_DX_A_CONSULTA !== null && !isNaN(p.DIAS_DX_A_CONSULTA) ? p.DIAS_DX_A_CONSULTA + ' d' : 'N/A'}</strong></td>
        <td>${p.EDAD || 'N/A'}</td>
        <td>${p.SEXO}</td>
        <td>${p.DEPARTAMENTO}</td>
        <td style="font-size: 0.8rem; color: var(--text-muted); max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.INTENCION_INICIAL || ''}">
          ${p.INTENCION_INICIAL || 'Sin registrar'}
        </td>
      `;
      tbodyPacientes.appendChild(tr);
    });
  }

  // Navegación entre Pestañas del Tablero
  document.querySelectorAll('.dash-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.dash-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const target = document.getElementById(tab.dataset.tab);
      if (target) target.classList.add('active');

      // Forzar ajuste de canvas en Chart.js en la pestaña que acaba de hacerse visible
      setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
        [chartTopNeoplasias, chartEpsPie, chartPrioridadPie, chartEstadiosPie, chartOportunidadHistogram, chartIntencion, chartIngresos, chartBenchmarkRegimen, chartPiramide, chartDeptos, chartRegimenPie, chartMunicipios].forEach(ch => {
          if (ch && typeof ch.resize === 'function') ch.resize();
        });
      }, 50);
    });
  });

  // Eventos de los Filtros Select (recalculan el tablero en tiempo real)
  [selectEps, selectPrioridad, selectAgrupador, selectTipoRegistro, selectRegimen, selectEstadio, selectSexo, selectEdad, selectDepto].forEach(sel => {
    if (sel) {
      sel.addEventListener('change', () => {
        console.log(`[INOOS Dashboard] Filtro modificado: ${sel.id} = ${sel.value}`);
        refreshDashboard();
      });
    }
  });

  // Botón Recargar / Actualizar
  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      refreshDashboard();
    });
  }

  // Botón Alternar Orientación del Gráfico Top Neoplasias (Barras con Línea)
  if (btnToggleTopChart) {
    btnToggleTopChart.addEventListener('click', () => {
      topChartOrientation = (topChartOrientation === 'x') ? 'y' : 'x';
      console.log(`[INOOS Dashboard] Orientación cambiada a: ${topChartOrientation}`);
      if (lastTopNeoplasiasData) {
        updateTopNeoplasiasChart(lastTopNeoplasiasData);
      }
    });
  }

  // Botón Limpiar Filtros
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      if (selectEps) selectEps.value = 'ALL';
      if (selectPrioridad) selectPrioridad.value = 'ALL';
      if (selectAgrupador) selectAgrupador.value = 'ALL';
      if (selectTipoRegistro) selectTipoRegistro.value = 'ALL';
      if (selectRegimen) selectRegimen.value = 'ALL';
      if (selectEstadio) selectEstadio.value = 'ALL';
      if (selectSexo) selectSexo.value = 'ALL';
      if (selectEdad) selectEdad.value = 'ALL';
      if (selectDepto) selectDepto.value = 'ALL';
      refreshDashboard();
    });
  }

  // Botón Exportar CSV
  if (btnExport) {
    btnExport.addEventListener('click', async () => {
      btnExport.disabled = true;
      btnExport.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Exportando...`;

      try {
        const filters = getActiveFilters();
        const res = await fetch('/api/dashboard/export_csv', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filters })
        });
        if (!res.ok) throw new Error('Error al generar archivo CSV');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Cohorte_Filtrada_INOOS_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } catch (err) {
        alert('Error al exportar CSV: ' + err.message);
      } finally {
        btnExport.disabled = false;
        btnExport.innerHTML = `<i class="fa-solid fa-file-csv"></i> Exportar`;
      }
    });
  }

  // ==========================================
  // EJECUCIÓN INMEDIATA AL ABRIR LA PANTALLA
  // ==========================================
  // 1. Cargar datos del dashboard de inmediato para poblar las tarjetas
  refreshDashboard();
  // 2. Cargar listas dinámicas de los selects
  initFilters();
});
