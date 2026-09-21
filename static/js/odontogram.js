document.addEventListener('DOMContentLoaded', function () {
  // --- CSRF: leer el token del meta tag para peticiones AJAX ---
  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function csrfFetch(url, options) {
    options = options || {};
    options.headers = options.headers || {};
    // Si ya es FormData, no sobreescribimos Content-Type (el browser lo hace solo)
    if (!(options.body instanceof FormData)) {
      options.headers['Content-Type'] = options.headers['Content-Type'] || 'application/x-www-form-urlencoded';
    }
    options.headers['X-CSRFToken'] = getCsrfToken();
    options.credentials = 'same-origin'; // enviar cookies de sesión
    return fetch(url, options);
  }

  const patientId = window.PATIENT_ID;
  const modalEl = document.getElementById('toothModal');
  const modal = new bootstrap.Modal(modalEl);
  const modalTitle = document.getElementById('toothModalTitle');
  const form = document.getElementById('toothForm');
  const surfaceSelect = document.getElementById('toothSurface');
  const statusSelect = document.getElementById('toothStatus');
  const noteField = document.getElementById('toothNote');
  const errorEl = document.getElementById('toothFormError');
  const submitBtn = document.getElementById('toothSubmitBtn');
  const cancelEditBtn = document.getElementById('toothCancelEdit');
  const historyList = document.getElementById('toothHistory');

  const fileUploadForm = document.getElementById('toothUploadForm');
  const fileInput = document.getElementById('toothUploadFile');
  const fileDesc = document.getElementById('toothUploadDesc');
  const fileCategory = document.getElementById('toothUploadCategory');
  const attachmentsList = document.getElementById('toothAttachments');
  const filesErrorEl = document.getElementById('toothFilesError');

  const lightboxEl = document.getElementById('toothLightbox');
  const lightboxImg = document.getElementById('toothLightboxImg');
  const lightboxCaption = document.getElementById('toothLightboxCaption');

  const previewImg = document.getElementById('toothPreviewImg');
  const previewPdf = document.getElementById('toothPreviewPdf');
  const previewPdfName = document.getElementById('toothPreviewName');
  const previewPdfOpen = document.getElementById('toothPreviewOpen');
  const previewEmpty = document.getElementById('toothPreviewEmpty');
  const previewHint = document.getElementById('toothPreviewHint');

  function openLightbox(url, caption) {
    lightboxImg.src = url;
    lightboxCaption.textContent = caption || '';
    lightboxEl.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    lightboxEl.classList.remove('open');
    lightboxImg.src = '';
    document.body.style.overflow = '';
  }

  lightboxEl.addEventListener('click', function (e) {
    if (e.target === lightboxEl || e.target.classList.contains('tooth-lightbox-close')) {
      closeLightbox();
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeLightbox();
  });

  let currentTooth = null;
  let currentStatuses = {}; // { '': 'sano', 'V': 'caries', ... } para el diente abierto
  let editingLogId = null;

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function renderHistory(logs) {
    historyList.innerHTML = '';
    if (!logs.length) {
      historyList.innerHTML = '<li class="tooth-history-empty">Todavía no hay anotaciones para este diente.</li>';
      return;
    }
    logs.forEach(function (log) {
      const li = document.createElement('li');

      const top = document.createElement('div');
      top.className = 'th-top';
      const who = document.createElement('span');
      who.textContent = log.dentist;
      const when = document.createElement('span');
      when.textContent = log.created_at;
      top.appendChild(who);
      top.appendChild(when);

      const status = document.createElement('div');
      status.className = 'th-status';
      status.textContent = log.status_label + ' · ' + log.surface_label;

      const note = document.createElement('div');
      note.textContent = log.note;

      const actions = document.createElement('div');
      actions.className = 'th-actions';
      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'th-btn';
      editBtn.setAttribute('aria-label', 'Editar anotación');
      editBtn.textContent = '✎';
      editBtn.addEventListener('click', function () { startEdit(log); });
      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'th-btn th-btn-del';
      delBtn.setAttribute('aria-label', 'Eliminar anotación');
      delBtn.textContent = '✕';
      delBtn.addEventListener('click', function () { removeLog(log.id); });
      actions.appendChild(editBtn);
      actions.appendChild(delBtn);

      li.appendChild(top);
      li.appendChild(status);
      li.appendChild(note);
      li.appendChild(actions);
      historyList.appendChild(li);
    });
  }

  function loadHistory() {
    fetch('/pacientes/' + patientId + '/diente/' + currentTooth)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) return;
        currentStatuses = data.statuses || {};
        renderHistory(data.logs);
      });
  }

  function resetForm() {
    editingLogId = null;
    noteField.value = '';
    errorEl.textContent = '';
    submitBtn.textContent = 'Guardar anotación';
    cancelEditBtn.hidden = true;
    statusSelect.value = currentStatuses[surfaceSelect.value] || 'sano';
  }

  function startEdit(log) {
    editingLogId = log.id;
    surfaceSelect.value = log.surface;
    statusSelect.value = log.status || 'sano';
    noteField.value = log.note;
    errorEl.textContent = '';
    submitBtn.textContent = 'Guardar cambios';
    cancelEditBtn.hidden = false;
  }

  cancelEditBtn.addEventListener('click', function () {
    resetForm();
    statusSelect.value = currentStatuses[surfaceSelect.value] || 'sano';
  });

  function removeLog(logId) {
    if (!confirm('¿Eliminar esta anotación del historial?')) return;
    csrfFetch('/pacientes/' + patientId + '/diente/' + currentTooth + '/log/' + logId + '/eliminar', {
      method: 'POST',
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          if (editingLogId === logId) resetForm();
          loadHistory();
        } else {
          errorEl.textContent = data.error || 'No se pudo eliminar la anotación.';
        }
      })
      .catch(function () {
        errorEl.textContent = 'Error de conexión.';
      });
  }

  function openTooth(toothNumber, surface) {
    currentTooth = toothNumber;
    resetForm();
    surfaceSelect.value = surface || '';
    statusSelect.value = currentStatuses[surfaceSelect.value] || 'sano';
    modalTitle.textContent = 'Cargando diente ' + toothNumber + '…';
    historyList.innerHTML = '';
    filesErrorEl.textContent = '';
    modal.show();
    loadToothAttachments(toothNumber);

    fetch('/pacientes/' + patientId + '/diente/' + toothNumber)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) return;
        currentStatuses = data.statuses || {};
        surfaceSelect.value = surface || '';
        statusSelect.value = currentStatuses[surfaceSelect.value] || 'sano';
        modalTitle.textContent = 'Diente ' + data.tooth_number;
        renderHistory(data.logs);
      })
      .catch(function () {
        modalTitle.textContent = 'Diente ' + toothNumber;
        historyList.innerHTML = '<li class="tooth-history-empty">No se pudo cargar el historial.</li>';
      });
  }

  // Al cambiar la cara seleccionada en el modal, mostrar el estado actual de esa cara
  surfaceSelect.addEventListener('change', function () {
    statusSelect.value = currentStatuses[surfaceSelect.value] || 'sano';
  });

  document.querySelectorAll('.tooth-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      const target = e.target.closest('[data-surface]');
      const surface = target ? target.dataset.surface : '';
      openTooth(btn.dataset.tooth, surface);
    });
  });

  let previewFile = null;

  function fileCaption(item) {
    return item.original_filename + (item.description ? ' · ' + item.description : '');
  }

  function showPreviewEmpty(text) {
    previewFile = null;
    previewImg.style.display = 'none';
    previewPdf.style.display = 'none';
    previewEmpty.style.display = 'block';
    previewEmpty.textContent = text;
    previewHint.textContent = '';
  }

  function selectPreview(item, li) {
    previewFile = item;
    document.querySelectorAll('.tooth-file-item.selected').forEach(function (el) {
      el.classList.remove('selected');
    });
    if (li) li.classList.add('selected');

    previewEmpty.style.display = 'none';
    if (item.is_image) {
      previewImg.src = item.url;
      previewImg.style.display = 'block';
      previewPdf.style.display = 'none';
      previewHint.textContent = '👁 Hacé clic en la imagen para verla en pantalla completa';
    } else {
      previewImg.style.display = 'none';
      previewPdf.style.display = 'flex';
      previewPdfName.textContent = item.original_filename;
      previewPdfOpen.href = item.url;
      previewHint.textContent = '';
    }
  }

  previewImg.addEventListener('click', function () {
    if (previewFile && previewFile.is_image) {
      openLightbox(previewFile.url, fileCaption(previewFile));
    }
  });

  function renderAttachments(list) {
    attachmentsList.innerHTML = '';
    if (!list.length) {
      showPreviewEmpty('Sin estudios cargados para este diente.');
      return;
    }

    list.forEach(function (item, idx) {
      const li = document.createElement('li');
      li.className = 'tooth-file-item';
      li.title = item.original_filename;

      if (item.is_image) {
        const img = document.createElement('img');
        img.className = 'tooth-file-thumb';
        img.src = item.url;
        img.alt = item.original_filename;
        li.appendChild(img);
      } else {
        const ph = document.createElement('div');
        ph.className = 'tooth-file-pdf';
        ph.textContent = 'PDF';
        li.appendChild(ph);
      }

      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'tooth-file-del';
      del.setAttribute('aria-label', 'Eliminar archivo');
      del.textContent = '✕';
      del.addEventListener('click', function (ev) {
        ev.stopPropagation();
        if (!confirm('¿Eliminar ' + item.original_filename + '?')) return;
        csrfFetch('/pacientes/' + patientId + '/diente/' + currentTooth + '/adjuntos/' + item.id + '/eliminar', {
          method: 'POST',
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.ok) loadToothAttachments(currentTooth);
          })
          .catch(function () {
            filesErrorEl.textContent = 'Error de conexión al eliminar.';
          });
      });
      li.appendChild(del);

      li.addEventListener('click', function () {
        selectPreview(item, li);
      });

      attachmentsList.appendChild(li);

      if (idx === 0) selectPreview(item, li);
    });
  }

  function loadToothAttachments(toothNumber) {
    showPreviewEmpty('Cargando estudios…');
    fetch('/pacientes/' + patientId + '/diente/' + toothNumber + '/adjuntos')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderAttachments(data.attachments || []);
      })
      .catch(function () {
        showPreviewEmpty('No se pudieron cargar los estudios.');
      });
  }

  fileUploadForm.addEventListener('submit', function (e) {
    e.preventDefault();
    filesErrorEl.textContent = '';
    if (!fileInput.files.length) {
      filesErrorEl.textContent = 'Seleccioná un archivo primero.';
      return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('category', fileCategory.value);
    formData.append('description', fileDesc.value.trim());

    csrfFetch('/pacientes/' + patientId + '/diente/' + currentTooth + '/adjuntos', {
      method: 'POST',
      body: formData,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) {
          filesErrorEl.textContent = data.error || 'No se pudo subir el archivo.';
          return;
        }
        fileInput.value = '';
        fileDesc.value = '';
        loadToothAttachments(currentTooth);
      })
      .catch(function () {
        filesErrorEl.textContent = 'Error de conexión. Intentá nuevamente.';
      });
  });

  function updateToothIcon(toothNumber, surface, status) {
    const btn = document.querySelector('.tooth-btn[data-tooth="' + toothNumber + '"]');
    if (!btn) return;
    const svg = btn.querySelector('.tooth-svg');

    if (surface === '') {
      // Estado general: reemplaza el overlay del ícono completo
      btn.classList.toggle('has-general', status !== 'sano');
      const oldOverlay = svg.querySelector('.tooth-overlay');
      if (oldOverlay) oldOverlay.remove();
      if (status !== 'sano') {
        const overlay = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        overlay.setAttribute('x', '0');
        overlay.setAttribute('y', '0');
        overlay.setAttribute('width', '40');
        overlay.setAttribute('height', '40');
        overlay.setAttribute('class', 'tooth-overlay overlay-' + status);
        svg.appendChild(overlay);
      }
    } else {
      const face = svg.querySelector('.face[data-surface="' + surface + '"]');
      if (face) {
        face.setAttribute('class', 'face status-' + status);
        face.setAttribute('data-surface', surface);
      }
    }
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    errorEl.textContent = '';

    const surface = surfaceSelect.value;
    const status = statusSelect.value;
    const formData = new FormData();
    formData.append('surface', surface);
    formData.append('status', status);
    formData.append('note', noteField.value.trim());

    const url = editingLogId
      ? '/pacientes/' + patientId + '/diente/' + currentTooth + '/log/' + editingLogId
      : '/pacientes/' + patientId + '/diente/' + currentTooth;

    csrfFetch(url, {
      method: 'POST',
      body: formData,
    })
      .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
      .then(function (result) {
        if (!result.data.ok) {
          errorEl.textContent = result.data.error || 'No se pudo guardar la anotación.';
          return;
        }

        currentStatuses[surface] = status;
        updateToothIcon(currentTooth, surface, status);
        loadHistory();
        resetForm();
      })
      .catch(function () {
        errorEl.textContent = 'Error de conexión. Intentá nuevamente.';
      });
  });
});
