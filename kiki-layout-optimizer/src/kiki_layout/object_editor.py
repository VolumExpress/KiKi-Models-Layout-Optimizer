"""Secondary bulk editor. Prefer CEP visual selection for day-to-day use.

This window is intentionally a searchable table rather than a list of opaque
'item-13' labels. Artwork changes are never performed by the editor.
"""
from __future__ import annotations
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from .constraints import read_constraints, validate_constraints, save_constraints

_SYMBOL = re.compile(r'(P\d+-SYM-\d+)', re.IGNORECASE)
_SIZE = re.compile(r'(\d+(?:\.\d+)?)mm', re.IGNORECASE)


def human_label(item: dict, ru=True) -> tuple[str, str]:
    """Provide useful identity even when Illustrator has no human-readable name."""
    name = item.get('name', '')
    symbol = _SYMBOL.search(name)
    size = _SIZE.search(name)
    bounds = item.get('source_bounds_pt', [])
    dimensions = ''
    if len(bounds) == 4:
        w, h = abs(bounds[2] - bounds[0]) * 25.4 / 72, abs(bounds[1] - bounds[3]) * 25.4 / 72
        dimensions = f'{w:.1f} × {h:.1f} мм' if ru else f'{w:.1f} × {h:.1f} mm'
    if symbol:
        label = symbol.group(1).upper()
        if size:
            label += ' · ' + size.group(1).replace('.', ',') + (' мм' if ru else ' mm')
    elif name and not re.fullmatch(r'item-\d+', name):
        label = name
    else:
        label = ('Без имени' if ru else 'Unnamed') + ' · #' + str(item['id'])
    return label, dimensions


def edit_object_rules(parent, input_path: Path, lang='ru'):
    data=json.loads(Path(input_path).read_text(encoding='utf-8-sig'))
    existing=read_constraints(input_path)
    validate_constraints(data, existing)
    byid={str(obj['id']):obj for obj in data['objects']}
    rules={key:dict(value) for key,value in existing.get('items', {}).items()} if existing else {}
    ru=lang=='ru'
    title='Ограничения объектов' if ru else 'Object constraints'
    win=tk.Toplevel(parent)
    win.title(title)
    win.geometry('920x570');win.minsize(700,440)
    win.transient(parent)
    win.grab_set()
    ttk.Label(win,text=('Удобнее выбирать эмблемы прямо на пластине через CEP → «Сохранить ограничения». Здесь — массовая настройка с поиском.'
                         if ru else 'For visual selection use CEP → Save rules. This table supports bulk editing and search.'),
              wraplength=880).pack(fill='x',padx=12,pady=(12,8))
    top=ttk.Frame(win);top.pack(fill='x',padx=12,pady=(0,6))
    ttk.Label(top,text='Поиск:' if ru else 'Search:').pack(side='left')
    search=tk.StringVar()
    entry=ttk.Entry(top,textvariable=search)
    entry.pack(side='left',fill='x',expand=True,padx=7)
    ttk.Button(top,text='Очистить' if ru else 'Clear',command=lambda: search.set('')).pack(side='right')
    frame=ttk.Frame(win);frame.pack(fill='both',expand=True,padx=12)
    columns=('code','size','position','rotations')
    table=ttk.Treeview(frame,columns=columns,show='tree headings',selectmode='extended')
    table.heading('#0',text='№');table.column('#0',width=52,stretch=False)
    for key,heading,width in [('code','Эмблема / код' if ru else 'Emblem / code',350),
                               ('size','Габариты' if ru else 'Dimensions',130),
                               ('position','Положение' if ru else 'Position',120),
                               ('rotations','Повороты' if ru else 'Rotations',150)]:
        table.heading(key,text=heading);table.column(key,width=width,stretch=key=='code')
    scroll=ttk.Scrollbar(frame,orient='vertical',command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y');table.pack(side='left',fill='both',expand=True)

    def row_values(oid):
        rule=rules.get(oid,{})
        title,dim=human_label(byid[oid],ru)
        locked=('🔒 Закреплён' if ru else '🔒 Locked') if rule.get('lock_position') else ('Свободен' if ru else 'Free')
        rot=rule.get('rotations')
        rotation=','.join(map(str,rot))+'°' if rot is not None else ('Общие' if ru else 'Global')
        return (title,dim,locked,rotation)

    def refresh(*_):
        selected=set(table.selection()); q=search.get().lower().strip()
        table.delete(*table.get_children())
        for obj in data['objects']:
            oid=str(obj['id']);label,dim=human_label(obj,ru)
            text=' '.join((label,dim,str(oid),str(obj.get('name','')))).lower()
            if q and q not in text:continue
            table.insert('', 'end',iid=oid,text='#'+oid,values=row_values(oid))
        remaining=[oid for oid in selected if table.exists(oid)]
        if remaining:table.selection_set(remaining)
        refresh_count()

    count=tk.StringVar()
    def refresh_count(*_):
        count.set((f'Выбрано: {len(table.selection())}' if ru else f'Selected: {len(table.selection())}') )

    search.trace_add('write',refresh)
    table.bind('<<TreeviewSelect>>',lambda *_: (refresh_count(),show_selection()))
    ctrl=ttk.Frame(win);ctrl.pack(fill='x',padx=12,pady=(9,2))
    ttk.Label(ctrl,textvariable=count).pack(side='left',padx=(0,12))
    fixed=tk.BooleanVar(value=False)
    ttk.Checkbutton(ctrl,text='Зафиксировать положение' if ru else 'Lock position',variable=fixed).pack(side='left',padx=(0,14))
    ttk.Label(ctrl,text='Разрешить повороты:' if ru else 'Allowed rotations:').pack(side='left')
    rotate=tk.StringVar(value='global')
    ttk.Combobox(ctrl,textvariable=rotate,values=['global','0','0,180','0,90,180,270'],width=18,state='readonly').pack(side='left',padx=8)

    def show_selection():
        ids=table.selection()
        if len(ids)==1:
            rule=rules.get(ids[0],{})
            fixed.set(bool(rule.get('lock_position')))
            angles=rule.get('rotations')
            rotate.set(','.join(map(str,angles)) if angles else 'global')

    def apply_choice():
        chosen=tuple(table.selection())
        if not chosen:
            messagebox.showinfo(title,'Сначала выделите строки таблицы.' if ru else 'Select rows first.',parent=win)
            return
        if fixed.get() and not data.get('artboard',{}).get('rect_pt'):
            messagebox.showerror(title,'Нужен свежий экспорт v0.5 (artboard.rect_pt).' if ru
                                 else 'A fresh export with artboard.rect_pt is required.',parent=win)
            return
        angles=None if rotate.get()=='global' else [int(a) for a in rotate.get().split(',')]
        if fixed.get() and angles is not None and 0 not in angles:
            messagebox.showerror(title,'У закреплённого объекта должен быть разрешён угол 0°.' if ru
                                 else 'A locked object must allow 0°.',parent=win)
            return
        for oid in chosen:
            if not fixed.get() and angles is None:
                rules.pop(oid,None)
            else:
                obj=byid[oid]
                rules[oid]={'source_name':obj.get('name'),'source_bounds_pt':obj.get('source_bounds_pt'),
                            'lock_position':fixed.get(),'rotations':angles}
            table.item(oid,values=row_values(oid))
        refresh_count()

    ttk.Button(ctrl,text='Применить к выделенным строкам' if ru else 'Apply to selected rows',command=apply_choice).pack(side='right')
    ttk.Label(win,text=('Выберите строки → задайте фиксацию/повороты → нажмите «Применить к выделенным строкам» → «Сохранить». Рисунок не меняется.'
                        if ru else 'Select rows → choose lock/rotation → Apply to selected rows → Save. Artwork is not edited.'),
              wraplength=890,foreground='#555').pack(fill='x',padx=12,pady=8)
    foot=ttk.Frame(win);foot.pack(fill='x',padx=12,pady=(2,12))
    def save():
        try:save_constraints(input_path,data,rules)
        except Exception as ex:messagebox.showerror(title,str(ex),parent=win);return
        # Invalidate obsolete placements after any constraint update.
        stale=Path(input_path).parent/'result_test.json'
        if stale.exists():
            try:stale.unlink()
            except OSError as ex:
                messagebox.showerror(title,'Сохранено, но не удалось удалить старый результат:\n'+str(ex),parent=win)
                return
        win.destroy()
    ttk.Button(foot,text='Сохранить' if ru else 'Save',command=save).pack(side='right')
    ttk.Button(foot,text='Отмена' if ru else 'Cancel',command=win.destroy).pack(side='right',padx=7)
    refresh()
    return win
