document.addEventListener('DOMContentLoaded', () => {
  const queryInput = document.getElementById('queryInput');
  const searchBtn = document.getElementById('searchBtn');
  const resultsPanel = document.getElementById('resultsPanel');

  searchBtn.addEventListener('click', () => {
    const query = queryInput.value.trim();
    if (!query) return;

    resultsPanel.textContent = 'Seeking...';

    // Simulate sending a postMessage to the parent shell
    const payloadObj = {
      type: 'agent_request',
      route: 'openclaw_search',
      payload: {
        action: 'semantic_search',
        query: query
      }
    };

    if (window.parent && window.parent !== window) {
      window.parent.postMessage(payloadObj, '*');
    } else {
      resultsPanel.textContent = 'Error: Not embedded in p.fMALL shell.';
    }
  });

  window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'agent_response' && event.data.service === 'holoindex') {
      resultsPanel.textContent = JSON.stringify(event.data.payload, null, 2);
    }
  });
});
