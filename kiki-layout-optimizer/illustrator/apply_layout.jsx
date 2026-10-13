#target illustrator
#include "json_helpers.jsxinc"
#include "language.jsxinc"
#include "workspace.jsxinc"
#include "bridge_receipt.jsxinc"
/* KiKi Models — apply JSON layout to the EXACT same selected objects in a COPY.
   This changes only translation and rotation, not path control points or scale.
   FIRST SAVE AS A NEW .AI FILE and don't change the selection after export. */
(function(){
  try{
    if(app.documents.length===0)throw Error(kikiT('no_doc'));
    var doc=app.activeDocument;
    var input=kikiWorkspaceFile(doc,'result_test.json');
    if(!input || !input.exists) {
      if(input) throw Error(kikiT('missing_result',{path:input.fsName}));
      input=File.openDialog(kikiT('load_layout'),'*.json');
    }
    if(!input)return;
    input.encoding='UTF-8';if(!input.open('r'))throw Error(kikiT('cannot_read'));
    var raw=input.read();input.close();
    var data=kikiParseJSON(raw);
    if(data.schema!==1 || !data.items || !data.artboard)throw Error(kikiT('invalid_layout'));
    if(doc.name !== data.document_name)throw Error(kikiT('name_mismatch'));
    var selection=doc.selection;
    // Empty top-level groups may have been skipped by exporter; item IDs refer
    // to ORIGINAL selection indices and are intentionally not renumbered.
    var sourceCount=(typeof data.source_selection_count==='number')
      ? data.source_selection_count : data.items.length;
    // Illustrator 24+ UUIDs are stable across changed selections. The old
    // selection-index fallback remains for exports that predate v0.5.1.
    var uuidReady=(data.items.length>0);
    try { uuidReady=uuidReady && !!doc.getPageItemFromUuid; } catch(noUuidMethod) {uuidReady=false;}
    for(var ui=0;ui<data.items.length;ui++){
      if(!data.items[ui].source_uuid) {uuidReady=false;break;}
    }
    if(!uuidReady && (!selection || selection.length!==sourceCount))
      throw Error(kikiT('selection_mismatch',{count:sourceCount}));
    var MM=25.4/72.0;
    var aiBoard=doc.artboards[doc.artboards.getActiveArtboardIndex()].artboardRect;
    var width=Math.abs(aiBoard[2]-aiBoard[0])*MM;
    var height=Math.abs(aiBoard[1]-aiBoard[3])*MM;
    if(Math.abs(width-data.artboard.width_mm)>0.2 || Math.abs(height-data.artboard.height_mm)>0.2)
      throw Error(kikiT('board_mismatch'));
    var arranged=[];
    for(var i=0;i<data.items.length;i++){
      var item=data.items[i],id=parseInt(item.id,10);
      if(String(id)!==item.id || id<0 || id>=sourceCount)
        throw Error(kikiT('bad_index',{id:item.id}));
      var reference=null;
      if(uuidReady) {
        try { reference=doc.getPageItemFromUuid(item.source_uuid); } catch(lookupError) {}
        if(!reference || String(reference.uuid)!==String(item.source_uuid))
          throw Error('Cannot find original Illustrator object UUID '+item.source_uuid+'. Re-export.');
      } else {
        reference=selection[id];
        if(!reference)throw Error(kikiT('bad_index',{id:item.id}));
      }
      if(item.rotation_deg!==0 && item.rotation_deg!==90 && item.rotation_deg!==180 && item.rotation_deg!==270)
        throw Error(kikiT('rotation',{angle:item.rotation_deg}));
      if(!reference.editable)throw Error(kikiT('apply_editable',{id:item.id}));
      if(item.source_bounds_pt){
        var expected=item.source_bounds_pt, actual=reference.geometricBounds;
        for(var k=0;k<4;k++){
          if(Math.abs(expected[k]-actual[k])>0.05)
            throw Error(kikiT('bounds_changed',{id:id}));
        }
      }
      if(item.source_name && reference.name && item.source_name!==reference.name)
        throw Error(kikiT('order_changed',{id:id}));
      if(!isFinite(item.x_mm)||!isFinite(item.y_mm))throw Error(kikiT('bad_coordinates'));
      arranged.push({ref:reference,x:item.x_mm,y:item.y_mm,angle:item.rotation_deg});
    }
    if(!confirm(kikiT('apply_confirm'))){kikiBridgeReceipt('apply','cancelled','','');return;}
    for(var j=0;j<arranged.length;j++){
      var a=arranged[j],obj=a.ref;
      // Python's positive rotation corresponds to clockwise in screen-down Y;
      // Illustrator's positive angle is counter-clockwise in art coordinates.
      if(a.angle!==0)obj.rotate(-a.angle,true,false,false,false,Transformation.CENTER);
      var b=obj.geometricBounds;
      var currentX=(b[0]+b[2])/2, currentY=(b[1]+b[3])/2;
      var targetX=aiBoard[0]+a.x/MM, targetY=aiBoard[1]-a.y/MM;
      obj.translate(targetX-currentX,targetY-currentY);
    }
    app.redraw();
    var isPanelApply=kikiBridgeIsRequested('apply');
    kikiBridgeReceipt('apply','ok','',doc.name);
    if(!isPanelApply)alert(kikiT('apply_ok',{count:arranged.length}));
  }catch(e){var isPanelError=kikiBridgeIsRequested('apply');kikiBridgeReceipt('apply','error',e.message,'');if(!isPanelError)alert(kikiT('apply_error',{message:e.message,line:e.line||'?'}));}
})();
