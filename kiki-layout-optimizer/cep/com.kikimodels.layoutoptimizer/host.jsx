/* CEP adapter v0.4.3 — executes the existing authoritative Illustrator JSX.
   No COM, no AppleScript, no Node.js, no direct geometry edits in the panel.
   kikiCepAction(action, projectRoot, nonce) returns a JSON-encoded status. */
function kikiCepAction(action, projectRoot, nonce) {
    function quote(s) {
        return '"'+String(s).replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/\r/g,'\\r').replace(/\n/g,'\\n')+'"';
    }
    function reply(status, detail, path) {
        return '{"status":'+quote(status)+',"detail":'+quote(detail||'')+',"path":'+quote(path||'')+'}';
    }
    var request = null, receipt = null;
    try {
        if (action !== 'export' && action !== 'apply' && action !== 'calculate' && action !== 'language') {
            return reply('error','Unsupported action');
        }
        if (typeof projectRoot !== 'string' || !projectRoot) return reply('error','Missing project root');
        var root = new Folder(projectRoot);
        if (!root.exists) return reply('error','Project folder missing: '+projectRoot);
        if (action === 'calculate') {
            var isWindows = $.os.toLowerCase().indexOf('windows') !== -1;
            var launcher = new File(root.fsName + (isWindows ? '/launch_gui_windows.vbs' : '/launch_gui_macos.command'));
            if (!launcher.exists || !launcher.execute()) return reply('error','Cannot launch Python dashboard: '+launcher.fsName);
            return reply('ok','Python dashboard launched');
        }
        if (action === 'language') {
            var language = new File(root.fsName+'/illustrator/set_language.jsx');
            if (!language.exists) return reply('error','Missing language script');
            $.evalFile(language);
            return reply('ok','Language dialog closed');
        }
        if (!/^[a-f0-9]{32}$/.test(nonce)) return reply('error','Invalid request token');
        var bridgeDir = new Folder(root.fsName+'/workspace/_bridge');
        if (!bridgeDir.exists && !bridgeDir.create()) return reply('error','Cannot create bridge folder');
        request = new File(bridgeDir.fsName+'/request.json');
        if (request.exists) return reply('error','Another pending action. Close the desktop bridge or remove stale workspace/_bridge/request.json after all activity stops.');
        request.encoding='UTF-8';
        if (!request.open('w')) return reply('error','Cannot open request file');
        request.write('{"action":'+quote(action)+',"nonce":'+quote(nonce)+'}');
        request.close();
        var source = new File(root.fsName+'/illustrator/'+(action==='export'?'export_selection.jsx':'apply_layout.jsx'));
        if (!source.exists) return reply('error','Missing JSX: '+source.fsName);
        $.evalFile(source);
        receipt = new File(bridgeDir.fsName+'/'+nonce+'.json');
        if (!receipt.exists) return reply('error','JSX did not confirm operation. Check Illustrator alerts and the selected document.');
        receipt.encoding='UTF-8';
        if (!receipt.open('r')) return reply('error','Cannot read JSX receipt');
        var text = receipt.read(); receipt.close();
        return text;
    } catch (e) {
        return reply('error',e.message||String(e));
    } finally {
        try { if (request && request.exists) request.remove(); } catch(_ignore1) {}
        try { if (receipt && receipt.exists) receipt.remove(); } catch(_ignore2) {}
    }
}

/* Visual selection -> constraints; all geometry remains in Illustrator. */
function kikiCepRules(projectRoot, lockPosition, rotationText) {
    try {
        var extra=new File(projectRoot+'/illustrator/cep_constraints.jsxinc');
        if(!extra.exists)return '{"status":"error","detail":"Missing cep_constraints.jsxinc"}';
        $.evalFile(extra);
        return kikiCepSetSelectedRules(projectRoot,lockPosition,rotationText);
    } catch (e) {
        return '{"status":"error","detail":"CEP adapter failed / Ошибка запуска скрипта ограничений"}';
    }
}
