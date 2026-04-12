/**
 * HoloIndex External FoundUp Connector Bus
 * Implements the EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md payload specs.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const connectionStatus = document.getElementById('connectionStatus');
    const statusDot = connectionStatus.querySelector('.dot');
    const statusText = connectionStatus.querySelector('.text');
    
    // UI State Elements
    const placeholderState = document.getElementById('placeholderState');
    const loadingState = document.getElementById('loadingState');
    const resultsList = document.getElementById('resultsList');
    const resultTemplate = document.getElementById('resultTemplate');

    let currentAction = 'semantic_search';
    let isConnected = false;

    // Simulate establishing connection to shell
    setTimeout(() => {
        isConnected = true;
        statusDot.classList.replace('disconnected', 'connected');
        statusText.textContent = 'Connected to p.fMALL Shell';
    }, 500);

    // Event Listeners
    filterBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            filterBtns.forEach(b => b.classList.remove('active'));
            const target = e.currentTarget;
            target.classList.add('active');
            currentAction = target.dataset.action;
            
            // Adjust placeholder text based on action
            if(currentAction === 'wsp_lookup'){
                searchInput.placeholder = "Enter Protocol Number (e.g. 97)...";
            } else if (currentAction === 'health') {
                searchInput.placeholder = "Run health check (press enter)...";
                searchInput.value = "";
            } else {
                searchInput.placeholder = "Search the WSP and codebase memory...";
            }
        });
    });

    const executeSearch = () => {
        const query = searchInput.value.trim();
        
        // Prepare the payload according to Section 2 of bridge contract
        const payload = {
            action: currentAction,
            ...(currentAction === 'semantic_search' && { query: query, limit: 5 }),
            ...(currentAction === 'wsp_lookup' && { protocol_number: query })
        };

        const agentRequest = {
            type: "agent_request",
            route: "openclaw_search",
            payload: payload
        };

        // UI State transition
        placeholderState.classList.add('hidden');
        resultsList.classList.add('hidden');
        loadingState.classList.remove('hidden');
        resultsList.innerHTML = '';

        // Transmit via parent postMessage
        // Note: For local iframe dev, targetOrigin is '*' but should be restricted in prod.
        if (window.parent && window.parent !== window) {
            window.parent.postMessage(agentRequest, '*');
            console.log("[HoloIndex UI] Sent agent_request to shell:", agentRequest);
        } else {
            console.warn("[HoloIndex UI] Not running inside an iframe. Simulating shell delay...");
            // Simulate the interceptor backend response if running standalone
            setTimeout(() => simulateBackendResponse(agentRequest), 1500);
        }
    };

    searchBtn.addEventListener('click', executeSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') executeSearch();
    });

    // Listen for agent_response messages from the pfMALL shell interceptor
    window.addEventListener('message', (event) => {
        const data = event.data;
        if (data && data.type === 'agent_response') {
            console.log("[HoloIndex UI] Received agent_response from shell:", data);
            handleResponse(data);
        }
    });

    // Handle incoming response payload
    function handleResponse(response) {
        loadingState.classList.add('hidden');
        
        if (response.status === 'success' && response.data) {
            resultsList.classList.remove('hidden');
            
            // Render results
            if (response.data.results && response.data.results.length > 0) {
                response.data.results.forEach(res => {
                    const clone = resultTemplate.content.cloneNode(true);
                    
                    clone.querySelector('.result-path').textContent = res.path || 'System Response';
                    
                    // Render score if available
                    const scoreElem = clone.querySelector('.result-score');
                    if (res.relevance) {
                         scoreElem.textContent = `${(res.relevance * 100).toFixed(1)}% Match`;
                    } else if (response.data.quantum_coherence) {
                         scoreElem.textContent = `Coherence: ${(response.data.quantum_coherence * 100).toFixed(1)}%`;
                    } else {
                         scoreElem.style.display = 'none';
                    }

                    clone.querySelector('.result-content').textContent = res.content || JSON.stringify(res, null, 2);
                    
                    resultsList.appendChild(clone);
                });
            } else {
                // Empty state
                const msg = document.createElement('div');
                msg.className = 'placeholder-state';
                msg.style.position = 'relative';
                msg.style.transform = 'none';
                msg.style.left = 'auto';
                msg.style.top = 'auto';
                msg.innerHTML = '<p>No memory records found for query.</p>';
                resultsList.appendChild(msg);
            }
        } else {
            // Error state
            resultsList.classList.remove('hidden');
            resultsList.innerHTML = `<div style="color: #ef4444; padding: 1rem; background: rgba(239,68,68,0.1); border-radius: 8px;">Error fulfilling request: ${response.error || 'Unknown error'}</div>`;
        }
    }

    // Mock response for standalone frontend testing (when not in shell iframe)
    function simulateBackendResponse(request) {
        let mockResults = [];
        const action = request.payload.action;
        const query = request.payload.query || request.payload.protocol_number || '';

        if (action === 'wsp_lookup') {
            mockResults.push({
                content: `Protocol WSP ${query}\n\nStrict verification mandates. 100% test coverage target. Do not invoke external tools without explicit directive mapping.`,
                path: `modules/wsp/docs/WSP_${query}.md`
            });
        } else if (action === 'health') {
            mockResults.push({
                content: `{"status": "healthy", "memory_usage": "1.2MB", "latency": "12ms"}`,
                path: `/f/holoindex/status`
            });
        } else {
            mockResults.push({
                content: `def verify_token_auth(token):\n    """Validates the ${query} string across the execution boundary."""\n    return False # TODO`,
                path: `holo_index/src/auth.py`,
                relevance: 0.94
            });
            mockResults.push({
                content: `# ${query} Implementation\nRequires the openclaw_search permission scope to access this fragment.`,
                path: `docs/search_architecture.md`,
                relevance: 0.81
            });
        }

        handleResponse({
            type: "agent_response",
            status: "success",
            stub: true, // Marker from phase 1 spec
            data: {
                results: mockResults,
                quantum_coherence: 0.87
            }
        });
    }
});
