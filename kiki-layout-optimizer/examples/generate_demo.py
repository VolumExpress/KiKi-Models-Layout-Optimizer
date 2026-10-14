"""Create a wholly synthetic test plate. NOT an existing P10/P11 artwork."""
import json
from pathlib import Path

here=Path(__file__).parent


def shape(kind,size):
    base={
      'horseshoe':[(-.5,-.5),(.5,-.5),(.5,.5),(.18,.5),(.18,-.1),(-.18,-.1),(-.18,.5),(-.5,.5)],
      'blade':[(-.08,-.5),(.08,-.5),(.08,.22),(.2,.22),(0,.5),(-.2,.22),(-.08,.22)],
      'gear':[(-.5,-.2),(-.2,-.2),(-.2,-.5),(.2,-.5),(.2,-.2),(.5,-.2),(.5,.2),(.2,.2),(.2,.5),(-.2,.5),(-.2,.2),(-.5,.2)]
    }[kind]
    return {'type':'path','ring':[[round(x*size,5),round(y*size,5)] for x,y in base]}

objs=[]
for typ in ('horseshoe','blade','gear'):
    for mm in (3,5.5,7,9):
        objs.append({'id':f'{typ}_{mm}', 'name':f'{typ}__{mm}mm', 'geometry':shape(typ,mm)})
for idx,(w,h) in enumerate(((4,2),(3,6),(5,4),(5,5),(6,3),(2,7))):
    objs.append({'id':f'misc_{idx}','name':f'honour_{idx}',
                 'geometry':{'type':'path','ring':[[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]]}})
data={'schema':1,'document_name':'KiKi_Synthetic_Demo.ai',
      'artboard':{'index':0,'width_mm':145,'height_mm':95},'objects':objs}
(here/'synthetic_plate.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Created synthetic_plate.json with',len(objs),'items')
