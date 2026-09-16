const { useState, useEffect, useRef } = React;

/* ---------- constants ---------- */
const DEFAULTS = {
  catalog_name: 'humana_payer', schema_name: 'integration_pattern',
  source_volume: 'source_files', file_format: 'csv', file_pattern: '*',
  target_schema: 'integration_pattern', target_table: 'member_eligibility_bronze',
  artifacts_volume: 'integration_artifacts',
  business_domain: 'Healthcare - Medicare Advantage',
  target_description: 'Bronze layer member eligibility data ingested from source volume (Medicare Advantage members)',
};

const ICON_MAP = { config: '\u2699\uFE0F', notebook: '\uD83D\uDCD3', test: '\uD83E\uDDEA', data: '\uD83D\uDCCA', doc: '\uD83D\uDCC4', vol: '\uD83D\uDDC4\uFE0F' };
function artifactIcon(a) {
  if (a.includes('notebook')) return ICON_MAP.notebook;
  if (a.includes('test')) return ICON_MAP.test;
  if (a.includes('sample') || a.includes('csv')) return ICON_MAP.data;
  if (a.includes('config')) return ICON_MAP.config;
  if (a.includes('volume')) return ICON_MAP.vol;
  return ICON_MAP.doc;
}

/* ---------- Header ---------- */
function Header() {
  return React.createElement('div', { className: 'app-header' },
    React.createElement('h1', null, '\u26A1 Integration Pattern Accelerator'),
    React.createElement('p', null, 'Generate complete implementation packages for Databricks ingestion pipelines')
  );
}

/* ---------- Landing ---------- */
function Landing({ patterns, onSelect }) {
  const entries = Object.values(patterns);
  return React.createElement('div', { className: 'container' },
    React.createElement('h2', { style: { fontSize: '1.1rem', color: '#475569' } }, 'Select an integration pattern to get started'),
    React.createElement('div', { className: 'cards' },
      entries.map(p => React.createElement('div', {
        key: p.id, className: 'card', onClick: () => onSelect(p)
      },
        React.createElement('div', { className: 'card-icon' }, p.icon),
        React.createElement('h3', null, p.name),
        React.createElement('p', { className: 'desc' }, p.short_description),
        React.createElement('ul', { className: 'details' },
          p.details.map((d, i) => React.createElement('li', { key: i }, d))
        ),
        React.createElement('div', { className: 'meta', style: { marginTop: 14 } },
          React.createElement('span', null, '\uD83D\uDCE5 ', p.source_system),
          React.createElement('span', null, '\u2192 ', p.target_layer)
        ),
        React.createElement('span', { className: 'arrow' }, '\u2192')
      ))
    )
  );
}

/* ---------- ConfigForm ---------- */
function ConfigForm({ pattern, onBack, onGenerate }) {
  const [form, setForm] = useState({
    catalog_name: DEFAULTS.catalog_name, schema_name: DEFAULTS.schema_name,
    source_volume: DEFAULTS.source_volume, source_path: '', file_format: DEFAULTS.file_format, file_pattern: DEFAULTS.file_pattern,
    jdbc_url: 'jdbc:oracle:thin:@//<host>:<port>/<service>', oracle_table: '', watermark_col: '',
    target_schema: DEFAULTS.target_schema, target_table: DEFAULTS.target_table,
    artifacts_volume: DEFAULTS.artifacts_volume, business_domain: DEFAULTS.business_domain,
    target_description: DEFAULTS.target_description, requirements_text: '',
  });
  const [file, setFile] = useState(null);
  const fileRef = useRef(null);
  const isAdls = pattern.id === 'adls_to_bronze';

  const set = (k) => (e) => setForm(prev => ({ ...prev, [k]: e.target.value }));

  const handleSubmit = () => {
    const cfg = {
      pattern_id: pattern.id, pattern_name: pattern.name,
      catalog_name: form.catalog_name, schema_name: form.schema_name,
      target_schema: form.target_schema, target_table: form.target_table,
      target_description: form.target_description,
      artifacts_volume: form.artifacts_volume, business_domain: form.business_domain,
      requirements_text: form.requirements_text,
    };
    if (isAdls) {
      cfg.volume_source = { source_volume: form.source_volume, source_path: form.source_path, file_format: form.file_format, file_pattern: form.file_pattern };
    } else {
      cfg.oracle_config = { jdbc_url: form.jdbc_url, source_table: form.oracle_table, watermark_column: form.watermark_col };
    }
    onGenerate(cfg, file);
  };

  const F = (label, key, opts) => {
    const { hint, type, full } = opts || {};
    const cls = full ? 'field' : 'field';
    if (type === 'select') {
      return React.createElement('div', { className: cls },
        React.createElement('label', null, label),
        React.createElement('select', { value: form[key], onChange: set(key) },
          (opts.options || []).map(o => React.createElement('option', { key: o, value: o }, o))
        ),
        hint && React.createElement('span', { className: 'hint' }, hint)
      );
    }
    if (type === 'textarea') {
      return React.createElement('div', { className: cls },
        React.createElement('label', null, label),
        React.createElement('textarea', { value: form[key], onChange: set(key), placeholder: opts.placeholder || '', rows: 4 }),
        hint && React.createElement('span', { className: 'hint' }, hint)
      );
    }
    return React.createElement('div', { className: cls },
      React.createElement('label', null, label),
      React.createElement('input', { type: 'text', value: form[key], onChange: set(key), placeholder: opts && opts.placeholder || '' }),
      hint && React.createElement('span', { className: 'hint' }, hint)
    );
  };

  return React.createElement('div', { className: 'container' },
    React.createElement('button', { className: 'back-btn', onClick: onBack }, '\u2190 Back'),
    React.createElement('div', { className: 'form-title' },
      React.createElement('span', null, pattern.icon), ' Configure: ', pattern.name
    ),
    /* Catalog & Schema */
    React.createElement('div', { className: 'section' },
      React.createElement('div', { className: 'section-label' }, 'Catalog & Schema'),
      React.createElement('div', { className: 'row' },
        F('Catalog Name *', 'catalog_name'),
        F('Schema Name *', 'schema_name')
      )
    ),
    /* Source */
    React.createElement('div', { className: 'section' },
      React.createElement('div', { className: 'section-label' }, 'Source Configuration'),
      isAdls ? React.createElement(React.Fragment, null,
        React.createElement('div', { className: 'row' },
          F('Source Volume Name *', 'source_volume', { hint: 'UC Volume containing source files' }),
          F('Source Path (subfolder)', 'source_path', { hint: 'Optional subfolder within volume' })
        ),
        React.createElement('div', { className: 'row' },
          F('File Format', 'file_format', { type: 'select', options: ['csv', 'json'] }),
          F('File Pattern', 'file_pattern', { hint: 'e.g. *.csv or customers_*' })
        )
      ) : React.createElement(React.Fragment, null,
        React.createElement('div', { className: 'row' },
          F('JDBC URL *', 'jdbc_url'),
          F('Oracle Source Table *', 'oracle_table', { placeholder: 'SCHEMA.TABLE' })
        ),
        React.createElement('div', { className: 'row' },
          F('Watermark Column', 'watermark_col', { hint: 'For incremental loads' }),
          React.createElement('div', null)
        )
      )
    ),
    /* Target */
    React.createElement('div', { className: 'section' },
      React.createElement('div', { className: 'section-label' }, 'Target Configuration'),
      React.createElement('div', { className: 'row' },
        F('Target Schema *', 'target_schema'),
        F('Target Bronze Table Name *', 'target_table')
      ),
      React.createElement('div', { className: 'row' },
        F('Artifacts Volume Name *', 'artifacts_volume', { hint: 'Auto-created if missing' }),
        F('Business Domain', 'business_domain', { hint: 'e.g. Healthcare, Finance' })
      ),
      F('Table Description', 'target_description', { type: 'textarea', full: true, placeholder: 'Describe the target table...' })
    ),
    /* Requirements */
    React.createElement('div', { className: 'section' },
      React.createElement('div', { className: 'section-label' }, 'Requirements'),
      React.createElement('div', {
        className: 'upload-area' + (file ? ' has-file' : ''),
        onClick: () => fileRef.current && fileRef.current.click()
      },
        React.createElement('input', { ref: fileRef, type: 'file', accept: '.txt,.md,.pdf,.docx', hidden: true, onChange: (e) => setFile(e.target.files[0]) }),
        React.createElement('p', null, file ? ('\u2705 ' + file.name) : '\uD83D\uDCC1 Drop a requirements file here or click to browse'),
        React.createElement('p', { className: 'formats' }, 'TXT, MD, PDF, DOCX')
      ),
      React.createElement('div', { style: { marginTop: 14 } },
        F('Additional Requirements', 'requirements_text', {
          type: 'textarea', placeholder: 'e.g. Load frequency: daily\nNull check on member_id\nDeduplicate on primary key'
        })
      )
    ),
    React.createElement('button', { className: 'btn-primary', onClick: handleSubmit },
      '\u2728 Generate Package'
    )
  );
}

/* ---------- ProgressOverlay ---------- */
function ProgressOverlay({ step, total, message }) {
  const pct = total > 0 ? Math.round((step / total) * 100) : 0;
  return React.createElement('div', { className: 'progress-overlay' },
    React.createElement('div', { className: 'progress-card' },
      React.createElement('div', { className: 'spinner' }),
      React.createElement('h3', null, 'Generating Package...'),
      React.createElement('div', { className: 'progress-bar-bg' },
        React.createElement('div', { className: 'progress-bar-fill', style: { width: pct + '%' } })
      ),
      React.createElement('p', { className: 'progress-msg' }, message || 'Initializing...')
    )
  );
}

/* ---------- Results ---------- */
function Results({ result, onReset }) {
  const [showPrompt, setShowPrompt] = useState(false);
  const [showArtifacts, setShowArtifacts] = useState(true);
  const [genieState, setGenieState] = useState('idle');
  const [genieInfo, setGenieInfo] = useState(null);
  const [genieError, setGenieError] = useState(null);
  const r = result;

  const handleRunGenie = async () => {
    setGenieState('running'); setGenieError(null);
    try {
      const resp = await fetch('/api/run-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: r.prompt, run_name: 'Integration Pattern - ' + r.package_id })
      });
      const data = await resp.json();
      if (data.success) { setGenieInfo(data); setGenieState('success'); }
      else { setGenieError(data.error || 'Failed to create job run'); setGenieState('error'); }
    } catch (e) { setGenieError(e.message); setGenieState('error'); }
  };
  return React.createElement('div', { className: 'container' },
    React.createElement('div', { className: 'result-banner' },
      React.createElement('h3', null, '\u2705 Package Generated Successfully'),
      React.createElement('p', null, 'Package ID: ', React.createElement('strong', null, r.package_id)),
      React.createElement('p', null, 'Location: ', React.createElement('code', { style: { fontSize: '.82rem' } }, r.package_path)),
      React.createElement('p', { style: { marginTop: 6 } },
        React.createElement('span', { className: 'tag ' + (r.used_llm ? 'tag-llm' : 'tag-fallback') },
          r.used_llm ? 'Claude LLM' : 'Fallback Template'
        ), ' ', r.llm_detail
      )
    ),
    /* Artifacts */
    React.createElement('div', { className: 'result-section' },
      React.createElement('div', { className: 'result-section-header', onClick: () => setShowArtifacts(!showArtifacts) },
        React.createElement('span', null, '\uD83D\uDCC2 Generated Artifacts (', r.artifacts.length, ')'),
        React.createElement('span', null, showArtifacts ? '\u25B2' : '\u25BC')
      ),
      showArtifacts && React.createElement('div', { className: 'result-section-body' },
        React.createElement('ul', { className: 'artifact-list' },
          r.artifacts.map((a, i) => React.createElement('li', { key: i },
            React.createElement('span', null, artifactIcon(a)), a
          ))
        )
      )
    ),
    /* Prompt */
    React.createElement('div', { className: 'result-section' },
      React.createElement('div', { className: 'result-section-header', onClick: () => setShowPrompt(!showPrompt) },
        React.createElement('span', null, '\uD83D\uDCAC Generated Prompt'),
        React.createElement('span', null, showPrompt ? '\u25B2' : '\u25BC')
      ),
      showPrompt && React.createElement('div', { className: 'result-section-body' },
        React.createElement('div', { className: 'prompt-preview' }, r.prompt)
      )
    ),
    /* Next steps */
    React.createElement('div', { className: 'result-section' },
      React.createElement('div', { className: 'result-section-header' }, React.createElement('span', null, '\uD83D\uDE80 Next Steps')),
      React.createElement('div', { className: 'result-section-body', style: { fontSize: '.875rem', color: '#475569' } },
        React.createElement('ol', { style: { paddingLeft: 20 } },
          React.createElement('li', null, 'Open the generated_prompt.md from the artifacts volume'),
          React.createElement('li', null, 'Paste it into Genie Code to generate the full implementation'),
          React.createElement('li', null, 'Run notebooks/01_ingest_to_bronze.py to test ingestion'),
          React.createElement('li', null, 'Run notebooks/02_data_quality_checks.py to validate')
        )
      )
    ),
    /* Genie Code execution */
    genieState === 'success' && genieInfo && React.createElement('div', { className: 'result-banner', style: { marginTop: 0, marginBottom: 16, background: '#eef2ff', borderColor: '#a5b4fc' } },
      React.createElement('h3', { style: { color: '#4f46e5' } }, '\u26A1 Genie Code Job Submitted'),
      React.createElement('p', null, 'Run ID: ', React.createElement('strong', null, genieInfo.run_id)),
      React.createElement('p', { style: { marginTop: 8 } },
        React.createElement('a', { href: genieInfo.run_url, target: '_blank', rel: 'noopener',
          style: { color: '#4f46e5', fontWeight: 600, textDecoration: 'none', padding: '8px 20px', border: '1px solid #4f46e5', borderRadius: '8px', display: 'inline-block' }
        }, 'Open Job Run \u2192')
      )
    ),
    genieState === 'error' && React.createElement('div', { className: 'error-box', style: { marginBottom: 16 } }, '\u274C ', genieError),
    /* Action buttons */
    React.createElement('div', { style: { marginTop: 24, textAlign: 'center', display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' } },
      React.createElement('button', {
        className: 'btn-primary',
        onClick: handleRunGenie,
        disabled: genieState === 'running' || genieState === 'success',
        style: { width: 'auto', padding: '14px 32px' }
      }, genieState === 'running' ? '\u23F3 Creating Job Run...' : genieState === 'success' ? '\u2705 Job Submitted' : '\u26A1 Execute with Genie Code'),
      React.createElement('button', { className: 'btn-outline', onClick: onReset }, '\u2190 Generate Another Package')
    )
  );
}

/* ---------- App ---------- */
function App() {
  const [page, setPage] = useState('landing');
  const [patterns, setPatterns] = useState({});
  const [selected, setSelected] = useState(null);
  const [progress, setProgress] = useState({ step: 0, total: 10, message: '' });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/patterns').then(r => r.json()).then(setPatterns);
  }, []);

  const handleSelect = (p) => { setSelected(p); setPage('config'); setError(null); };
  const handleBack = () => { setPage('landing'); setError(null); };
  const handleReset = () => { setPage('landing'); setResult(null); setError(null); setProgress({ step: 0, total: 10, message: '' }); };

  const handleGenerate = async (cfg, file) => {
    setPage('generating');
    setProgress({ step: 0, total: 10, message: 'Starting...' });
    setError(null);

    const fd = new FormData();
    fd.append('config_json', JSON.stringify(cfg));
    if (file) fd.append('file', file);

    try {
      const resp = await fetch('/api/generate', { method: 'POST', body: fd });
      if (!resp.ok && resp.headers.get('content-type')?.includes('json')) {
        const err = await resp.json();
        setError(err.errors ? err.errors.join(', ') : 'Request failed');
        setPage('config');
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.type === 'progress') setProgress({ step: evt.step, total: evt.total, message: evt.message });
            if (evt.type === 'complete') { setResult(evt.result); setPage('results'); }
            if (evt.type === 'error') { setError(evt.message); setPage('config'); }
          } catch (e) { /* ignore parse errors on keepalive */ }
        }
      }
    } catch (e) {
      setError('Network error: ' + e.message);
      setPage('config');
    }
  };

  return React.createElement(React.Fragment, null,
    React.createElement(Header),
    page === 'landing' && React.createElement(Landing, { patterns, onSelect: handleSelect }),
    page === 'config' && React.createElement(React.Fragment, null,
      React.createElement(ConfigForm, { pattern: selected, onBack: handleBack, onGenerate: handleGenerate }),
      error && React.createElement('div', { className: 'container' },
        React.createElement('div', { className: 'error-box' }, '\u274C ', error)
      )
    ),
    page === 'generating' && React.createElement(ProgressOverlay, progress),
    page === 'results' && result && React.createElement(Results, { result, onReset: handleReset })
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
