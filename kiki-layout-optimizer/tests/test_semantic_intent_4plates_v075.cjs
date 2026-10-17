// Regression: generic automatically detected families are not semantic rules.
// In prior QA P01 had 13/13 "Other" bulk-confirmed, P03/P10 provisional,
// and P11 had 43 meaningful reviewed numerical/carrier groups.
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const base=path.resolve(__dirname,'../cep/com.kikimodels.layoutoptimizer');
const js=fs.readFileSync(path.join(base,'panel.js'),'utf8');
const html=fs.readFileSync(path.join(base,'index.html'),'utf8');
assert.doesNotThrow(()=>new vm.Script(js));
const match=js.match(/function hasReviewedSemanticIntent\(row\)\{[\s\S]*?\n\}/);
assert(match,'Semantic intent gate must exist');
const gate=vm.runInNewContext('('+match[0]+')');
const row=(section,status,value,edited=false)=>({section,status,value,edited});
assert.equal(gate(row('other','confirmed',null)),false,'generic P01 Others must not force 3.92mm gap');
assert.equal(gate(row('other','provisional',null)),false,'P03 defaults must not force 3.34mm gap');
assert.equal(gate(row('role','provisional',null)),false,'unreviewed P10 role must not force 2.74mm gap');
assert.equal(gate(row('role','confirmed',null)),true,'explicitly reviewed P10 role orders safely');
assert.equal(gate(row('chapter','confirmed',null)),true);
assert.equal(gate(row('carrier','confirmed',null)),true);
assert.equal(gate(row('roman','confirmed',1)),true,'P11 numeric families stay strict');
assert.equal(gate(row('gothic','confirmed',10)),true);
assert.equal(gate(row('roman','confirmed',null)),false,'missing number cannot be treated as valid');
assert.equal(gate(row('roman','provisional',14)),false,'unreviewed numbers may not masquerade as confirmed');
assert.equal(gate(row('other','confirmed',null,true)),true,'manual ordering is an explicit semantic rule');
assert.match(js,/if\(!hasReviewedSemanticIntent\(row\)\)return;/);
assert.match(js,/Generic Other rows cannot be bulk confirmed/);
assert.match(html,/Подтвердить размеченные/);
console.log('PASS semantic intent gating: P01/P03/P10 defaults do not override 4.5 mm, P11 numbering preserved');
