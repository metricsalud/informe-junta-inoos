document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const fileDisplayName = document.getElementById('file-display-name');
  const selectActiveFile = document.getElementById('select-active-file');
  const filesBadge = document.getElementById('files-badge');
  const selectMes = document.getElementById('select-mes');
  const inputAno = document.getElementById('input-ano');
  const lastUpdate = document.getElementById('last-update');
  const btnGenerate = document.getElementById('btn-generate');
  const btnDownload = document.getElementById('btn-download');
  const btnVerify = document.getElementById('btn-verify');
  const terminal = document.getElementById('terminal-console');
  const progressContainer = document.getElementById('progress-container');
  const progressFill = document.getElementById('progress-fill');

  let currentExcelPath = "BD pacientes Inoos SEPTIEMBRE 2026 .xlsx";
  let lastGeneratedFilename = null;

  function logTerminal(message, type = 'info') {
    const line = document.createElement('div');
    line.className = `term-line ${type}`;
    const timestamp = new Date().toLocaleTimeString();
    line.textContent = `[${timestamp}] ${message}`;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
  }

  // 0. Manejo de Tema (Claro / Oscuro) - Predeterminado Claro
  function initThemeToggle() {
    const themeBtn = document.getElementById('theme-toggle-btn');
    const themeIcon = document.getElementById('theme-icon');
    const themeLabel = document.getElementById('theme-label');

    function applyTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('inoos-theme', theme);
      const isDark = theme === 'dark';
      if (themeIcon) themeIcon.className = isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
      if (themeLabel) themeLabel.textContent = isDark ? 'Modo Claro' : 'Modo Oscuro';
    }

    const currentTheme = localStorage.getItem('inoos-theme') || 'light';
    applyTheme(currentTheme);

    if (themeBtn) {
      themeBtn.addEventListener('click', () => {
        const nextTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        applyTheme(nextTheme);
      });
    }
  }
  initThemeToggle();

  // 1. Cargar lista de archivos disponibles en el servidor
  async function loadAvailableFiles() {
    try {
      const res = await fetch('/api/files');
      const data = await res.json();
      if (data.status === 'success' && selectActiveFile) {
        selectActiveFile.innerHTML = '';
        if (filesBadge) {
          filesBadge.textContent = `${data.files.length} disponible${data.files.length !== 1 ? 's' : ''}`;
        }
        
        data.files.forEach(f => {
          const opt = document.createElement('option');
          opt.value = f.filepath;
          opt.textContent = `${f.filename} (${f.mes} ${f.ano})`;
          if (f.filepath === currentExcelPath || f.filename === currentExcelPath) {
            opt.selected = true;
          }
          selectActiveFile.appendChild(opt);
        });
      }
    } catch (err) {
      console.warn('No se pudo listar archivos:', err);
    }
  }

  // 2. Cargar y reflejar métricas en toda la pantalla principal
  async function loadKPIs() {
    try {
      const mesVal = selectMes ? selectMes.value : 'Septiembre';
      const anoVal = inputAno ? inputAno.value : '2026';
      const url = `/api/kpis?excel=${encodeURIComponent(currentExcelPath)}&mes=${encodeURIComponent(mesVal)}&ano=${encodeURIComponent(anoVal)}`;
      
      const res = await fetch(url);
      const data = await res.json();
      
      if (data.status === 'success') {
        // Actualizar nombres y encabezados de corte
        if (fileDisplayName) fileDisplayName.textContent = data.active_filename;
        if (lastUpdate) lastUpdate.textContent = data.corte_display;

        // Actualizar tarjetas de KPI
        const elTotal = document.getElementById('kpi-total');
        const elPrio = document.getElementById('kpi-priorizados');
        const elNoPrio = document.getElementById('kpi-no-priorizados');

        if (elTotal) elTotal.textContent = Number(data.total_registros).toLocaleString();
        if (elPrio) elPrio.textContent = Number(data.prioridad_distribucion['Priorizados']).toLocaleString();
        if (elNoPrio) elNoPrio.textContent = Number(data.prioridad_distribucion['No Priorizados']).toLocaleString();

        // Actualizar tabla de Aseguradoras (EPS)
        const tbody = document.getElementById('table-eps-body');
        if (tbody) {
          tbody.innerHTML = '';
          const total = data.total_registros || 1;

          for (const [eps, count] of Object.entries(data.eps_distribucion || {})) {
            const pob = (data.poblaciones && data.poblaciones[eps]) || 0;
            const tasa = pob > 0 ? ((count / pob) * 100000).toFixed(1) : '-';
            const pct = ((count / total) * 100).toFixed(1);

            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td><span class="badge-eps">${eps}</span></td>
              <td><strong>${Number(count).toLocaleString()}</strong></td>
              <td>${pob > 0 ? Number(pob).toLocaleString() : 'N/A'}</td>
              <td>${tasa !== '-' ? `${tasa} x 100k` : 'N/A'}</td>
              <td>${pct}%</td>
            `;
            tbody.appendChild(tr);
          }
        }

        // Actualizar Top 5 Neoplasias
        const topList = document.getElementById('top-cancers-list');
        if (topList) {
          topList.innerHTML = '';
          const colors = ['#34D399', '#60A5FA', '#F472B6', '#FBBF24', '#A78BFA'];
          let colorIdx = 0;
          for (const [cancer, count] of Object.entries(data.top_tumores || {})) {
            const item = document.createElement('div');
            item.style = 'background: rgba(255,255,255,0.03); padding: 10px 14px; border-radius: var(--radius-md); border: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center;';
            item.innerHTML = `
              <span style="font-size: 0.85rem; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${cancer}">${cancer}</span>
              <strong style="color: ${colors[colorIdx % colors.length]};">${Number(count).toLocaleString()} casos</strong>
            `;
            topList.appendChild(item);
            colorIdx++;
          }
        }
      } else {
        logTerminal(`[ERROR AL CARGAR MÉTRICAS] ${data.error}`, 'error');
      }
    } catch (err) {
      logTerminal(`Error de conexión al cargar métricas: ${err.message}`, 'error');
    }
  }

  // 3. Subida de Archivo Nuevo
  async function uploadFile(file) {
    if (!file) return;
    
    logTerminal(`Subiendo y analizando cohorte clínica: ${file.name}...`, 'info');
    if (fileDisplayName) {
      fileDisplayName.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Procesando ${file.name}...`;
    }
    dropZone.style.opacity = '0.7';
    dropZone.style.pointerEvents = 'none';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      
      if (data.status === 'success') {
        currentExcelPath = data.filepath;
        if (fileDisplayName) fileDisplayName.textContent = data.filename;
        
        // Auto-seleccionar mes y año detectados del archivo
        if (data.detected_mes && selectMes) selectMes.value = data.detected_mes;
        if (data.detected_ano && inputAno) inputAno.value = data.detected_ano;
        
        logTerminal(`[ÉXITO] Archivo cargado e indexado: ${data.filename}`, 'success');
        logTerminal(`Total registros auditados: ${Number(data.total_registros).toLocaleString()} | Periodo: ${data.detected_mes} ${data.detected_ano}`, 'success');
        
        // Reflejar inmediatamente en la pantalla principal
        await loadKPIs();
        await loadAvailableFiles();
      } else {
        if (fileDisplayName) fileDisplayName.textContent = "Error al procesar archivo";
        logTerminal(`[ERROR] ${data.error}`, 'error');
      }
    } catch (err) {
      if (fileDisplayName) fileDisplayName.textContent = "Error de conexión";
      logTerminal(`Error de red al subir archivo: ${err.message}`, 'error');
    } finally {
      dropZone.style.opacity = '1';
      dropZone.style.pointerEvents = 'auto';
      fileInput.value = '';
    }
  }

  // Eventos de Drag & Drop y Selección
  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      uploadFile(fileInput.files[0]);
    }
  });

  // Selector de bases disponibles ya cargadas
  if (selectActiveFile) {
    selectActiveFile.addEventListener('change', async () => {
      const selectedPath = selectActiveFile.value;
      if (!selectedPath) return;
      
      logTerminal(`Cambiando base activa a: ${selectActiveFile.options[selectActiveFile.selectedIndex].text}...`, 'info');
      try {
        const res = await fetch('/api/set_active_file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filepath: selectedPath })
        });
        const data = await res.json();
        if (data.status === 'success') {
          currentExcelPath = data.active.filepath;
          if (fileDisplayName) fileDisplayName.textContent = data.active.filename;
          if (selectMes && data.active.mes) selectMes.value = data.active.mes;
          if (inputAno && data.active.ano) inputAno.value = data.active.ano;
          
          logTerminal(`[OK] Base activa establecida: ${data.active.filename} (${data.total_registros} registros)`, 'success');
          await loadKPIs();
        } else {
          logTerminal(`[ERROR] ${data.error}`, 'error');
        }
      } catch (err) {
        logTerminal(`Error al cambiar base activa: ${err.message}`, 'error');
      }
    });
  }

  // Eventos al cambiar Mes o Año
  if (selectMes) {
    selectMes.addEventListener('change', () => {
      logTerminal(`Periodo actualizado a ${selectMes.value} ${inputAno.value}. Actualizando pantalla...`, 'info');
      loadKPIs();
    });
  }

  if (inputAno) {
    inputAno.addEventListener('change', () => {
      logTerminal(`Periodo actualizado a ${selectMes.value} ${inputAno.value}. Actualizando pantalla...`, 'info');
      loadKPIs();
    });
  }

  // 4. Generar Informe PPTX
  btnGenerate.addEventListener('click', async () => {
    const mes = selectMes.value;
    const ano = inputAno.value;

    btnGenerate.disabled = true;
    btnGenerate.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generando 115 láminas (${mes} ${ano})...`;
    progressContainer.style.display = 'block';
    progressFill.style.width = '15%';

    logTerminal(`Iniciando generación de informe para ${mes} ${ano}...`, 'info');
    logTerminal(`Base fuente: ${currentExcelPath}`, 'info');

    const t1 = setTimeout(() => { progressFill.style.width = '45%'; }, 800);
    const t2 = setTimeout(() => { progressFill.style.width = '75%'; }, 2000);

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mes: mes,
          ano: parseInt(ano),
          excel_path: currentExcelPath
        })
      });

      clearTimeout(t1);
      clearTimeout(t2);
      const data = await res.json();
      progressFill.style.width = '100%';

      if (data.status === 'success') {
        lastGeneratedFilename = data.output_filename;
        logTerminal(`[ÉXITO] ${data.message}`, 'success');
        logTerminal(`Archivo: ${data.output_filename} | ${data.file_size_mb} MB | ${data.slides_count} slides en ${data.duration_seconds}s`, 'success');
        
        btnDownload.style.display = 'inline-flex';
        btnDownload.innerHTML = `<i class="fa-solid fa-download"></i> Descargar ${data.output_filename}`;
      } else {
        logTerminal(`[FALLO] ${data.error}`, 'error');
      }
    } catch (err) {
      logTerminal(`Error de conexión al generar: ${err.message}`, 'error');
    } finally {
      btnGenerate.disabled = false;
      btnGenerate.innerHTML = `<i class="fa-solid fa-bolt"></i> Generar Informe PPTX`;
      setTimeout(() => { progressContainer.style.display = 'none'; }, 2500);
    }
  });

  // 5. Descargar Informe PPTX
  btnDownload.addEventListener('click', () => {
    if (lastGeneratedFilename) {
      window.location.href = `/api/download/${encodeURIComponent(lastGeneratedFilename)}`;
    }
  });

  // 6. Ejecutar Auditoría
  btnVerify.addEventListener('click', async () => {
    btnVerify.disabled = true;
    btnVerify.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Auditando concordancia clínica...`;
    logTerminal(`Ejecutando suite de validación clínica de concordancia...`, 'info');

    try {
      const res = await fetch('/api/test');
      const data = await res.json();
      if (data.status === 'success') {
        logTerminal(`[AUDITORÍA COMPLETADA]`, 'success');
        logTerminal(`Puntos Evaluados: ${data.total_pruebas} | Coincidentes: ${data.exitosas} (${data.porcentaje_concordancia}%)`, 'success');
        logTerminal(`Discrepancias marginales: ${data.discrepancias}`, 'warning');
      } else {
        logTerminal(`Error en auditoría: ${data.error}`, 'error');
      }
    } catch (err) {
      logTerminal(`Error al ejecutar auditoría: ${err.message}`, 'error');
    } finally {
      btnVerify.disabled = false;
      btnVerify.innerHTML = `<i class="fa-solid fa-stethoscope"></i> Ejecutar Auditoría de Concordancia`;
    }
  });

  // Inicialización de la pantalla al cargar
  loadKPIs();
  loadAvailableFiles();
});
