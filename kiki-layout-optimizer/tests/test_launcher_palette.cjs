/* v0.4.1: the JSX should launch a persistent EXTERNAL GUI without a ScriptUI palette. */
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(path.join(__dirname,'../illustrator/kiki_launcher.jsx'),'utf8').replace(/^#target.*$/mg,'');
function run(os){
 const executed=[],dialogs=[],created=[];
 function File(value){this.fsName=String(value);this.exists=true;this.parent={fsName:'/repo/illustrator',parent:{fsName:'/repo'}}; created.push(this.fsName);}
 File.prototype.execute=function(){executed.push(this.fsName);return true;};
 const ctx={File,$:{fileName:'/repo/illustrator/kiki_launcher.jsx',os},alert:s=>dialogs.push(s),Error};
 vm.runInNewContext(source,ctx);
 assert.strictEqual(executed.length,1);
 assert.strictEqual(dialogs.length,0);
 return executed[0];
}
assert(run('Windows 11').endsWith('launch_gui_windows.vbs'));
assert(run('Macintosh').endsWith('launch_gui_macos.command'));
console.log('PASS launcher opens native persistent desktop GUI without ScriptUI palette');
