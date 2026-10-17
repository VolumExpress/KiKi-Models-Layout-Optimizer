// Regression: filled two-anchor Bezier curves may enclose a valid area.
// Illustrator mock only; never changes user artwork.
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(__dirname,'../illustrator');
const code=['json_helpers.jsxinc','language.jsxinc','workspace.jsxinc','bridge_receipt.jsxinc','export_selection.jsx']
  .map(f=>fs.readFileSync(path.join(root,f),'utf8').replace(/^\uFEFF?#(?:target|include).*$/mg,'')).join('\n');
function makeBezier(shift=0){
  const p0=[10+shift,10],p1=[20+shift,10];
  return {typename:'PathItem',name:'two-anchor lens',guides:false,clipping:false,
    filled:true,stroked:false,closed:true,hidden:false,locked:false,editable:true,
    pathPoints:[
      {anchor:p0,leftDirection:[13+shift,9.98],rightDirection:[13+shift,10.02]},
      {anchor:p1,leftDirection:[17+shift,10.02],rightDirection:[17+shift,9.98]}
    ]};
}
const bezier=makeBezier();
const compound={typename:'CompoundPathItem',name:'P03-compound',hidden:false,locked:false,editable:true,
  pathItems:[bezier],geometricBounds:[10,10.02,20,9.98],uuid:'p03-uuid'};
const open=makeBezier(25);open.name='open-filled-curve';open.closed=false;open.uuid='p03-open';open.geometricBounds=[35,10.02,45,9.98];
const artboards=[{artboardRect:[0,100,411,-169.29]}];artboards.getActiveArtboardIndex=()=>0;
const doc={name:'P03_TEST.ai',selection:[compound,open],artboards};
let json='',alerts=[];
const File={saveDialog:()=>({encoding:'',open:()=>true,write(v){json=v;},close(){}})};
vm.runInNewContext(code,{app:{documents:[doc],activeDocument:doc},File,alert:s=>alerts.push(String(s)),
 Error,isFinite,Math,String,Number,RegExp,Date});
assert(json,alerts.join('\n'));
const data=JSON.parse(json);assert.equal(data.objects.length,2);
assert.equal(data.objects[0].uuid,'p03-uuid');
const rings=data.objects[0].geometry.rings;
assert.equal(rings.length,1);assert(rings[0].length>=4,JSON.stringify(rings));
const area=Math.abs(rings[0].reduce((a,p,i)=>{const q=rings[0][(i+1)%rings[0].length];return a+p[0]*q[1]-p[1]*q[0]},0))/2;
assert(area>1e-6,'Bezier lens flattened to a zero-area line');
const openRing=data.objects[1].geometry.ring;
assert(openRing.length>=4,'Open filled curved path should retain its interior');
assert.deepEqual(bezier.pathPoints[0].anchor,[10,10],'Artwork must remain untouched');
assert.equal(data.source_selection_count,2);
console.log('PASS filled closed/open two-anchor Bezier, stable IDs, non-destructive export');
