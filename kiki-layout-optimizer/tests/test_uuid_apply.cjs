const assert=require('assert'),fs=require('fs'),vm=require('vm');
const scripts=['json_helpers.jsxinc','language.jsxinc','workspace.jsxinc','bridge_receipt.jsxinc','apply_layout.jsx'];
const source=scripts.map(f=>fs.readFileSync('illustrator/'+f,'utf8').replace(/^\uFEFF?#(?:target|include).*$/mg,'')).join('\n');
const things=[
 {uuid:'one',name:'A',geometricBounds:[0,100,20,80],editable:true},
 {uuid:'two',name:'B',geometricBounds:[40,100,60,80],editable:true}
];
things.forEach(it=>{it.translate=function(x,y){this.geometricBounds=[this.geometricBounds[0]+x,this.geometricBounds[1]+y,this.geometricBounds[2]+x,this.geometricBounds[3]+y]};it.rotate=function(a){assert.equal(a,0);};});
const result={schema:1,document_name:'Test.ai',source_selection_count:2,
 artboard:{width_mm:100,height_mm:50},items:things.map((it,i)=>({id:String(i),source_uuid:it.uuid,source_name:it.name,
 source_bounds_pt:it.geometricBounds.slice(),rotation_deg:0,x_mm:20+i*25,y_mm:12}))};
const doc={name:'Test.ai',selection:[things[1]],artboards:[{artboardRect:[0,100,100*72/25.4,100-50*72/25.4]}],
 getPageItemFromUuid(uuid){return things.find(t=>t.uuid===uuid);}};
doc.artboards.getActiveArtboardIndex=()=>0;
const alerts=[];
const File={openDialog:()=>({open:()=>true,read:()=>JSON.stringify(result),close(){}})};
vm.runInNewContext(source,{app:{documents:[doc],activeDocument:doc,redraw(){}},File,
 Error,isFinite,Math,String,Number,RegExp,Transformation:{CENTER:0},confirm:()=>true,alert:s=>alerts.push(s)});
assert(alerts.some(a=>a.includes('объектов: 2')),alerts.join(';'));
assert.notDeepStrictEqual(things[0].geometricBounds,[0,100,20,80]);
console.log('PASS apply by UUID despite a changed Illustrator selection');
