document.addEventListener('DOMContentLoaded', function () {
  const patientId = window.PATIENT_ID;
  const modalEl = document.getElementById('toothModal');
  const modal = new bootstrap.Modal(modalEl);
  const modalTitle = document.getElementById('toothModalTitle');
  const form = document.getElementById('toothForm');
  const surfaceSelect = document.getElementById('toothSurface');
  const statusSelect = document.getElementById('toothStatus');
  const noteField = document.getElementById('toothNote');
  const errorEl = document.getElementById('toothFormError');
  const historyList = document.getElementById('toothHistory');

  let currentTooth = null;
  let currentStatuses = {}; // { '': 'sano', 'V': 'caries', ... } para el diente abierto

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
      li.innerHTML =
        '<div class="th-top"><span>' + log.dentist + '</span><span>' + log.created_at + '</span></div>' +
        '<div class="th-status">' + log.status_label + ' · ' + log.surface_label + '</div>' +
        '<div>' + escapeHtml(log.note) + '</div>';
      historyList.appendChild(li);
    });
  }

  function openTooth(toothNumber, surface) {
    currentTooth = toothNumber;
    errorEl.textContent = '';
    noteField.value = '';
    modalTitle.textContent = 'Cargando diente ' + toothNumber + '…';
    historyList.innerHTML = '';
    modal.show();

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

    fetch('/pacientes/' + patientId + '/diente/' + currentTooth, {
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
        noteField.value = '';

        const li = document.createElement('li');
        li.innerHTML =
          '<div class="th-top"><span>' + result.data.log.dentist + '</span><span>' + result.data.log.created_at + '</span></div>' +
          '<div class="th-status">' + result.data.log.status_label + ' · ' + result.data.log.surface_label + '</div>' +
          '<div>' + escapeHtml(result.data.log.note) + '</div>';
        if (historyList.firstElementChild && historyList.firstElementChild.classList.contains('tooth-history-empty')) {
          historyList.innerHTML = '';
        }
        historyList.insertBefore(li, historyList.firstChild);
      })
      .catch(function () {
        errorEl.textContent = 'Error de conexión. Intentá nuevamente.';
      });
  });
});
