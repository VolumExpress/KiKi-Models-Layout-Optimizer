// The CEP UI is shipped as plain JS. This test catches syntax errors and
// accidental reintroduction of P11-only controls without starting Illustrator.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const base=path.resolve(__dirname,'../cep/com.kikimodels.layoutoptimizer');
const js=fs.readFileSync(path.join(base,'panel.js'),'utf8');
const html=fs.readFileSync(path.join(base,'index.html'),'utf8');
assert.doesNotThrow(()=>new vm.Script(js,{filename:'panel.js'}));
assert.match(html,/<option value="semantic">/);
assert.match(html,/id="familyEditorSection"/);
assert.match(html,/id="familyEditorRows"/);
assert.doesNotMatch(html,/id="semanticOrder"/);
assert.match(js,/function renderFamilyEditor\(/);
assert.match(js,/function loadFamilyPlan\(/);
assert.match(js,/function saveFamilyPlan\(/);
assert.match(js,/function familyThumbnail\(/);
assert.match(js,/calcReady=false;\$\('apply'\)\.disabled=true/);
assert.match(js,/lastFolder,'family_plan\.json'/);
assert.match(js,/Object\.keys\(entries\)\.length/);
console.log('PASS universal family editor JS syntax and integrated controls');
