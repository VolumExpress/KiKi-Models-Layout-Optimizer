/* Contract for a compact bilingual CEP help/label system. */
const fs=require('fs'), assert=require('assert'), path=require('path');
const html=fs.readFileSync('cep/com.kikimodels.layoutoptimizer/index.html','utf8');
const js=fs.readFileSync('cep/com.kikimodels.layoutoptimizer/panel.js','utf8');
const ids=Array.from(html.matchAll(/\bid="([^"]+)"/g),x=>x[1]);
assert.strictEqual(new Set(ids).size,ids.length,'duplicate HTML element IDs');
const keys=[...html.matchAll(/\bdata-i18n="([^"]+)"/g)].map(x=>x[1]);
const translationList=js.match(/var i18nIds=\[([^\]]+)\]/)[1];
const ru=js.split('ru:{',2)[1].split('\nen:{',1)[0];
const en=js.split('en:{',2)[1].split('\n}}',1)[0];
for (const key of keys){
 assert(translationList.includes("'"+key+"'"),'missing dynamic translation: '+key);
 assert(new RegExp('(?:^|[,\\n])'+key+':').test(ru),'missing RU translation: '+key);
 assert(new RegExp('(?:^|[,\\n])'+key+':').test(en),'missing EN translation: '+key);
}
for(const required of ['workflowHelp','operationHelp','modeHelp','familyHelp','rotationHelp','clearanceHelp','familyLayoutHelp','travelHelp','rulesHelp','presetHelp','familyReviewNote','showFamilyIds']){
 assert(keys.includes(required),'missing expected help: '+required);
}
assert(!html.includes('прежний алгоритм'),'avoid engineering labels in public controls');
assert(!html.includes('Generalized NFP Beta'),'remove stale technical subtitle');
for(const docs of ['README.md','README_RU.md','README_EN.md','docs/ru/FAMILY-LAYOUT-QA.md','docs/en/FAMILY-LAYOUT-QA.md'])
 assert(fs.existsSync(docs),'missing paired documentation '+docs);
console.log('PASS CEP help keys, no duplicate IDs, RU/EN translations, docs audit');
