#target illustrator
/* KiKi v0.4.1: launch the persistent Python desktop dashboard.
   Avoid ScriptUI palettes in Illustrator 30.x: on some builds they close
   immediately after the JSX invocation finishes. */
(function () {
    try {
        var folder = new File($.fileName).parent;
        var root = folder.parent;
        var win = $.os.toLowerCase().indexOf('windows') !== -1;
        var launcher = new File(root.fsName + (win ? '/launch_gui_windows.vbs' : '/launch_gui_macos.command'));
        if (!launcher.exists) throw new Error('KiKi launcher missing: ' + launcher.fsName);
        if (!launcher.execute()) throw new Error('Cannot launch KiKi desktop dashboard: ' + launcher.fsName);
    } catch (e) {
        alert('KiKi Models: ' + e.message + ' (line ' + (e.line || '?') + ')');
    }
})();
