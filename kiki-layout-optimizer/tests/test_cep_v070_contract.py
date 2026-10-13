from pathlib import Path
from kiki_layout.cep_worker import ALLOWED

def test_new_worker_options_are_explicitly_whitelisted():
    assert {'objective_weights','cut_common_line_audit'} <= ALLOWED

def test_cep_has_unique_ids_and_required_controls():
    import re
    root=Path(__file__).resolve().parents[1]
    html=(root/'cep/com.kikimodels.layoutoptimizer/index.html').read_text(encoding='utf-8')
    ids=re.findall(r'\bid="([^"]+)"',html)
    assert len(ids)==len(set(ids)), 'Duplicate HTML IDs break CEP checkbox bindings'
    for ident in ('multiEnabled','wArea','wSpacing','wTravel','commonLineAudit','advancedSearch'):
        assert ident in ids
    js=(root/'cep/com.kikimodels.layoutoptimizer/panel.js').read_text(encoding='utf-8')
    for token in ('objective_weights','cut_common_line_audit','multiobjective','common_line_audit'):
        assert token in js
