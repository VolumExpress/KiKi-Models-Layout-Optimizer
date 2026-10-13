#target illustrator
#include "json_helpers.jsxinc"
#include "language.jsxinc"
#include "workspace.jsxinc"
#include "bridge_receipt.jsxinc"
/* KiKi Models — non-destructive exporter for visible vector fill/stroke geometry.
   Each top-level selection entry is one movable unit, original indices preserved.
   Stroke widths are exported for a conservative centreline-buffer approximation
   in Python; Illustrator artwork is NEVER expanded, edited or outlined here.
   Clipping and unsupported objects fail loudly rather than losing detail. */
(function () {
  try {
    if (app.documents.length === 0) throw Error(kikiT('no_doc'));
    var doc = app.activeDocument, selected = doc.selection;
    if (!selected || selected.length < 1) throw Error(kikiT('no_selection'));
    var MM = 25.4 / 72.0;
    var TOL_PT = 0.06; // ~0.021 mm sampling error vs Bezier centreline
    var skippedEmptyGroups = 0, skippedUnpainted = 0, sampledStrokes = 0, filledOpen = 0;

    function mid(a,b) { return [(a[0]+b[0])/2,(a[1]+b[1])/2]; }
    function nearLine(p,a,b) {
      var dx=b[0]-a[0],dy=b[1]-a[1],den=Math.sqrt(dx*dx+dy*dy);
      if (den < 0.00001) return Math.sqrt(Math.pow(p[0]-a[0],2)+Math.pow(p[1]-a[1],2));
      return Math.abs((p[0]-a[0])*dy-(p[1]-a[1])*dx)/den;
    }
    function flatten(p0,p1,p2,p3,out,depth) {
      if (depth >= 12 || Math.max(nearLine(p1,p0,p3),nearLine(p2,p0,p3)) <= TOL_PT) {
        out.push(p3); return;
      }
      var a=mid(p0,p1),b=mid(p1,p2),c=mid(p2,p3);
      var d=mid(a,b),e=mid(b,c),f=mid(d,e);
      flatten(p0,a,d,f,out,depth+1); flatten(f,e,c,p3,out,depth+1);
    }
    function toLocal(p,centre) { return [(p[0]-centre[0])*MM,(centre[1]-p[1])*MM]; }
    function describe(item) {
      return (item.name ? '"'+item.name+'"' : '(unnamed)')+' ['+item.typename+']';
    }
    // Actual centreline of open or closed Bezier path; no invented closure for strokes.
    function points(path,centre) {
      var anchors=path.pathPoints, n=anchors.length;
      if (n < 2) throw Error(kikiT('bad_path'));
      var out=[toLocal(anchors[0].anchor,centre)];
      var count=path.closed ? n : n-1;
      for (var j=0; j<count; j++) {
        var p=anchors[j],q=anchors[(j+1)%n],segment=[];
        flatten(p.anchor,p.rightDirection,q.leftDirection,q.anchor,segment,0);
        for (var k=0; k<segment.length; k++) {
          if (path.closed && j===n-1 && k===segment.length-1) continue;
          out.push(toLocal(segment[k],centre));
        }
      }
      return out;
    }
    function capName(path) {
      // Prefer exact Illustrator enum comparison (its string coercion may vary).
      try {
        if (typeof StrokeCap !== 'undefined') {
          if (path.strokeCap===StrokeCap.ROUNDENDCAP) return 'round';
          if (path.strokeCap===StrokeCap.PROJECTINGENDCAP) return 'square';
          if (path.strokeCap===StrokeCap.BUTTENDCAP) return 'flat';
        }
      } catch(e) {}
      var s=''; try { s=String(path.strokeCap).toUpperCase(); } catch(e) {}
      if (s.indexOf('ROUND')>=0) return 'round';
      if (s.indexOf('PROJECTING')>=0 || s.indexOf('SQUARE')>=0) return 'square';
      return 'flat'; // Illustrator BUTTENDCAP
    }
    function joinName(path) {
      try {
        if (typeof StrokeJoin !== 'undefined') {
          if (path.strokeJoin===StrokeJoin.ROUNDENDJOIN) return 'round';
          if (path.strokeJoin===StrokeJoin.BEVELENDJOIN) return 'bevel';
          if (path.strokeJoin===StrokeJoin.MITERENDJOIN) return 'mitre';
        }
      } catch(e) {}
      var s=''; try { s=String(path.strokeJoin).toUpperCase(); } catch(e) {}
      if (s.indexOf('ROUND')>=0) return 'round';
      if (s.indexOf('BEVEL')>=0) return 'bevel';
      return 'mitre';
    }
    function strokeNode(path, centre, polyline) {
      var width=Number(path.strokeWidth);
      if (!(width>0) || !isFinite(width))
        throw Error(kikiT('invalid_stroke',{item:describe(path)}));
      var ml=5;
      try { var limit=Number(path.strokeMiterLimit); if (limit>0 && isFinite(limit)) ml=limit; } catch(e) {}
      sampledStrokes++;
      return {type:'stroke',points:polyline,closed:!!path.closed,
              width_mm:width*MM,cap:capName(path),join:joinName(path),mitre_limit:ml};
    }
    function pathGeometry(path,centre) {
      if (path.guides) return null; // Illustrator guide is not artwork
      if (path.clipping) throw Error(kikiT('clipping_path',{item:describe(path)}));
      var filled=!!path.filled,stroked=!!path.stroked;
      if (!filled && !stroked) { skippedUnpainted++; return null; }
      var polyline=points(path,centre), children=[];
      if (filled) {
        if (polyline.length < 3) throw Error(kikiT('filled_path',{item:describe(path)}));
        // Illustrator closes the interior of an open filled path implicitly.
        if (!path.closed) filledOpen++;
        children.push({type:'path',ring:polyline});
      }
      if (stroked) children.push(strokeNode(path,centre,polyline));
      return children.length===1 ? children[0] : {type:'group',children:children};
    }
    function compoundGeometry(item,centre) {
      var fills=[],strokes=[];
      for (var j=0;j<item.pathItems.length;j++) {
        var path=item.pathItems[j];
        if (path.guides) continue;
        if (path.clipping) throw Error(kikiT('clipping_compound',{item:describe(item)}));
        var filled=!!path.filled,stroked=!!path.stroked;
        if (!filled && !stroked) { skippedUnpainted++; continue; }
        var polyline=points(path,centre);
        if (filled) {
          if (polyline.length<3) throw Error(kikiT('filled_part'));
          if (!path.closed) filledOpen++;
          fills.push(polyline);
        }
        if (stroked) strokes.push(strokeNode(path,centre,polyline));
      }
      var nodes=[];
      if (fills.length) nodes.push({type:'compound',rings:fills});
      for(var k=0;k<strokes.length;k++) nodes.push(strokes[k]);
      return nodes.length===0 ? null : nodes.length===1 ? nodes[0] : {type:'group',children:nodes};
    }
    function geometry(item,centre) {
      if (item.hidden || item.locked) throw Error(kikiT('hidden_locked',{item:describe(item)}));
      if (item.typename==='PathItem') return pathGeometry(item,centre);
      if (item.typename==='CompoundPathItem') return compoundGeometry(item,centre);
      if (item.typename==='GroupItem') {
        if (item.clipped) throw Error(kikiT('clipping_group',{item:describe(item)}));
        var children=[];
        for (var k=0;k<item.pageItems.length;k++) {
          var child=item.pageItems[k], sub;
          try { sub=geometry(child,centre); }
          catch(e) { throw Error(kikiT('child_error',{item:describe(item),index:k,child:describe(child),message:e.message})); }
          if (sub!==null) children.push(sub);
        }
        if (children.length===0) { skippedEmptyGroups++; return null; }
        return {type:'group',children:children};
      }
      throw Error(kikiT('unsupported',{type:item.typename,name:item.name}));
    }
    var index=doc.artboards.getActiveArtboardIndex();
    var board=doc.artboards[index].artboardRect;
    var data={schema:1,document_name:doc.name,
      source_selection_count:selected.length,
      artboard:{index:index,rect_pt:[board[0],board[1],board[2],board[3]],width_mm:Math.abs(board[2]-board[0])*MM,
        height_mm:Math.abs(board[1]-board[3])*MM},objects:[],skipped:[]};
    for(var i=0;i<selected.length;i++) {
      var item=selected[i];
      if (!item.editable) throw Error(kikiT('not_editable',{item:describe(item)}));
      var box=item.geometricBounds;
      var centre=[(box[0]+box[2])/2,(box[1]+box[3])/2];
      var shape;
      try { shape=geometry(item,centre); }
      catch(e) { throw Error(kikiT('selection_error',{index:i,item:describe(item),message:e.message})); }
      if (shape===null) {
        data.skipped.push({selection_index:i,name:item.name||'',reason:'no paintable geometry'});
        continue;
      }
      data.objects.push({id:String(i),uuid:(function(){try{return String(item.uuid||'');}catch(ignore){return '';}})(),name:item.name||('item-'+i),
        source_bounds_pt:[box[0],box[1],box[2],box[3]],geometry:shape});
    }
    if(data.objects.length===0) throw Error(kikiT('no_geometry'));
    var destination=kikiWorkspaceFile(doc,'input_copy.json');
    if(!destination) destination=File.saveDialog(kikiT('save_export'),'*.json');
    if(!destination)return;
    // v0.6.4: every repeated export is a new document revision. Keep a
    // local, dated snapshot, then reconcile constraints using UUID + actual
    // geometry. Never blindly reuse an index after selection order changes.
    var ruleFile=kikiWorkspaceFile(doc,'constraints.json');
    var oldExport=null, oldRules=null, audit={schema:1, preserved:0, reset:[], archived:false};
    function loadLocal(f){
      if(!f || !f.exists)return null;
      f.encoding='UTF-8';if(!f.open('r'))throw Error('Cannot read '+f.fsName);
      var content=f.read();f.close();return content;
    }
    function putLocal(f,content){
      f.encoding='UTF-8';if(!f.open('w'))throw Error('Cannot write '+f.fsName);
      f.write(content);f.close();
    }
    var previousText=loadLocal(destination), previousRules=loadLocal(ruleFile);
    if(previousText!==null || previousRules!==null){
      var rootDir=destination.parent, history=new Folder(rootDir.fsName+'/history');
      if(!history.exists && !history.create())throw Error('Cannot create export history');
      var tag=String((new Date()).getTime());
      for(var suffix=0; new File(history.fsName+'/'+tag+(suffix?'_'+suffix:'')+'_input.json').exists; suffix++){}
      tag+=(suffix?'_'+suffix:'');
      if(previousText!==null)putLocal(new File(history.fsName+'/'+tag+'_input.json'),previousText);
      if(previousRules!==null)putLocal(new File(history.fsName+'/'+tag+'_constraints.json'),previousRules);
      audit.archived=true;
    }
    if(previousRules!==null){
      try{
        oldRules=kikiParseJSON(previousRules);
        oldExport=previousText!==null?kikiParseJSON(previousText):null;
        if(!oldExport || oldExport.document_name!==doc.name || oldRules.schema!==1 ||
           oldRules.document_name!==doc.name)throw Error('Previous export/constraints mismatch');
        var previousById={}, nextByUuid={};
        for(var oi=0;oi<oldExport.objects.length;oi++)previousById[String(oldExport.objects[oi].id)]=oldExport.objects[oi];
        for(var ni=0;ni<data.objects.length;ni++)if(data.objects[ni].uuid)nextByUuid[data.objects[ni].uuid]=data.objects[ni];
        var newItems={}, oldItems=oldRules.items||{};
        for(var oldId in oldItems)if(oldItems.hasOwnProperty(oldId)){
          var oldObj=previousById[oldId], rule=oldItems[oldId], current=oldObj&&oldObj.uuid?nextByUuid[oldObj.uuid]:null;
          var reason='';
          if(!oldObj || !current)reason='missing_uuid';
          else if(oldObj.name!==current.name || rule.source_name!==oldObj.name)reason='name_changed';
          else if(kikiStringify(oldObj.geometry)!==kikiStringify(current.geometry))reason='geometry_changed';
          else{
            var before=oldObj.source_bounds_pt, now=current.source_bounds_pt, stored=rule.source_bounds_pt;
            if(!before||!stored||!now||before.length!==4||stored.length!==4||now.length!==4)reason='bounds_missing';
            else for(var bi=0;bi<4;bi++)if(Math.abs(before[bi]-now[bi])>0.05 ||
                     Math.abs(before[bi]-stored[bi])>0.05){reason='bounds_changed';break;}
          }
          if(reason)audit.reset.push({id:oldId,reason:reason,name:oldObj?oldObj.name:''});
          else{
            newItems[String(current.id)]={source_name:current.name,source_bounds_pt:current.source_bounds_pt,
                lock_position:!!rule.lock_position,rotations:rule.rotations};
            audit.preserved++;
          }
        }
        oldRules={schema:1,document_name:doc.name,items:newItems};
      }catch(reconcileError){
        audit.reset.push({id:'*',reason:'invalid_previous_rules',detail:String(reconcileError)});
        oldRules={schema:1,document_name:doc.name,items:{}};
      }
    }
    // The export always supersedes stale calculations and old rules. Avoid
    // corrupting valid constraints if the previous snapshot could not be read.
    // Never allow applying an obsolete calculation after a new export.
    if(typeof File === 'function' && typeof Folder === 'function') {
      var staleNames=['result_test.json','preview_test.svg','best_so_far.json',
                      'best_so_far.svg','route_test.svg','route_test.csv'];
      for(var si=0;si<staleNames.length;si++){
        var stale=kikiWorkspaceFile(doc,staleNames[si]);
        if(stale && stale.exists && !stale.remove())throw Error(kikiT('cannot_clear_result'));
      }
    }
    // Only write the new revision after obsolete results are cleared.
    putLocal(destination,kikiStringify(data));
    if(oldRules!==null)putLocal(ruleFile,kikiStringify(oldRules));
    var auditFile=kikiWorkspaceFile(doc,'export_audit.json');
    if(auditFile)putLocal(auditFile,kikiStringify(audit));
    var isPanelExport=kikiBridgeIsRequested('export');
    kikiBridgeReceipt('export','ok','',destination.fsName);
    if(!isPanelExport)alert(kikiT('export_ok',{objects:data.objects.length,strokes:sampledStrokes,open:filledOpen,groups:skippedEmptyGroups,unpainted:skippedUnpainted,skipped:data.skipped.length})+'\n'+kikiT('file_saved',{path:destination.fsName}));
  }catch(e){var isPanelError=kikiBridgeIsRequested('export');kikiBridgeReceipt('export','error',e.message,'');if(!isPanelError)alert(kikiT('export_error',{message:e.message,line:e.line||'?'}));}
})();
