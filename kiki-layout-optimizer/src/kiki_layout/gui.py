"""Cross-platform Tk/ttk window; Illustrator remains authoritative for editing."""
from __future__ import annotations
import json
import os
import sys
import threading
import queue
import math
from datetime import datetime
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, scrolledtext
import webbrowser
from .gui_jobs import available_exports, project_root, calculate
from .constraints import save_preset, read_preset
from .object_editor import edit_object_rules
from .illustrator_bridge import run_action, IllustratorAutomationError

LABELS = {
 'ru': {
  'cep_hint':'Экспорт и применение выполняются через панель KiKi внутри Illustrator (без COM).',
  'ai_export':'Экспорт из AI','ai_apply':'Применить в AI','ai_language':'Язык Illustrator',
  'ai_running':'Отправляем команду в Illustrator и ожидаем подтверждения…','ai_done':'Illustrator подтвердил операцию.',
  'export_done':'Экспорт подтверждён. Файл: ', 'apply_done':'Раскладка применена в Illustrator.',
  'export_missing':'Illustrator не подтвердил экспорт. Подробности в журнале. Для ручного запуска: Файл → Сценарии → Другой сценарий → export_selection.jsx.',
  'log':'Журнал операций','workspace':'Открыть рабочую папку','log_saved':'Файл журнала',
  'rules':'Ограничения объектов','preset_save':'Сохранить пресет','preset_load':'Загрузить пресет',
  'stage_saving':'Сохранение JSON и SVG',
  'operation':'Технология','kerf':'Ширина пропила, мм','cut_note':'Резка — предварительный режим: только разнос контуров с учётом пропила, без общего реза и управляющей программы.',
  'title':'KiKi Models — оптимизатор пластин','input':'Экспорт из Illustrator',
  'browse':'Выбрать файл…','refresh':'Обновить','mode':'Режим','family':'Группировка одинаковых',
  'flow':'Порядок размещения','travel':'Расчёт переходов','rotation':'Допустимый поворот',
  'gap':'Зазор / перемычка, мм','margins':'Отступы, мм (Л / В / П / Н)', 'calculate':'Рассчитать раскладку',
  'preview':'Открыть SVG','route':'Открыть схему обхода','status':'Выделите объекты в Illustrator и выполните экспорт.',
  'waiting':'Идёт оптимизация…','done':'Готово. Вернитесь в Illustrator → KiKi → Применить раскладку.',
  'nothing':'Сначала сделайте экспорт в Illustrator.','error':'Ошибка расчёта',
  'saved':'Файлы сохранены в папке:','objects':'Объектов','clusters':'Семейств',
  'distance':'Мин. зазор, мм','within':'В пределах краёв','area':'Рамка, мм²',
  'note':'Предпросмотр приблизительный. Проверяйте обводки и составные контуры в Illustrator.',
  'help':'Подсказка','progress':'Ход расчёта','stage_preparing':'Чтение геометрии','stage_placing':'Размещение эмблем',
  'stage_refining':'Выравнивание интервалов','stage_validating':'Проверка расстояний','stage_complete':'Готово',
 },
 'en': {
  'cep_hint':'Export and apply are available from the KiKi CEP panel inside Illustrator (no COM).',
  'ai_export':'Export from AI','ai_apply':'Apply in AI','ai_language':'Illustrator language',
  'ai_running':'Sending operation to Illustrator; waiting for confirmation…','ai_done':'Illustrator confirmed the operation.',
  'export_done':'Export confirmed. File: ', 'apply_done':'Layout applied in Illustrator.',
  'export_missing':'Illustrator did not confirm the export. See log. Manual fallback: File → Scripts → Other Script → export_selection.jsx.',
  'log':'Operation log','workspace':'Open workspace','log_saved':'Log file',
  'rules':'Object rules','preset_save':'Save preset','preset_load':'Load preset',
  'stage_saving':'Saving JSON and SVG',
  'operation':'Process','kerf':'Kerf width, mm','cut_note':'Cutting is a preview-only beta: kerf-safe separation, NO common-line cutting or machine toolpath.',
  'title':'KiKi Models — plate optimizer','input':'Illustrator export',
  'browse':'Browse…','refresh':'Refresh','mode':'Mode','family':'Similar-emblem grouping',
  'flow':'Placement flow','travel':'Travel estimation','rotation':'Allowed rotation',
  'gap':'Gap / material web, mm','margins':'Margins, mm (L / T / R / B)', 'calculate':'Calculate layout',
  'preview':'Open SVG','route':'Open travel preview','status':'Select artwork in Illustrator and export it.',
  'waiting':'Calculating…','done':'Ready. Go back to Illustrator → KiKi → Apply layout.',
  'nothing':'Export geometry from Illustrator first.','error':'Calculation failed',
  'saved':'Files are saved in:','objects':'Objects','clusters':'Families',
  'distance':'Min. gap, mm','within':'Within margins','area':'Bounding area, mm²',
  'note':'Preview is approximate. Verify strokes/compound paths in Illustrator.',
  'help':'Help','progress':'Calculation progress','stage_preparing':'Loading geometry','stage_placing':'Placing artwork',
  'stage_refining':'Refining gaps','stage_validating':'Validating clearances','stage_complete':'Complete',
 }
}


# Each setting documents the actual engine behavior and its trade-offs.
HELP = {
 'ru': {
  'mode': ('Режим оптимизации',
     'Dense — уменьшает занимаемую рамку (ширина × высота).\nUniform — после плотной укладки выравнивает интервалы ближайших соседей.\nOrdered — сохраняет порядок выделения, но не обязательно исходные координаты.\n\nНи один режим не гарантирует глобальный оптимум.'),
  'family': ('Группировка эмблем',
     'off — каждый объект отдельно.\nnamed — одна серия размеров по коду/имени (P10-SYM-007).\nauto — поиск по похожему силуэту; проверьте результат.\nГруппы Illustrator не разбиваются.'),
  'flow': ('Порядок размещения',
     'free — свободная геометрическая укладка.\nrows — заполнять пластину преимущественно слева направо строками.\ncolumns — преимущественно сверху вниз по столбцам.\n\nЭто способ РАСКЛАДКИ, а не порядок движения лазерной головки.'),
  'travel': ('Расчёт переходов лазера',
     'nearest — следующий ближайший центр эмблемы.\nrows/columns — обход по строкам или столбцам.\nsource — исходный порядок Illustrator.\n\nПока это приблизительная длина холостых переходов между центрами. Не маршрут гравировки и не оценка времени обработки.'),
  'rotation': ('Поворот объектов',
     '0 — не поворачивать. 0,180 — допускается переворот. 0,90,180,270 — все четыре угла.\n\nВНИМАНИЕ: для стрелок, орденских и других ориентированных знаков обычно выбирайте 0. Поворот может быть геометрически допустим, но семантически неверен.'),
 },
 'en': {
  'mode': ('Optimization objective',
     'Dense: minimize layout bounding area.\nUniform: attempt to equalize nearest-neighbor gaps after packing.\nOrdered: retain the selection order, not exact original positions.\n\nNo mode guarantees a global optimum.'),
  'family': ('Similar-emblem families',
     'off: independent objects.\nnamed: cluster sizes by name/code (P10-SYM-007).\nauto: match similar silhouettes; review the results.\nIllustrator groups remain intact.'),
  'flow': ('Placement direction',
     'free: unrestricted geometric nesting.\nrows: arrange mostly left-to-right in rows.\ncolumns: arrange top-to-bottom in columns.\n\nThis is a LAYOUT preference, not a physical laser path.'),
  'travel': ('Laser-off jump estimates',
     'nearest: move to nearest emblem center.\nrows/columns: row or column scan order.\nsource: original Illustrator ordering.\n\nOnly a center-to-center proxy; NOT a machine toolpath or runtime prediction.'),
  'rotation': ('Allowed rotation',
     '0: never rotate; 0,180: permit inversion; 0,90,180,270: all quarter-turns.\n\nCAUTION: use 0 for arrows, insignia and direction-sensitive artwork unless changing orientation is intentional.'),
 }
}


def illustrator_language() -> str:
    # Illustrator stores preference in Folder.userData/KiKiModels/language.txt.
    # Windows %APPDATA%; macOS ~/Library/Application Support. Independent from UI.
    base = Path(os.environ.get('APPDATA','')) if sys.platform=='win32' else Path.home()/'Library'/'Application Support'
    try:
        value=(base/'KiKiModels'/'language.txt').read_text(encoding='utf-8-sig').strip().lower()
        return value if value in LABELS else 'ru'
    except (OSError, UnicodeError):
        return 'ru'


class LayoutUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang=tk.StringVar(value=illustrator_language())
        self.geometry('1080x840')
        self.minsize(900,700)
        self.option_add('*Font','Arial 10')
        self.current_input=tk.StringVar()
        self.mode=tk.StringVar(value='uniform')
        self.operation=tk.StringVar(value='engrave')
        self.kerf=tk.StringVar(value='0.15')
        self.family=tk.StringVar(value='named')
        self.flow=tk.StringVar(value='free')
        self.travel=tk.StringVar(value='nearest')
        self.rotation=tk.StringVar(value='0')
        self.gap=tk.StringVar(value='0.8')
        self.margins=[tk.StringVar(value='2') for _ in range(4)]
        self.status=tk.StringVar()
        self.report=tk.StringVar()
        self.latest_result=None
        self.preview_shape=None
        self.busy=False
        self.events=queue.Queue()
        self._last_progress_stage=''
        self.log_path=project_root()/'workspace'/'optimizer.log'
        self.progress_value=tk.DoubleVar(value=0)
        self.progress_description=tk.StringVar(value='')
        self._icon_img=None
        self._build()
        self.after(50, self._present_window)
        self.after(80, self._poll_events)
        self._log('KiKi GUI started')
        self.refresh_inputs()
        self.operation.trace_add("write", lambda *_:self._update_operation())

    def tr(self, key): return LABELS[self.lang.get()][key]

    def _update_operation(self):
        cut=self.operation.get()=='cut'
        self.kerf_entry.configure(state='normal' if cut else 'disabled')
        self.cut_note.configure(text=self.tr('cut_note') if cut else '')

    def _log(self, message, level='INFO'):
        """Visible event history + local UTF-8 log, no network transmission."""
        line=f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [{level}] {message}"
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open('a',encoding='utf-8') as fp:
                fp.write(line+'\n')
        except OSError:
            pass  # UI should still function in a read-only folder
        if hasattr(self,'log_view'):
            self.log_view.configure(state='normal')
            self.log_view.insert('end',line+'\n')
            self.log_view.see('end')
            self.log_view.configure(state='disabled')

    def _poll_events(self):
        for _ in range(120):
            try:event=self.events.get_nowait()
            except queue.Empty:break
            kind=event[0]
            if kind=='ai_result':
                _,action,error,receipt=event
                self._action_completed(action,error,receipt)
            elif kind=='progress':
                _,pct,stage,done,total=event
                self._progress(pct,stage,done,total)
            elif kind=='calculated':
                _,path,result,geometry,error=event
                self._calculated(path,result,geometry,error)
        self.after(80,self._poll_events)

    def run_illustrator_action(self, action):
        if self.busy:return
        self.busy=True
        self.status.set(self.tr('ai_running'))
        self._log('Illustrator action started: '+action)
        # Hide GUI so native Illustrator dialogs are not covered by a topmost window.
        self.iconify()
        for button in self.ai_buttons:button.configure(state='disabled')
        def work():
            try:
                receipt=run_action(action,verify=action in ('export','apply'))
            except Exception as exc:
                self.events.put(('ai_result',action,str(exc),None))
            else:
                self.events.put(('ai_result',action,None,receipt))
        threading.Thread(target=work,daemon=True).start()

    def _action_completed(self, action, error, receipt=None):
        self.deiconify()
        self._present_window()
        self.busy=False
        for button in self.ai_buttons:button.configure(state='normal')
        if error:
            self._log(f'Illustrator {action}: {error}',level='ERROR')
            fallback=self.tr('export_missing') if action=='export' else error
            self.status.set(fallback)
            messagebox.showerror(self.tr('error'),error+'\n\n'+fallback)
        elif receipt and receipt.get('status')=='cancelled':
            self._log('Illustrator '+action+': cancelled')
            self.status.set('Cancelled / Отменено')
        else:
            self._log(f'Illustrator {action} confirmed'+(' ['+str(receipt.get('path'))+']' if receipt and receipt.get('path') else ''))
            self.status.set(self.tr('ai_done'))
            if action=='export':
                if receipt and receipt.get('path'):
                    self.current_input.set(receipt['path'])
                self.preview_shape=None
                self.report.set('')
                self.canvas.delete('all')
                self.refresh_inputs()
                self.status.set(self.tr('export_done')+self.current_input.get())
            elif action=='apply':
                self.status.set(self.tr('apply_done'))
            elif action=='language':
                self.lang.set(illustrator_language())

    def _present_window(self):
        # Windows can keep Illustrator foreground while a child Python process starts.
        # Topmost is TEMPORARY: don't pin GUI above the user's other windows forever.
        self.update_idletasks()
        self.lift()
        try:
            self.attributes('-topmost', True)
            self.focus_force()
            self.after(1100, lambda: self.attributes('-topmost', False))
        except tk.TclError:
            pass

    def show_help(self, key):
        title,description=HELP[self.lang.get()][key]
        win=tk.Toplevel(self)
        win.title('KiKi Models — '+title)
        win.geometry('820x425' if key=='mode' else ('690x288' if key=='family' else '780x335'))
        win.transient(self)
        win.resizable(True,True)
        ttk.Label(win,text=title,font=('Arial',12,'bold')).pack(anchor='w',padx=16,pady=(14,9))
        ttk.Label(win,text=description,justify='left',wraplength=(650 if key=='family' else 750)).pack(fill='x',padx=16)
        if key in ('mode','flow','travel','rotation','family'):
            diagram=tk.Canvas(win,height=(108 if key=='family' else 155),bg='white',highlightthickness=1,highlightbackground='#ddd')
            diagram.pack(fill='x',padx=16,pady=8)
            self._help_diagram(diagram,key,self.lang.get())
        ttk.Button(win,text='OK',command=win.destroy).pack(anchor='e',padx=16,pady=7)

    @staticmethod
    def _help_diagram(c,key,locale="ru"):
        """Offline diagrams use intentionally asymmetric shapes and before/after comparisons."""
        def sq(x,y,size=13,color='#8baabf'):
            c.create_rectangle(x,y,x+size,y+size,fill=color,outline='#506b83')
        def circle(x,y,size=11,color='#b3c8a2'):
            c.create_oval(x,y,x+size,y+size,fill=color,outline='#58734a')
        def tri(x,y,size=15,color='#ccae8e'):
            c.create_polygon(x,y+size,x+size/2,y,x+size,y+size,fill=color,outline='#946a4a')
        if key=='family':
            # Three simple, deliberately different examples: independent items,
            # named size-series, and inferred silhouette match with a warning.
            ru=locale=='ru'
            panels=[('off', 'Без групп' if ru else 'Separate'),
                    ('named','Серия по коду' if ru else 'Same ID / name'),
                    ('auto','Похожий контур (?)' if ru else 'Similar shape (?)')]
            for j,(key_name,caption) in enumerate(panels):
                ox=12+219*j
                c.create_rectangle(ox,7,ox+207,98,outline='#ddd')
                c.create_text(ox+103,19,text=key_name,font=('Arial',10,'bold'),fill='#23394a')
                c.create_text(ox+103,88,text=caption,font=('Arial',9),fill='#586674')
            # Off: different silhouettes are unrelated and remain in place.
            c.create_oval(37,39,56,58,fill='#96b7c8',outline='#537589')
            c.create_rectangle(91,37,115,61,fill='#c3a67b',outline='#8f714e')
            c.create_polygon(153,62,168,37,183,62,fill='#abbf9b',outline='#5f8152')
            # Named: one motif at 3, 5.5 and 9 mm becomes an ordered family.
            for cx,sz in [(278,11),(324,18),(378,27)]:
                c.create_polygon(cx-sz/2,66,cx,66-sz,cx+sz/2,66,
                                 fill='#88abc7',outline='#3f6f96',width=1)
            c.create_line(278,74,378,74,fill='#8999a5',dash=(3,2))
            # Auto: similar silhouettes are recognized with uncertainty; color
            # encodes a suggested family, the question mark an imperfect match.
            for cx,sz in [(495,12),(552,21),(613,27)]:
                c.create_polygon(cx-sz/2,66,cx,66-sz,cx+sz/2,66,
                                 fill='#a9c4ac',outline='#598362')
            c.create_oval(586,38,607,59,outline='#b76c2b',width=2,dash=(2,2))
            c.create_text(597,33,text='?',font=('Arial',10,'bold'),fill='#b76c2b')
            return
        if key=='mode':
            samples=(('Dense',[(6,29),(36,4),(36,36)],[(0,0),(14,0),(0,14)]),
                     ('Uniform',[(0,26),(30,4),(45,35)],[(0,0),(33,0),(0,33)]),
                     ('Ordered',[(31,31),(0,0),(39,3)],[(0,0),(22,0),(44,0)]))
            for idx,(name,before,after) in enumerate(samples):
                x=11+idx*250
                c.create_rectangle(x,5,x+239,143,outline='#bbb')
                c.create_text(x+119,16,text=name,font=('Arial',10,'bold'))
                c.create_text(x+43,33,text='До / Before',font=('Arial',8),fill='#666')
                c.create_text(x+181,33,text='После / After',font=('Arial',8),fill='#666')
                c.create_line(x+117,52,x+138,52,arrow=tk.LAST,fill='#777',width=2)
                shape_funcs=(sq,circle,tri)
                for j,(px,py) in enumerate(before):shape_funcs[j](x+8+px,56+py)
                for j,(px,py) in enumerate(after):shape_funcs[j](x+147+px,66+py)
                c.create_rectangle(x+141,56,x+231,121,outline='#ddd',dash=(2,2))
                if idx==1:
                    c.create_line(x+165,62,x+190,62,fill='#bf672c',arrow=tk.BOTH)
                    c.create_line(x+144,83,x+144,106,fill='#bf672c',arrow=tk.BOTH)
                if idx==2:
                    for j,(px,py) in enumerate(after):
                        c.create_text(x+155+px,111,text=str(j+1),font=('Arial',8),fill='#555')
            return
        if key=='rotation':
            # An asymmetrical arrow rotates visually, not only the printed label.
            base=[(-10,12),(-10,-5),(-17,-5),(0,-28),(17,-5),(10,-5),(10,12)]
            for i,angle in enumerate((0,90,180,270)):
                cx=88+i*185;cy=82
                c.create_rectangle(cx-56,30,cx+56,130,outline='#ddd')
                rad=math.radians(angle)
                pts=[]
                for x,y in base:
                    rx=x*math.cos(rad)-y*math.sin(rad)
                    ry=x*math.sin(rad)+y*math.cos(rad)
                    pts.extend([cx+rx,cy+ry])
                c.create_polygon(*pts,fill='#83a4bf',outline='#3b6482',width=2)
                # Dot marks the object's top-left corner, proving inversion.
                dotx=(-6)*math.cos(rad)-(7)*math.sin(rad)
                doty=(-6)*math.sin(rad)+(7)*math.cos(rad)
                c.create_oval(cx+dotx-3,cy+doty-3,cx+dotx+3,cy+doty+3,fill='#c35337',outline='')
                c.create_text(cx,142,text=str(angle)+'°',font=('Arial',10,'bold'))
            return
        coords=([(80,45),(160,45),(240,45),(80,100),(160,100),(240,100)] if key=='flow'
                else [(80,40),(160,100),(250,40),(340,100)])
        for x,y in coords:sq(x,y,20)
        if key=='travel':
            for (x,y),(nx,ny) in zip(coords,coords[1:]):
                c.create_line(x+10,y+10,nx+10,ny+10,arrow=tk.LAST,fill='#ba6b34',width=2)

    def _build(self):
        self.title(self.tr('title'))
        outer=ttk.Frame(self,padding=12);outer.pack(fill='both',expand=True)
        header=ttk.Frame(outer);header.pack(fill='x')
        icon_path=project_root()/'assets'/'kiki-icon.png'
        if icon_path.is_file():
            try:
                self._icon_img=tk.PhotoImage(file=str(icon_path)).subsample(3,3)
                self.iconphoto(True,self._icon_img)
                ttk.Label(header,image=self._icon_img).pack(side='left',padx=(0,8))
            except tk.TclError:pass
        ttk.Label(header,text='KiKi Models',font=('Arial',16,'bold')).pack(side='left')
        ttk.Combobox(header,textvariable=self.lang,values=['ru','en'],state='readonly',width=5).pack(side='right')
        self.lang.trace_add('write', lambda *_:self._translate())
        ai_actions=ttk.Frame(outer);ai_actions.pack(fill='x',pady=(9,0))
        # COM automation is unreliable on Illustrator 30.6 Windows; CEP+JSX
        # is the tested transport. Don't advertise buttons that hang/fail.
        self.ai_buttons=[]
        self.cep_hint=ttk.Label(ai_actions,text=self.tr('cep_hint'),foreground='#355e76')
        self.cep_hint.pack(anchor='w')
        row=ttk.Frame(outer);row.pack(fill='x',pady=(8,6))
        self.filelabel=ttk.Label(row,text=self.tr('input'));self.filelabel.pack(anchor='w')
        filerow=ttk.Frame(row);filerow.pack(fill='x',pady=5)
        self.files=ttk.Combobox(filerow,textvariable=self.current_input,state='normal')
        self.files.pack(side='left',fill='x',expand=True)
        self.browse_button=ttk.Button(filerow,text=self.tr('browse'),command=self.browse)
        self.browse_button.pack(side='left',padx=5)
        self.refresh_button=ttk.Button(filerow,text=self.tr('refresh'),command=self.refresh_inputs)
        self.refresh_button.pack(side='left')

        processrow=ttk.Frame(outer);processrow.pack(fill='x',pady=(0,7))
        self.processlabel=ttk.Label(processrow,text=self.tr('operation'))
        self.processlabel.pack(side='left',padx=(0,8))
        ttk.Combobox(processrow,textvariable=self.operation,values=['engrave','cut'],state='readonly',width=14).pack(side='left')
        self.kerflabel=ttk.Label(processrow,text=self.tr('kerf'))
        self.kerflabel.pack(side='left',padx=(20,6))
        self.kerf_entry=ttk.Entry(processrow,textvariable=self.kerf,width=8)
        self.kerf_entry.pack(side='left')
        self.cut_note=ttk.Label(processrow,text='',foreground='#934a28',wraplength=380)
        self.cut_note.pack(side='left',padx=10)
        self._update_operation()
        panel=ttk.LabelFrame(outer,text='Layout / Раскладка',padding=10);panel.pack(fill='x')
        controls=[('mode',self.mode,['uniform','dense','ordered']),
                  ('family',self.family,['named','auto','off']),
                  ('flow',self.flow,['free','rows','columns']),
                  ('travel',self.travel,['nearest','rows','columns','source']),
                  ('rotation',self.rotation,['0','0,180','0,90,180,270'])]
        self.control_labels={}
        for i,(key,var,vals) in enumerate(controls):
            r,c=divmod(i,3)
            frame=ttk.Frame(panel);frame.grid(row=r*2,column=c,sticky='ew',padx=8,pady=2)
            title_row=ttk.Frame(frame);title_row.pack(fill='x')
            label=ttk.Label(title_row,text=self.tr(key));label.pack(side='left')
            help_btn=ttk.Button(title_row,text='?',width=2,command=lambda k=key:self.show_help(k))
            help_btn.pack(side='right')
            self.control_labels[key]=label
            ttk.Combobox(frame,values=vals,textvariable=var,state='readonly',width=21).pack(fill='x')
        for i in range(3):panel.columnconfigure(i,weight=1)
        gapframe=ttk.Frame(panel);gapframe.grid(row=4,column=0,sticky='ew',padx=8,pady=(8,2))
        self.gaplabel=ttk.Label(gapframe,text=self.tr('gap'));self.gaplabel.pack(anchor='w')
        ttk.Entry(gapframe,textvariable=self.gap).pack(fill='x')
        marframe=ttk.Frame(panel);marframe.grid(row=4,column=1,columnspan=2,sticky='ew',padx=8,pady=(8,2))
        self.marginlabel=ttk.Label(marframe,text=self.tr('margins'));self.marginlabel.pack(anchor='w')
        sub=ttk.Frame(marframe);sub.pack(fill='x')
        for i,var in enumerate(self.margins):ttk.Entry(sub,textvariable=var,width=9).pack(side='left',fill='x',expand=True,padx=(0,4))

        actions=ttk.Frame(outer);actions.pack(fill='x',pady=(12,4))
        self.run_button=ttk.Button(actions,text=self.tr('calculate'),command=self.start_calculation)
        self.run_button.pack(side='left')
        self.rules_button=ttk.Button(actions,text=self.tr('rules'),command=self.show_object_rules)
        self.rules_button.pack(side='left',padx=(8,0))
        self.preset_save_button=ttk.Button(actions,text=self.tr('preset_save'),command=self.save_profile)
        self.preset_save_button.pack(side='left',padx=(8,0))
        self.preset_load_button=ttk.Button(actions,text=self.tr('preset_load'),command=self.load_profile)
        self.preset_load_button.pack(side='left',padx=(5,0))
        self.preview_button=ttk.Button(actions,text=self.tr('preview'),command=lambda:self.open_file('preview_test.svg'))
        self.preview_button.pack(side='left',padx=6)
        self.route_button=ttk.Button(actions,text=self.tr('route'),command=lambda:self.open_file('route_test.svg'))
        self.route_button.pack(side='left')
        ttk.Label(actions,text='  PDF / SVG / JSON: workspace',foreground='#666').pack(side='right')
        progress_row=ttk.Frame(outer);progress_row.pack(fill='x',pady=(8,0))
        ttk.Label(progress_row,textvariable=self.progress_description).pack(side='left')
        self.progress_bar=ttk.Progressbar(progress_row,maximum=100,variable=self.progress_value,mode='determinate')
        self.progress_bar.pack(side='right',fill='x',expand=True,padx=(12,0))
        ttk.Label(outer,textvariable=self.status,wraplength=930).pack(fill='x',pady=(6,4))
        ttk.Label(outer,textvariable=self.report,wraplength=940).pack(fill='x',pady=(0,6))
        log_header=ttk.Frame(outer);log_header.pack(fill='x',pady=(3,2))
        self.log_label=ttk.Label(log_header,text=self.tr('log'))
        self.log_label.pack(side='left')
        self.workspace_button=ttk.Button(log_header,text=self.tr('workspace'),command=self.open_workspace)
        self.workspace_button.pack(side='right')
        self.log_view=scrolledtext.ScrolledText(outer,height=5,wrap='word',font=('Consolas',9),state='disabled')
        self.log_view.pack(fill='x',pady=(0,5))
        self.canvas=tk.Canvas(outer,bg='white',highlightbackground='#bbb',highlightthickness=1)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>', lambda _e:self.paint_preview())
        self.notelabel=ttk.Label(outer,text=self.tr('note'))
        self.notelabel.pack(fill='x',pady=(8,0))
        self.status.set(self.tr('status'))

    def _translate(self):
        self.title(self.tr('title'))
        for k,label in self.control_labels.items():label.configure(text=self.tr(k))
        self.filelabel.configure(text=self.tr('input'))
        self.gaplabel.configure(text=self.tr('gap'))
        self.marginlabel.configure(text=self.tr('margins'))
        self.run_button.configure(text=self.tr('calculate'))
        self.rules_button.configure(text=self.tr('rules'))
        self.preset_save_button.configure(text=self.tr('preset_save'))
        self.preset_load_button.configure(text=self.tr('preset_load'))
        self.preview_button.configure(text=self.tr('preview'))
        self.route_button.configure(text=self.tr('route'))
        self.refresh_button.configure(text=self.tr('refresh'))
        self.browse_button.configure(text=self.tr('browse'))
        self.notelabel.configure(text=self.tr('note'))
        self.log_label.configure(text=self.tr('log'))
        self.workspace_button.configure(text=self.tr('workspace'))
        self.cep_hint.configure(text=self.tr('cep_hint'))
        for button,key in zip(self.ai_buttons,('ai_export','ai_apply','ai_language')):
            button.configure(text=self.tr(key))
        self.processlabel.configure(text=self.tr('operation'))
        self.kerflabel.configure(text=self.tr('kerf'))
        self._update_operation()

    def refresh_inputs(self):
        exports=available_exports()
        names=[str(p) for p in exports]
        self.files.configure(values=names)
        if names and (self.current_input.get() not in names):
            self.current_input.set(names[0])
        elif not names and not self.current_input.get():
            self.status.set(self.tr('nothing'))

    def browse(self):
        selected=filedialog.askopenfilename(title=self.tr('input'),filetypes=[('KiKi JSON','*.json')])
        if selected:self.current_input.set(selected)

    def _options(self):
        def number(v):
            x=float(v.strip().replace(',','.'))
            if not 0<=x<=100:raise ValueError('Expected a nonnegative number <= 100 mm')
            return x
        return dict(mode=self.mode.get(), gap=number(self.gap.get()),margin=0,
          margin_left=number(self.margins[0].get()),margin_top=number(self.margins[1].get()),
          margin_right=number(self.margins[2].get()),margin_bottom=number(self.margins[3].get()),
          rotations=tuple(int(x) for x in self.rotation.get().split(',')),
          families=self.family.get(),flow=self.flow.get(),travel_order=self.travel.get(),
          lang=self.lang.get(),operation=self.operation.get(),
          kerf_mm=number(self.kerf.get()) if self.operation.get()=='cut' else 0)

    def show_object_rules(self):
        path=Path(self.current_input.get())
        if not path.is_file():
            messagebox.showwarning(self.tr('error'),self.tr('nothing'));return
        try:edit_object_rules(self,path,self.lang.get())
        except Exception as exc:messagebox.showerror(self.tr('error'),str(exc))

    def save_profile(self):
        try: opts=self._options()
        except Exception as exc:messagebox.showerror(self.tr('error'),str(exc));return
        folder=project_root()/'presets'
        folder.mkdir(parents=True,exist_ok=True)
        file=filedialog.asksaveasfilename(initialdir=str(folder),defaultextension='.json',
            filetypes=[('KiKi preset','*.json')],title=self.tr('preset_save'))
        if file:
            try:save_preset(Path(file),opts)
            except Exception as exc:messagebox.showerror(self.tr('error'),str(exc))
            else:self._log('Saved preset: '+str(file))

    def load_profile(self):
        folder=project_root()/'presets'
        file=filedialog.askopenfilename(initialdir=str(folder),filetypes=[('KiKi preset','*.json')],
            title=self.tr('preset_load'))
        if not file:return
        try:profile=read_preset(Path(file))
        except Exception as exc:messagebox.showerror(self.tr('error'),str(exc));return
        for key,var in (('mode',self.mode),('families',self.family),('flow',self.flow),
                        ('travel_order',self.travel),('operation',self.operation),
                        ('gap',self.gap),('kerf_mm',self.kerf)):
            if key in profile:var.set(str(profile[key]))
        if 'rotations' in profile:self.rotation.set(','.join(map(str,profile['rotations'])))
        for side,var in zip(('left','top','right','bottom'),self.margins):
            key='margin_'+side
            if key in profile:var.set(str(profile[key]))
        self._log('Loaded preset: '+str(file))

    def start_calculation(self):
        if self.busy:return
        path=Path(self.current_input.get())
        if not path.is_file():messagebox.showwarning(self.tr('error'),self.tr('nothing'));return
        try:opts=self._options()
        except ValueError as e:messagebox.showerror(self.tr('error'),str(e));return
        self.busy=True;self.run_button.configure(state='disabled');self.rules_button.configure(state='disabled')
        for button in self.ai_buttons:button.configure(state='disabled')
        self.progress_value.set(0)
        self.progress_description.set(self.tr('waiting'))
        self.status.set(self.tr('waiting'))
        self._log('Calculation started | '+str(path)+' | '+str(opts))
        self._last_progress_stage=''
        progress_marker=[-1]
        def progress(stage,done,total):
            proportion=min(1.0,done/max(total,1))
            starts={'preparing':(0,3),'placing':(3,80),'refining':(80,95),
                    'validating':(95,99),'complete':(99,99)}
            lo,hi=starts.get(stage,(0,0))
            pct=int(lo+(hi-lo)*proportion)
            if pct == progress_marker[0]:return
            progress_marker[0]=pct
            self.events.put(('progress',pct,stage,done,total))
        def work():
            try:result,geometry=calculate(path,opts,progress=progress)
            except Exception as ex:
                self.events.put(('calculated',path,None,None,str(ex)))
            else:
                self.events.put(('calculated',path,result,geometry,None))
        threading.Thread(target=work,daemon=True).start()

    def _progress(self,pct,stage,done,total):
        self.progress_value.set(pct)
        if stage != self._last_progress_stage:
            self._last_progress_stage=stage
            self._log(f'Calculation stage: {stage} ({done}/{total})')
        description=self.tr('stage_'+stage)
        if stage in ('placing','refining'):
            description+=' ('+str(done)+'/'+str(total)+')'
        self.progress_description.set(description+' — '+str(pct)+'%')

    def _calculated(self,path,result,geometry,error):
        self.busy=False;self.run_button.configure(state='normal');self.rules_button.configure(state='normal')
        for button in self.ai_buttons:button.configure(state='normal')
        if error:
            self._log('Calculation error: '+error,level='ERROR')
            self.progress_description.set(self.tr('error'))
            self.status.set(self.tr('error')+': '+error)
            messagebox.showerror(self.tr('error'),error)
            return
        self._progress(100,'complete',1,1)
        self._log('Calculation completed; files saved: '+str(Path(path).parent))
        self.latest_result=Path(path).parent;self.preview_shape=(result,geometry)
        r=result['report'];self.report.set(
            f"{self.tr('objects')}: {r['object_count']}  |  {self.tr('clusters')}: {r['cluster_count']}  |  "
            f"{self.tr('distance')}: {r['min_clearance_mm']:.3f}  |  "
            f"{self.tr('area')}: {r['occupied_bbox_mm2']:.1f}  |  "
            f"{self.tr('within')}: {'✓' if r['within_margins'] else '✗'}")
        self.status.set(self.tr('done')+' '+self.tr('saved')+' '+str(self.latest_result))
        self.paint_preview()

    def open_workspace(self):
        path=(self.latest_result or (Path(self.current_input.get()).parent if self.current_input.get() else project_root()/'workspace'))
        path.mkdir(parents=True,exist_ok=True)
        self._log('Open workspace: '+str(path))
        if sys.platform=='win32':os.startfile(str(path))
        elif sys.platform=='darwin':
            import subprocess
            subprocess.Popen(['open',str(path)])
        else:
            webbrowser.open(path.resolve().as_uri())

    def open_file(self, filename):
        path=(self.latest_result or Path(self.current_input.get()).parent)/filename
        if path.exists():webbrowser.open(path.resolve().as_uri())
        else:messagebox.showinfo(self.tr('nothing'),self.tr('calculate'))

    def paint_preview(self):
        if not self.preview_shape:return
        result,geometry=self.preview_shape
        c=self.canvas;c.delete('all')
        width,height=result['artboard']['width_mm'],result['artboard']['height_mm']
        cw=max(c.winfo_width(),300);ch=max(c.winfo_height(),180)
        scale=min((cw-30)/width,(ch-20)/height)
        ox=(cw-width*scale)/2;oy=(ch-height*scale)/2
        tx=lambda coords:[val*scale+(ox if i%2==0 else oy) for i,val in enumerate(coords)]
        c.create_rectangle(ox,oy,ox+width*scale,oy+height*scale,outline='#aaa',fill='white')
        margins=result['settings'].get('margins_mm',{})
        l,t,r,b=(margins.get(k,0) for k in ('left','top','right','bottom'))
        c.create_rectangle(ox+l*scale,oy+t*scale,ox+(width-r)*scale,oy+(height-b)*scale,outline='#bb8888',dash=(2,2))
        colors=['#88add0','#caa08a','#85b79d','#b7a1c9','#bdbe81','#d99eb1']
        for i,shape in enumerate(geometry.values()):
            polys=shape.geoms if hasattr(shape,'geoms') else [shape]
            for p in polys:
                if not hasattr(p,'exterior'):continue
                pts=list(p.exterior.coords)
                if len(pts)<3:continue
                if len(pts)>220:pts=pts[::max(1,len(pts)//200)]
                flat=[v for point in pts for v in point]
                c.create_polygon(*tx(flat),fill=colors[i%len(colors)],outline='#333',width=0.5)
                for interior in p.interiors:
                    pts=list(interior.coords)
                    if len(pts)>220:pts=pts[::max(1,len(pts)//200)]
                    if len(pts)>=3:c.create_polygon(*tx([v for point in pts for v in point]),fill='white',outline='white')


def main():
    LayoutUI().mainloop()

if __name__=='__main__':main()
