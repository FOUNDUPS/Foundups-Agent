(() => {
  const dialog = document.getElementById('enquiry-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  let trigger;
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href="/contact/"]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    trigger = link;
    const frame = dialog.querySelector('iframe');
    if (!frame.src) frame.src = frame.dataset.src;
    dialog.showModal();
    document.body.classList.add('dialog-open');
    document.getElementById('close-enquiry').focus();
  });
  document.getElementById('close-enquiry').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    document.body.classList.remove('dialog-open');
    trigger?.focus();
  });
  dialog.addEventListener('click', event => { if (event.target === dialog) {
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
  }});
})();
