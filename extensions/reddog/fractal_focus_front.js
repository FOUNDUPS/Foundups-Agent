'use strict';

// Canonical RedDog extension face. The Mall serves an identical static projection.
// Keep this function self-contained: the VSIX embeds these trusted bytes in its
// nonce-bound webview rather than loading code from a workspace or remote site.
function renderFractalFocus(container, model, onAsk) {
  const doc = container.ownerDocument;
  const group = doc.createElement('div');
  group.className = 'reddog-fractal-focus';
  group.setAttribute('role', 'group');
  group.setAttribute('aria-label', 'Fractal Mall focus');
  const id = model && model.foundupId;
  const selected = model?.state === 'selected' && typeof id === 'string'
    && id.length <= 80 && /^[a-z0-9]/.test(id) && !/[^a-z0-9_-]/.test(id);
  const label = doc.createElement('span');
  label.setAttribute('data-reddog-fractal-path', '');
  label.textContent = selected ? 'Mall › ' + id
    : (model?.state === 'none' ? 'Mall · No FoundUp selected' : 'Mall · Focus unavailable');
  group.appendChild(label);
  if (selected && model.canAsk === true && typeof onAsk === 'function') {
    const ask = doc.createElement('button');
    ask.type = 'button';
    ask.textContent = 'Ask about this FoundUp';
    ask.setAttribute('data-reddog-fractal-ask', '');
    ask.addEventListener('click', () => {
      // An old button cannot use its previous binding after a host redraw.
      if (container.children[0] === group) onAsk(id);
    });
    group.appendChild(ask);
  }
  container.replaceChildren(group);
}

if (typeof module === 'object' && module.exports) {
  module.exports = { renderFractalFocus };
} else {
  globalThis.RedDogFractalFocus = Object.freeze({ renderFractalFocus });
}
