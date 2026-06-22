const vscode = require('vscode');
const cp = require('child_process');
const path = require('path');
const fs = require('fs');

const EXTENSION_VERSION = '0.3.13';
const DEFAULT_FUSION_WORKER = {
  title: 'FoundUps Fusion',
  lead: 'deepseek/deepseek-v3.2',
  panel: ['z-ai/glm-5.2', 'moonshotai/kimi-k2.7-code']
};

const REDDOG_ARCHITECT_SYSTEM_PROMPT = [
  'You are 0102 operating as the RedDog Architect advisory surface for FoundUps.',
  'Operate in WSP_00: self=0102, role=architect unless a narrower role is supplied, origin=external_principal.',
  'Apply WSP_97: retrieve/evaluate supplied evidence before stating facts; separate OBSERVED, INFERRED, and NEEDS_VERIFICATION; never claim direct repo access beyond the bounded context packet.',
  'Apply WSP_15 at the bottom of every substantive answer: score each recommended next action with Complexity, Importance, Deferability, Impact, MPS total, and P0-P4 priority.',
  'For every finding, include an actionable proposed fix or a reason the fix must be deferred.',
  'If HoloIndex recall is weak, offline, stale, or returns zero WSP hits, treat that as a retrieval-quality finding and propose the next retrieval/index repair step instead of overclaiming.',
  'If a public/, pfMALL, RedDog, WRE, OpenClaw, Hermes, Kanban, CABR, or FoundUp onboarding boundary appears, classify whether it is implemented, specified-not-implemented, inferred, or unknown.',
  'Do not edit files, run commands, merge PRs, create repos, grant authority, route payouts, or claim CABR/verification truth. Advisory only.',
  'Output format: Decision, Findings, Evidence, Proposed fixes, Uncertainties, WSP_97 Truth Labels, WSP_15 Priority, Next safest step.'
].join(' ');

const REDDOG_REQUIRED_OUTPUT_SECTIONS = [
  'Decision',
  'Findings',
  'Evidence',
  'Proposed fixes',
  'Uncertainties',
  'WSP_97 Truth Labels',
  'WSP_15 Priority',
  'Next safest step'
];

const ULTRA_TASK_PATTERNS = [
  /\bauth(entication|orize|orization)?\b/i,
  /\bsecurity\b/i,
  /\bsecret(s)?\b/i,
  /\bcredential(s)?\b/i,
  /\boauth\b/i,
  /\blive runtime\b/i,
  /\bruntime control\b/i,
  /\bpublic\/\b/i,
  /\bpf\s?mall\b/i,
  /\bwre\b/i,
  /\bopenclaw\b/i,
  /\bhermes\b/i,
  /\bkanban\b/i,
  /\bcabr\b/i,
  /\bmerge authority\b/i,
  /\bmerge pr\b/i,
  /\brepo creation\b/i,
  /\bcreate repo\b/i,
  /\bdeploy(ment)?\b/i,
  /\bfirebase hosting\b/i
];

const HIGH_TASK_PATTERNS = [
  /\barchitecture\b/i,
  /\bwsp[_\s-]?\d+/i,
  /\bholoindex\b/i,
  /\bextension routing\b/i,
  /\bfoundup intake\b/i,
  /\breddog\b/i,
  /\borchestrat/i,
  /\bprotocol\b/i,
  /\bgate report\b/i,
  /\brepair slice\b/i,
  /\bmodlog\b/i,
  /\binterface\.md\b/i
];

const REGULAR_TASK_PATTERNS = [
  /\bsmoke test\b/i,
  /\breply with exactly\b/i,
  /\bsimple explain\b/i,
  /\bui polish\b/i,
  /\bregular mode works\b/i
];

function classifyTaskForRedDog(prompt, contextMode, workerType) {
  const text = String(prompt || '');
  const worker = cleanWorkerType(workerType);
  const mode = cleanContextMode(contextMode);
  const haystack = text + ' ' + mode + ' ' + worker;
  let tier = 'HIGH';
  let reasons = [];

  if (ULTRA_TASK_PATTERNS.some((pattern) => pattern.test(haystack))) {
    tier = 'ULTRA';
    reasons.push('ultra_keyword_match');
  } else if (REGULAR_TASK_PATTERNS.some((pattern) => pattern.test(haystack)) && worker === 'smoke_tester') {
    tier = 'REGULAR';
    reasons.push('regular_smoke_prompt');
  } else if (HIGH_TASK_PATTERNS.some((pattern) => pattern.test(haystack))) {
    tier = 'HIGH';
    reasons.push('high_keyword_match');
  } else if (worker === 'smoke_tester') {
    tier = 'REGULAR';
    reasons.push('smoke_tester_default');
  } else {
    tier = 'HIGH';
    reasons.push('uncertain_default_high');
  }

  const preferManualPanel = tier !== 'REGULAR' || worker !== 'smoke_tester';
  return {
    tier,
    reasons,
    worker,
    contextMode: mode,
    preferManualPanel,
    prefersAuditablePanel: preferManualPanel && worker !== 'smoke_tester'
  };
}

function resolveAutoEffort(classification, selectedEffort) {
  const effort = cleanEffort(selectedEffort);
  if (effort !== 'auto') {
    return effort;
  }
  const tier = classification && classification.tier ? classification.tier : 'HIGH';
  if (tier === 'ULTRA') {
    return 'ultra';
  }
  if (tier === 'REGULAR') {
    return 'regular';
  }
  return 'high';
}

function resolveModelMode(classification, selectedMode, workerType) {
  const mode = cleanMode(selectedMode);
  const worker = cleanWorkerType(workerType);
  if (worker === 'smoke_tester') {
    return mode;
  }
  if (mode === 'openrouter_fusion_alias') {
    return mode;
  }
  if (classification && classification.prefersAuditablePanel) {
    return 'foundups_fusion';
  }
  return mode;
}

function validateRedDogOutput(markdown) {
  const text = String(markdown || '');
  const missingSections = [];
  for (const section of REDDOG_REQUIRED_OUTPUT_SECTIONS) {
    const pattern = new RegExp('(^|\\n)\\s*(#{1,3}\\s*)?' + section.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'i');
    if (!pattern.test(text)) {
      missingSections.push(section);
    }
  }
  return {
    valid: missingSections.length === 0,
    missingSections
  };
}

function buildRepairPrompt(originalPrompt, badOutput, missingSections) {
  const sections = Array.isArray(missingSections) ? missingSections : [];
  return [
    'Repair pass: preserve the existing answer content and add only the missing required schema sections.',
    'Do not invent evidence, repo paths, test results, or authority.',
    'Label claims with WSP_97 truth labels where applicable.',
    'Missing sections: ' + (sections.length ? sections.join(', ') : '(none listed)'),
    '',
    'Original task:',
    String(originalPrompt || '').slice(0, 4000),
    '',
    'Draft answer to repair:',
    String(badOutput || '').slice(0, 12000)
  ].join('\n');
}

function isSubstantiveRedDogWorker(workerType) {
  const worker = cleanWorkerType(workerType);
  return worker === 'reddog_architect' || worker === 'wsp_gate_critic' || worker === 'repair_planner';
}

function attachOrchestratorMetadata(reviewPacket, classification, resolvedEffort, resolvedMode, validationState) {
  const base = reviewPacket && typeof reviewPacket === 'object' ? reviewPacket : {};
  return Object.assign({}, base, {
    task_classification: classification,
    resolved_effort: resolvedEffort,
    resolved_mode: resolvedMode,
    output_validation: validationState
  });
}

const WORKER_TYPES = {
  reddog_architect: {
    label: 'RedDog Architect',
    prompt: REDDOG_ARCHITECT_SYSTEM_PROMPT
  },
  wsp_gate_critic: {
    label: 'WSP Gate Critic',
    prompt: REDDOG_ARCHITECT_SYSTEM_PROMPT + ' Emphasize gate failure modes, WSP_97 truth boundaries, missing evidence, non-vacuity, and exact return-to-author criteria.'
  },
  repair_planner: {
    label: 'Repair Planner',
    prompt: REDDOG_ARCHITECT_SYSTEM_PROMPT + ' Emphasize smallest valid repair slices, test contracts, ModLog/TestModLog memory, and PR-ready work breakdowns.'
  },
  smoke_tester: {
    label: 'Smoke Test',
    prompt: REDDOG_ARCHITECT_SYSTEM_PROMPT + ' Emphasize bounded smoke tests, expected output, failure reasons, and no destructive/live actions unless explicitly authorized.'
  }
};

const EFFORT_GUIDANCE = {
  auto: 'Effort: AUTO. Classify risk from supplied context. Use high rigor for WSP/security/architecture, normal rigor for simple smoke checks.',
  regular: 'Effort: REGULAR. Keep concise, verify core claims, avoid broad architecture unless needed.',
  high: 'Effort: HIGH. Run micro/macro reasoning over supplied context, compare alternatives, and include specific tests.',
  ultra: 'Effort: ULTRA. Treat as adversarial architecture review: include competing interpretations, non-vacuity checks, and failure-mode analysis.'
};

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('foundupsFusion.open', () => openFusionEditor(context))
  );
}

function openFusionEditor(context) {
  const worker = fusionWorkerFromConfig();
  const panel = vscode.window.createWebviewPanel(
    'foundupsFusionWorker',
    worker.title,
    vscode.ViewColumn.Beside,
    {
      enableScripts: true,
      retainContextWhenHidden: true,
      localResourceRoots: [context.extensionUri]
    }
  );
  const logoUri = panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'icon.png'));
  wireFusionWebview(context, panel.webview, worker, { history: [], lastReviewPacket: null });
  panel.webview.html = renderHtml(worker, 'editor', logoUri.toString());
}

function workspaceRoot() {
  const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
  return folder ? folder.uri.fsPath : process.cwd();
}

function fusionWorkerFromConfig() {
  const config = vscode.workspace.getConfiguration('foundupsFusion');
  const lead = cleanModel(config.get('leadModel'), DEFAULT_FUSION_WORKER.lead);
  const configuredPanel = config.get('panelModels');
  const panel = Array.isArray(configuredPanel)
    ? configuredPanel.map((item) => cleanModel(item, '')).filter(Boolean).slice(0, 4)
    : DEFAULT_FUSION_WORKER.panel;
  return {
    title: DEFAULT_FUSION_WORKER.title,
    lead,
    panel: panel.length ? panel : DEFAULT_FUSION_WORKER.panel
  };
}

function cleanModel(value, fallback) {
  return typeof value === 'string' && value.trim() && value.length <= 120 ? value.trim() : fallback;
}

function wireFusionWebview(context, webview, worker, state) {
  webview.onDidReceiveMessage(async (message) => {
    if (!message || typeof message !== 'object') {
      return;
    }
    if (message.command === 'copyReview') {
      if (state.lastReviewPacket) {
        await vscode.env.clipboard.writeText(JSON.stringify(state.lastReviewPacket, null, 2));
        webview.postMessage({ command: 'status', text: 'Copied redacted review packet for 0102.' });
      } else {
        webview.postMessage({ command: 'status', text: 'No review packet available yet.' });
      }
      return;
    }
    if (message.command === 'copyMarkdown' && typeof message.text === 'string') {
      await vscode.env.clipboard.writeText(message.text);
      webview.postMessage({ command: 'status', text: 'Copied assistant markdown.' });
      return;
    }
    if (message.command !== 'ask' || typeof message.text !== 'string') {
      return;
    }

    const contextMode = cleanContextMode(message.contextMode);
    const workerType = cleanWorkerType(message.workerType);
    const selectedEffort = cleanEffort(message.effort);
    const selectedMode = cleanMode(message.mode);
    const classification = classifyTaskForRedDog(message.text, contextMode, workerType);
    const effort = resolveAutoEffort(classification, selectedEffort);
    const mode = resolveModelMode(classification, selectedMode, workerType);
    const contextPacket = buildBoundedRepoContext(contextMode, message.text);
    const systemPrompt = buildSystemPrompt(workerType, effort, contextPacket.quality);

    webview.postMessage({
      command: 'status',
      text: 'Orchestrator: effort=' + effort + ' mode=' + mode + ' tier=' + classification.tier + ' (' + classification.reasons.join(', ') + ')'
    });
    webview.postMessage({ command: 'status', text: 'Bridge started. Redaction gate runs before any OpenRouter API call.' });
    if (contextPacket.summary) {
      webview.postMessage({ command: 'status', text: contextPacket.summary });
    }
    let result = await callFusion(context, worker, message.text, contextPacket.text, systemPrompt, state.history, mode, (text) => {
      webview.postMessage({ command: 'status', text });
    });
    if (result.ok && isSubstantiveRedDogWorker(workerType)) {
      const validation = validateRedDogOutput(result.content || '');
      let validationState = {
        validated: validation.valid,
        missing_sections: validation.missingSections,
        repair_attempted: false,
        repair_ok: false
      };
      if (!validation.valid && validation.missingSections.length) {
        validationState.repair_attempted = true;
        webview.postMessage({
          command: 'status',
          text: 'Output schema incomplete. Missing: ' + validation.missingSections.join(', ') + '. Running one repair pass...'
        });
        const repairPrompt = buildRepairPrompt(message.text, result.content, validation.missingSections);
        const repairResult = await callFusion(
          context,
          worker,
          repairPrompt,
          contextPacket.text,
          systemPrompt + '\n\nRepair pass: add missing schema sections only. Do not invent evidence.',
          state.history,
          mode,
          (text) => {
            webview.postMessage({ command: 'status', text });
          }
        );
        if (repairResult.ok) {
          const repairValidation = validateRedDogOutput(repairResult.content || '');
          validationState.repair_ok = repairValidation.valid;
          validationState.missing_sections_after_repair = repairValidation.missingSections;
          if (repairValidation.valid) {
            result = repairResult;
            validationState.validated = true;
            validationState.missing_sections = [];
          } else {
            result.content = String(result.content || '') + '\n\n---\n\n**Validator warning:** Output still missing sections after repair: '
              + repairValidation.missingSections.join(', ');
          }
        } else {
          result.content = String(result.content || '') + '\n\n---\n\n**Validator warning:** Repair pass failed ('
            + (repairResult.reason || 'unknown') + '). Missing sections: ' + validation.missingSections.join(', ');
        }
      }
      if (result.review_packet) {
        result.review_packet = attachOrchestratorMetadata(
          result.review_packet,
          classification,
          effort,
          mode,
          validationState
        );
      }
    } else if (result.ok && result.review_packet) {
      result.review_packet = attachOrchestratorMetadata(
        result.review_packet,
        classification,
        effort,
        mode,
        { validated: false, skipped: true, reason: 'non_substantive_worker' }
      );
    }
    if (result.ok && Array.isArray(result.history)) {
      state.history = result.history;
    }
    if (result.ok && result.review_packet) {
      state.lastReviewPacket = result.review_packet;
    }
    webview.postMessage({ command: 'result', result });
  });
}

function callFusion(context, worker, prompt, boundedContext, systemPrompt, history, mode, onProgress) {
  return new Promise((resolve) => {
    const root = workspaceRoot();
    const script = path.join(root, 'scripts', 'advisory_model_once.py');
    const config = vscode.workspace.getConfiguration('foundupsFusion');
    const pythonPath = config.get('pythonPath') || 'python';
    onProgress('Mode: ' + mode);
    onProgress('Bridge process starting: ' + pythonPath);
    onProgress('Workspace root: ' + root);
    onProgress('Bridge script: ' + script);
    onProgress('OpenRouter key visible to Cursor process: ' + (process.env.OPENROUTER_API_KEY ? 'yes' : 'no'));
    const child = cp.spawn(pythonPath, [script], {
      cwd: root,
      env: process.env,
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';
    const payload = {
      mode,
      prompt,
      context: boundedContext,
      system: systemPrompt,
      model: mode === 'openrouter_single' ? worker.lead : undefined,
      history,
      lead_model: worker.lead,
      panel_models: worker.panel,
      max_tokens: 2200,
      temperature: 0.2,
      timeout: mode === 'foundups_fusion' ? 120 : 90
    };

    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => {
      const text = chunk.toString();
      stderr += text;
      for (const line of text.split(/\r?\n/)) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          if (event && event.event === 'progress' && event.text) {
            onProgress(event.text);
          }
        } catch (err) {
          // stderr can contain non-JSON diagnostics from Python dependencies.
        }
      }
    });
    child.on('error', (err) => {
      resolve({ ok: false, reason: 'spawn_error', detail: err.message });
    });
    child.on('close', () => {
      try {
        const parsed = JSON.parse(stdout || '{}');
        resolve(parsed);
      } catch (err) {
        resolve({ ok: false, reason: 'invalid_bridge_output', detail: stderr.slice(0, 500) });
      }
    });
    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  });
}

function cleanContextMode(value) {
  if (value === 'wsp_holo' || value === 'wsp_holo_git' || value === 'active_editor' || value === 'git_diff' || value === 'none') {
    return value;
  }
  return 'wsp_holo';
}

function cleanWorkerType(value) {
  return Object.prototype.hasOwnProperty.call(WORKER_TYPES, value) ? value : 'reddog_architect';
}

function cleanEffort(value) {
  return Object.prototype.hasOwnProperty.call(EFFORT_GUIDANCE, value) ? value : 'auto';
}

function buildSystemPrompt(workerType, effort, retrievalQuality) {
  const worker = WORKER_TYPES[cleanWorkerType(workerType)];
  const effortText = EFFORT_GUIDANCE[cleanEffort(effort)];
  const qualityText = retrievalQuality ? 'Retrieval quality note: ' + retrievalQuality : '';
  return [worker.prompt, effortText, qualityText, 'Always end with a WSP_15 Priority block and one Next safest step.'].filter(Boolean).join('\n\n');
}

function buildBoundedRepoContext(mode, taskText) {
  const root = workspaceRoot();
  const sections = [
    '## WSP_OPERATING_CONTRACT',
    '- You are an advisory 0102 worker surface. 012 remains the external principal and final decision holder.',
    '- Operate in WSP_00: HoloIndex-first recall, anti-vibecoding, verify before recommending action.',
    '- Apply WSP_97: label each factual claim as OBSERVED, INFERRED, or NEEDS_VERIFICATION.',
    '- Apply WSP_15: every recommended fix must include C/I/D/Impact/MPS/Priority.',
    '- Every finding must include a proposed fix or an explicit defer/block reason.',
    '- No shell, repo modification, credential, browser, deploy, or runtime control. Return recommendations only.',
    '',
    '## BOUNDED_REPO_CONTEXT',
    'The model cannot read the filesystem. The following context was gathered by the local Cursor extension and redaction-gated before egress.',
    'Context mode: ' + mode,
    'Workspace root: ' + root
  ];
  let quality = 'No HoloIndex requested for this context mode.';
  if (mode === 'none') {
    const text = sections.join('\n');
    return { text, summary: 'Repo context: WSP operating contract only.', quality };
  }
  if (mode === 'wsp_holo' || mode === 'wsp_holo_git') {
    const holo = holoIndexOutput(root, taskText || '', 18000);
    quality = holo.quality;
    sections.push('### HoloIndex recall (WSP_00 bundle-json first; offline fallback only if needed)\n```text\n' + (holo.output || '(no HoloIndex output)') + '\n```');
  }
  const active = activeEditorContext(root);
  if (active) {
    sections.push(active);
  }
  if (mode === 'git_diff' || mode === 'wsp_holo_git') {
    const status = gitOutput(root, ['status', '--short'], 8000);
    const stat = gitOutput(root, ['diff', '--stat'], 8000);
    const diff = gitOutput(root, ['diff', '--', '.'], 24000);
    sections.push('### git status --short\n```text\n' + (status || '(clean)') + '\n```');
    sections.push('### git diff --stat\n```text\n' + (stat || '(no diff)') + '\n```');
    sections.push('### git diff -- . (bounded)\n```diff\n' + (diff || '(no diff)') + '\n```');
  }
  const text = sections.join('\n\n').slice(0, 42000);
  return { text, summary: 'Repo context attached: ' + mode + ' (' + text.length + ' chars). ' + quality, quality };
}

function activeEditorContext(root) {
  const editor = vscode.window.activeTextEditor || (vscode.window.visibleTextEditors && vscode.window.visibleTextEditors[0]);
  if (!editor || !editor.document) {
    return '';
  }
  const doc = editor.document;
  if (!doc.uri || doc.uri.scheme !== 'file') {
    return '';
  }
  const filePath = doc.uri.fsPath;
  const rel = relativePath(root, filePath);
  const selected = editor.selection && !editor.selection.isEmpty;
  const raw = selected ? doc.getText(editor.selection) : doc.getText();
  const max = selected ? 16000 : 24000;
  const clipped = raw.length > max ? raw.slice(0, max) + '\n...[TRUNCATED ' + (raw.length - max) + ' chars]' : raw;
  return '### active editor ' + (selected ? 'selection' : 'file') + ': ' + rel + '\n```' + (doc.languageId || 'text') + '\n' + clipped + '\n```';
}

function relativePath(root, filePath) {
  try {
    const rel = path.relative(root, filePath);
    if (rel && !rel.startsWith('..') && !path.isAbsolute(rel)) {
      return rel;
    }
  } catch (err) {
    // fall through to basename
  }
  return path.basename(filePath);
}

function moduleHintFromActive(root) {
  const editor = vscode.window.activeTextEditor || (vscode.window.visibleTextEditors && vscode.window.visibleTextEditors[0]);
  if (!editor || !editor.document || !editor.document.uri || editor.document.uri.scheme !== 'file') {
    return 'extensions/foundups_advisory_workers';
  }
  const rel = relativePath(root, editor.document.uri.fsPath).replace(/\\/g, '/');
  if (!rel || rel.startsWith('..')) {
    return 'extensions/foundups_advisory_workers';
  }
  const parts = rel.split('/');
  if (parts[0] === 'modules' && parts.length >= 3) {
    return parts.slice(0, 3).join('/');
  }
  if (parts[0] === 'extensions' && parts.length >= 2) {
    return parts.slice(0, 2).join('/');
  }
  return parts[0];
}

function holoIndexOutput(root, taskText, maxChars) {
  const query = String(taskText || '').replace(/\s+/g, ' ').trim().slice(0, 500) || 'FoundUps RedDog WSP_00 WSP_97 WSP_15 current task';
  const moduleHint = moduleHintFromActive(root);
  try {
    const env = Object.assign({}, process.env, { HOLO_SKIP_MODEL: '1' });
    const output = cp.execFileSync('python', ['-B', 'holo_index.py', '--bundle-json', '--search', query, '--bundle-module-hint', moduleHint, '--limit', '5', '--quiet-root-alerts'], {
      cwd: root,
      env,
      encoding: 'utf8',
      timeout: 25000,
      maxBuffer: Math.max(maxChars * 4, 65536),
      windowsHide: true
    });
    return { output: String(output || '').slice(0, maxChars), quality: summarizeHoloBundle(output) };
  } catch (bundleErr) {
    try {
      const output = cp.execFileSync('python', ['-B', 'holo_index.py', '--offline', '--search', query, '--limit', '5'], {
        cwd: root,
        encoding: 'utf8',
        timeout: 20000,
        maxBuffer: Math.max(maxChars * 4, 65536),
        windowsHide: true
      });
      return {
        output: String(output || '').slice(0, maxChars),
        quality: 'HoloIndex bundle-json failed; offline lexical fallback used. Treat protocol coverage as NEEDS_VERIFICATION and propose re-index/bundle repair if WSP hits are missing.'
      };
    } catch (offlineErr) {
      return {
        output: '[HoloIndex unavailable: ' + (offlineErr && offlineErr.message ? offlineErr.message.slice(0, 180) : 'unknown') + ']',
        quality: 'HoloIndex unavailable. Use supplied editor/git evidence only; propose HoloIndex recovery as a fix when retrieval affects the decision.'
      };
    }
  }
}

function summarizeHoloBundle(output) {
  try {
    const data = JSON.parse(String(output || '{}'));
    const meta = data.task_retrieval && data.task_retrieval.metadata ? data.task_retrieval.metadata : {};
    const wspCount = Number(meta.wsp_count || 0);
    const codeCount = Number(meta.code_count || 0);
    const missing = data.structured_memory && Array.isArray(data.structured_memory.missing_required)
      ? data.structured_memory.missing_required
      : [];
    const parts = ['HoloIndex bundle-json ok', 'wsp=' + wspCount, 'code=' + codeCount];
    if (missing.length) {
      parts.push('missing_required=' + missing.join(','));
    }
    if (wspCount === 0) {
      parts.push('WSP hits are zero; propose retrieval/index repair before strong protocol claims.');
    }
    return parts.join('; ');
  } catch (err) {
    return 'HoloIndex bundle-json returned non-JSON output; treat recall as NEEDS_VERIFICATION.';
  }
}

function gitOutput(root, args, maxChars) {
  try {
    if (!fs.existsSync(path.join(root, '.git'))) {
      return '';
    }
    const output = cp.execFileSync('git', args, {
      cwd: root,
      encoding: 'utf8',
      timeout: 5000,
      maxBuffer: Math.max(maxChars * 4, 65536),
      windowsHide: true
    });
    return String(output || '').slice(0, maxChars);
  } catch (err) {
    return '[git context unavailable: ' + (err && err.message ? err.message.slice(0, 180) : 'unknown') + ']';
  }
}

function cleanMode(value) {
  if (value === 'openrouter_single' || value === 'openrouter_fusion_alias' || value === 'foundups_fusion') {
    return value;
  }
  return 'foundups_fusion';
}

function renderHtml(worker, surface, logoUri) {
  const escapedTitle = escapeHtml(worker.title);
  const escapedLead = escapeHtml(worker.lead);
  const escapedPanel = escapeHtml(worker.panel.join(' + '));
  const escapedSurface = escapeHtml(surface);
  const escapedLogoUri = escapeHtml(logoUri || '');
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapedTitle}</title>
  <style>
    :root { color-scheme: dark; }
    html, body { height: 100%; overflow: hidden; }
    body { margin: 0; font-family: var(--vscode-font-family); color: var(--vscode-foreground); background: var(--vscode-editor-background); }
    .wrap { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; height: 100vh; overflow: hidden; }
    header { padding: 8px 12px; border-bottom: 1px solid var(--vscode-panel-border); background: var(--vscode-editor-background); }
    .brand { display: flex; align-items: center; gap: 9px; margin-bottom: 3px; }
    .brand img { width: 30px; height: 30px; object-fit: contain; }
    h1 { margin: 0; font-size: 14px; font-weight: 600; }
    .meta { color: var(--vscode-descriptionForeground); font-size: 11px; line-height: 1.35; }
    #log { min-height: 0; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 10px; scroll-behavior: smooth; }
    .entry { border: 1px solid var(--vscode-panel-border); border-radius: 6px; padding: 8px; white-space: pre-wrap; line-height: 1.45; font-size: 12px; overflow-wrap: anywhere; }
    .entry .label { display: block; margin-bottom: 5px; color: var(--vscode-descriptionForeground); font-size: 10px; text-transform: uppercase; letter-spacing: 0; }
    .user { border-left: 3px solid var(--vscode-charts-blue); }
    .assistant { border-left: 3px solid var(--vscode-charts-green); }
    .status { border-left: 3px solid var(--vscode-descriptionForeground); color: var(--vscode-descriptionForeground); background: var(--vscode-sideBar-background); }
    .error { border-left: 3px solid var(--vscode-errorForeground); color: var(--vscode-errorForeground); }
    form { display: grid; grid-template-columns: 1fr; gap: 7px; padding: 10px; border-top: 1px solid var(--vscode-panel-border); background: var(--vscode-editor-background); z-index: 1; }
    .toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: var(--vscode-descriptionForeground); font-size: 11px; }
    select, button { color: var(--vscode-dropdown-foreground); background: var(--vscode-dropdown-background); border: 1px solid var(--vscode-dropdown-border); padding: 3px 6px; }
    button { cursor: pointer; }
    textarea { resize: none; min-height: 74px; max-height: 180px; padding: 8px; color: var(--vscode-input-foreground); background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border); font-family: var(--vscode-editor-font-family); }
    textarea:focus { outline: 1px solid var(--vscode-focusBorder); }
    .hint { color: var(--vscode-descriptionForeground); font-size: 11px; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand"><img src="${escapedLogoUri}" alt="RedDawg"><h1>${escapedTitle}</h1></div>
      <div class="meta">Build: ${EXTENSION_VERSION}<br>Surface: ${escapedSurface}<br>Lead: ${escapedLead}<br>Panel: ${escapedPanel}<br>Advisory only. Redaction-gated. No repo, shell, or merge authority.</div>
    </header>
    <main id="log" aria-label="FoundUps Fusion output scrollback">
      <div class="entry status"><span class="label">status</span>FoundUps Fusion extension ${EXTENSION_VERSION} loaded.</div>
      <div class="entry status"><span class="label">status</span>OPENROUTER_API_KEY must be set in the environment used to launch Cursor. Do not paste secrets.</div>
    </main>
    <form id="form">
      <div class="toolbar">
        <label for="workerType">Worker</label><select id="workerType"><option value="reddog_architect" selected>RedDog Architect</option><option value="wsp_gate_critic">WSP Gate Critic</option><option value="repair_planner">Repair Planner</option><option value="smoke_tester">Smoke Test</option></select>
        <label for="effort">Effort</label><select id="effort"><option value="auto" selected>Auto</option><option value="regular">Regular</option><option value="high">High</option><option value="ultra">Ultra</option></select>
        <label for="mode">Mode</label><select id="mode"><option value="foundups_fusion" selected>FoundUps manual lead + panel (RedDog WSP default)</option><option value="openrouter_fusion_alias">OpenRouter Fusion alias (fast/black-box)</option><option value="openrouter_single">Regular OpenRouter</option></select>
        <label for="contextMode">Context</label><select id="contextMode"><option value="wsp_holo" selected>WSP + HoloIndex + active editor</option><option value="wsp_holo_git">WSP + HoloIndex + git diff</option><option value="git_diff">Active editor + git diff</option><option value="active_editor">Active editor only</option><option value="none">WSP only</option></select>
        <label for="testPrompt">Tests</label><select id="testPrompt"><option value="">Select test...</option><option value="regular">Regular smoke</option><option value="fusion">Fusion smoke</option><option value="wsp97">WSP_97 repo review</option><option value="reddog">RedDog architect review</option></select>
        <button id="copyMd" type="button">Copy MD</button>
      </div>
      <textarea id="prompt" placeholder="Ask the FoundUps Fusion worker..."></textarea>
      <div class="hint">Enter sends. Shift+Enter adds a new line. Ctrl+Shift+C copies the redacted review packet.</div>
    </form>
  </div>
  <script>
    const vscode = acquireVsCodeApi();
    const form = document.getElementById('form');
    const prompt = document.getElementById('prompt');
    const mode = document.getElementById('mode');
    const contextMode = document.getElementById('contextMode');
    const workerType = document.getElementById('workerType');
    const effort = document.getElementById('effort');
    const testPrompt = document.getElementById('testPrompt');
    const copyMd = document.getElementById('copyMd');
    let lastAssistantMarkdown = '';
    const log = document.getElementById('log');
    let running = false;
    let startedAt = 0;

    function add(cls, text, label) {
      const el = document.createElement('div');
      el.className = 'entry ' + cls;
      const span = document.createElement('span');
      span.className = 'label';
      span.textContent = label || cls;
      el.appendChild(span);
      el.appendChild(document.createTextNode(text));
      log.appendChild(el);
      log.scrollTop = log.scrollHeight;
    }

    function elapsed() {
      return startedAt ? ' [' + Math.round((Date.now() - startedAt) / 1000) + 's]' : '';
    }

    function addStatus(text) {
      add('status', text + elapsed(), 'status');
    }

    function setRunning(value) {
      running = value;
      prompt.disabled = value;
      mode.disabled = value;
      contextMode.disabled = value;
      workerType.disabled = value;
      effort.disabled = value;
      testPrompt.disabled = value;
      copyMd.disabled = value;
      if (value) {
        startedAt = Date.now();
      }
    }

    testPrompt.addEventListener('change', () => {
      const value = testPrompt.value;
      if (value === 'regular') { mode.value = 'openrouter_single'; contextMode.value = 'none'; workerType.value = 'smoke_tester'; effort.value = 'regular'; prompt.value = 'Reply with exactly: regular mode works'; }
      if (value === 'fusion') { mode.value = 'openrouter_fusion_alias'; contextMode.value = 'none'; workerType.value = 'smoke_tester'; effort.value = 'regular'; prompt.value = 'Fusion smoke test. Reply with one consensus, one contradiction, and one blind spot. Keep it under 80 words.'; }
      if (value === 'wsp97') { mode.value = 'foundups_fusion'; contextMode.value = 'wsp_holo'; workerType.value = 'wsp_gate_critic'; effort.value = 'high'; prompt.value = 'Apply WSP_00, WSP_97, and WSP_15 to the supplied context. Provide findings, evidence, proposed fixes, uncertainties, WSP_15 priority, and next safest step.'; }
      if (value === 'reddog') { mode.value = 'foundups_fusion'; contextMode.value = 'wsp_holo_git'; workerType.value = 'reddog_architect'; effort.value = 'ultra'; prompt.value = 'Operate as RedDog Architect. Review the supplied repo context as a FoundUps intake/orchestration surface. For each issue, propose the WSP-compliant fix path and end with WSP_15 priority.'; }
      testPrompt.value = '';
      prompt.focus();
    });

    copyMd.addEventListener('click', () => {
      if (!lastAssistantMarkdown) { addStatus('No assistant markdown available to copy.'); return; }
      vscode.postMessage({ command: 'copyMarkdown', text: lastAssistantMarkdown });
    });

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      sendPrompt();
    });

    prompt.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendPrompt();
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'c') {
        event.preventDefault();
        vscode.postMessage({ command: 'copyReview' });
      }
    });

    function sendPrompt() {
      const text = prompt.value.trim();
      if (!text) return;
      if (running) {
        addStatus('A request is already running. Wait for the final response.');
        return;
      }
      setRunning(true);
      addStatus('Request sent. Waiting for bridge...');
      add('user', text, '012 prompt');
      prompt.value = '';
      vscode.postMessage({ command: 'ask', text, mode: mode.value, contextMode: contextMode.value, workerType: workerType.value, effort: effort.value });
    }

    window.addEventListener('message', (event) => {
      const msg = event.data;
      if (!msg) return;
      if (msg.command === 'status') addStatus(msg.text);
      if (msg.command === 'result') {
        setRunning(false);
        if (msg.result && msg.result.ok) {
          addStatus('Complete: ' + (msg.result.mode || msg.result.model || 'ok'));
          lastAssistantMarkdown = msg.result.content || '';
          add('assistant', lastAssistantMarkdown, '0102 output');
        } else {
          const failure = failureText(msg.result);
          addStatus('Stopped: ' + failure);
          add('error', 'Blocked/failed: ' + failure, 'error');
        }
        prompt.focus();
      }
    });
  </script>
</body>
</html>`;
}

function failureText(result) {
  if (!result) {
    return 'unknown';
  }
  const parts = [result.reason || 'unknown'];
  if (result.status) {
    parts.push('status=' + result.status);
  }
  if (result.lead_model) {
    parts.push('lead=' + result.lead_model);
  }
  if (result.detail && result.detail !== result.reason) {
    parts.push(result.detail);
  }
  if (result.redaction_reason) {
    parts.push('redaction=' + result.redaction_reason);
  }
  return parts.join(' | ');
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
  classifyTaskForRedDog,
  resolveAutoEffort,
  resolveModelMode,
  validateRedDogOutput,
  buildRepairPrompt,
  REDDOG_REQUIRED_OUTPUT_SECTIONS
};
