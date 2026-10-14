#target illustrator
#include "language.jsxinc"
/* Run via File > Scripts > Other Script... to change interface language.
   Saved in the current OS user's KiKiModels settings folder, not in .ai. */
(function () {
  try {
    var current=kikiGetLanguage();
    var chosen=null;
    // ScriptUI is provided by Illustrator on Windows and macOS.
    if(typeof Window!=='undefined') {
      var ui=new Window('dialog',kikiT('choose_title'));
      ui.orientation='column';ui.alignChildren='left';
      ui.add('statictext',undefined,kikiT('choose_prompt'));
      var r=ui.add('radiobutton',undefined,'Русский');
      var e=ui.add('radiobutton',undefined,'English');
      r.value=current==='ru';e.value=current==='en';
      var actions=ui.add('group');actions.orientation='row';
      actions.add('button',undefined,kikiT('choose_accept'),{name:'ok'});
      actions.add('button',undefined,kikiT('choose_cancel'),{name:'cancel'});
      if(ui.show()!==1)return;
      chosen=r.value?'ru':'en';
    } else {
      var response=prompt('KiKi Models — language / язык\n1 — Русский\n2 — English',current==='ru'?'1':'2');
      if(response===null)return;
      chosen=(String(response).replace(/\s+/g,'').toLowerCase()==='2' || String(response).toLowerCase()==='en')?'en':'ru';
    }
    kikiSetLanguage(chosen);
    alert(kikiT('lang_saved'));
  } catch(ex) {
    alert(kikiT('lang_file_error')+'\n'+ex.message);
  }
})();
