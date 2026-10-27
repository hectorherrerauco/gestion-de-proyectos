// Auto-cierre de mensajes flash (los que contienen enlaces permanecen para poder copiarlos)
document.querySelectorAll('.flash').forEach((el, i) => {
  const close = () => { el.classList.add('hide'); setTimeout(() => el.remove(), 300); };
  el.querySelector('.flash-close')?.addEventListener('click', close);
  if (el.textContent.includes('http')) { el.classList.add('sticky'); return; }
  setTimeout(close, 5000 + i * 400);
});

// Cambio de rol inmediato al seleccionar
document.querySelectorAll('.role-select').forEach(sel => {
  sel.addEventListener('change', () => sel.form.submit());
});
