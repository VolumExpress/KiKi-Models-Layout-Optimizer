#target illustrator
#include "language.jsxinc"
/* Three-step Illustrator UI: export, open local GUI, apply. */
(function(){
  try {
    if(app.documents.length===0)throw Error(kikiT('no_doc'));
    var folder=new File($.fileName).parent;
    var window=new Window('dialog','KiKi Models — Layout Optimizer');
    window.orientation='column';window.alignChildren='fill';window.spacing=11;
    window.add('statictext',undefined,'KiKi Models  |  Illustrator → Python → Illustrator');
    var l=kikiGetLanguage();
    var exportButton=window.add('button',undefined,l==='ru'?'1. Экспорт выделения':'1. Export selection');
    var calculateButton=window.add('button',undefined,l==='ru'?'2. Настройки и расчёт':'2. Settings and calculate');
    var applyButton=window.add('button',undefined,l==='ru'?'3. Применить раскладку':'3. Apply layout');
    var langButton=window.add('button',undefined,l==='ru'?'Русский / English':'English / Русский');
    var closeButton=window.add('button',undefined,l==='ru'?'Закрыть':'Close');
    function invoke(name){window.close();$.evalFile(new File(folder.fsName+'/'+name));}
    exportButton.onClick=function(){invoke('export_selection.jsx');};
    applyButton.onClick=function(){invoke('apply_layout.jsx');};
    langButton.onClick=function(){invoke('set_language.jsx');};
    calculateButton.onClick=function(){
      var root=folder.parent;
      var script=($.os.toLowerCase().indexOf('windows')!==-1)
        ? new File(root.fsName+'/launch_gui_windows.vbs')
        : new File(root.fsName+'/launch_gui_macos.command');
      if(!script.exists) {alert(l==='ru'?'Нет файла запуска интерфейса: ':'GUI launcher missing: '+script.fsName);return;}
      if(!script.execute()) alert(l==='ru'?'Не удалось открыть интерфейс. Проверьте установку Python.':'Cannot open GUI. Check Python installation.');
      window.close();
    };
    closeButton.onClick=function(){window.close();};
    window.show();
  }catch(e){alert('KiKi: '+e.message);}
})();
