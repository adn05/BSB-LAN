#!/usr/bin/env python3
"""Répartition flash/RAM d'un build à partir du fichier .map de l'éditeur de liens.

Usage : mapsize.py <BSB_LAN.ino.map>
"""
import re,sys,collections
lines=open(sys.argv[1],errors='ignore').read().split('\n')
start=next(i for i,l in enumerate(lines) if l.startswith('Linker script and memory map'))
ALLOC={'.iram0.text':'flash','.flash.text':'flash','.flash.rodata':'flash','.dram0.data':'ram+flash','.dram0.bss':'ram','.flash.appdesc':'flash','.flash.init_array':'flash','.eh_frame':'flash','.noinit':'ram'}
out=None; pend=None
by=collections.Counter(); syms=[]
for l in lines[start:]:
    m=re.match(r'^(\.[\w.]+)',l)
    if m: out=m.group(1); pend=None; continue
    if out not in ALLOC: continue
    m=re.match(r'^ (\S+)\s*$',l)
    if m: pend=m.group(1); continue
    m=re.match(r'^ (\S+)?\s+0x([0-9a-f]{8,16})\s+0x([0-9a-f]+)\s+(\S+)$',l)
    if not m: pend=None; continue
    sec=m.group(1) or pend; pend=None
    size=int(m.group(3),16); f=m.group(4)
    if size==0: continue
    name=f.split('/')[-1]
    if '.a(' in name: name=re.sub(r'\(.*','',name)
    if '/sketch/' in f or 'BSB_LAN.ino' in f: name='SKETCH:'+f.split('/')[-1]
    elif '/libraries/' in f: name='LIB:'+f.split('/libraries/')[1].split('/')[0]
    elif 'core.a' in f or '/core/' in f: name='ARDUINO-CORE'
    by[(name,ALLOC[out])]+=size
    syms.append((size,out,sec,name))
def tot(kinds):
    c=collections.Counter()
    for (n,k),s in by.items():
        if k in kinds: c[n]+=s
    return c
print('TOTAL flash',sum(s for (n,k),s in by.items() if k!='ram'),' RAM',sum(s for (n,k),s in by.items() if k!='flash'))
print('== flash par composant (top 40)')
for n,s in tot({'flash','ram+flash'}).most_common(40): print(f'{s:9d}  {n}')
print('== RAM statique par composant (top 12)')
for n,s in tot({'ram','ram+flash'}).most_common(12): print(f'{s:9d}  {n}')
print('== sketch : plus gros objets')
for s,o,sec,n in sorted([x for x in syms if x[3].startswith('SKETCH:BSB')],reverse=True)[:45]: print(f'{s:8d} {o:14s} {sec[:80]}')
print('== objets du sketch (src/ embarqué inclus), flash / ram')
fl=tot({'flash','ram+flash'}); rm=tot({'ram','ram+flash'})
for n in sorted({k for k in fl if k.startswith('SKETCH')}|{k for k in rm if k.startswith('SKETCH')}, key=lambda k:-fl[k]): print(f'{fl[n]:9d} {rm[n]:7d}  {n}')
import fnmatch
print('== symboles BSB_LAN.ino par motif')
pats={'IPWE':['*Ipwe*'],'datalog/journal/SD':['*atalog*','*LogTelegram*','*transmitFile*','*usedBytes*','*totalBytes*','*startLoggingDevice*','*dateTime*','*graph_html*'],'MAX!':['*Max*','*max_*','*connectToMaxCul*'],'PPS':['*pps*','*PPS*'],'capteurs virtuels':['*queryVirtualPrognr*','*tcaselect*'],'MQTT':['*mqtt*','*MQTT*','*LogToMQTT*'],'config web':['*Config*','*config*','*printConfig*','*applyingConfig*'],'QD dump':['*handleDumpStatus*'],'certs':['*certs_bundle*'],'heating_cmdtbl':['*heating_cmdtbl*'],'OTA':['*init_ota_update*','*serverIndex*']}
for k,ps in pats.items():
    s=sum(x[0] for x in syms if x[3]=='SKETCH:BSB_LAN.ino.cpp.o' and any(fnmatch.fnmatch(x[2],p) for p in ps) and 'init_ota_updateEUlvE0_E9_M_invokeERKSt9_' not in x[2])
    print(f'{s:8d}  {k}')
