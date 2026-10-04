"""Independent NumPy oracle for specification 1.1.6 and Python bounds.
No original module import: its import has logging side effects and requires PyTorch.
Also writes the exact Python RWGT 1.3 format and checks native byte-for-byte export.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'build/rw'

def tensor(a):
    a = np.asarray(a, dtype='<f4')
    return struct.pack('<I', a.ndim) + struct.pack('<'+'I'*a.ndim, *a.shape) + a.tobytes()

def config():
    return struct.pack('<4I6d2IB', 100, 5, 1000, 4, 1e-6, .98, 1.2, .9, 10, .9, 12, 5, 1)

def string(s):
    b=s.encode(); return struct.pack('<I',len(b))+b

def signed(b):
    return b+hashlib.sha256(b).digest()

def encode(w, legacy=False):
    m = dict(base_codebook_index=w['index'],dimension_size=len(w['error']),num_references=len(w['refs']))
    b=b'RWGT'+struct.pack('<H',0x103 if legacy else 0x104)+string(json.dumps(m))
    for a in [w['position'],w['phase'],w['amplitudes'],w['freq'],w['offset'],w['error']]: b+=tensor(a)
    for r in w['refs']:
        b+=struct.pack('<fi',r['weight'],r['time'])+tensor(r['position'])+tensor(r['matrix'])
    if not legacy:
        b+=b'RWEX'+struct.pack('<dd',w['scale'],w['depth_scale'])+tensor(w['delta'])+tensor(w['adaptive'])+config()+struct.pack('<I',0)
    return signed(b)

def archive(weights,cb):
    b=b'RWGS'+struct.pack('<H',0x100)+config()+tensor(cb)+struct.pack('<I',len(weights))
    for i,w in enumerate(weights):
        wb=encode(w);b+=string(str(i))+struct.pack('<Q',len(wb))+wb+struct.pack('<I',0)
    return signed(b)

def reference(weights,cb,index,depth,time,py=False):
    w=weights[index]
    factors=[abs(r['weight'])*float(np.linalg.norm(r['matrix'])) for r in w['refs']]
    if py:
        gamma=max(factors,default=0)/max(1,len(factors))
        if gamma>=1 or (gamma>0 and depth>=math.ceil(math.log(1e-6*(1-gamma))/math.log(gamma))):depth=0
    base=cb[w['index']]*np.float32(w['scale'])
    delta=w['delta']*np.float32(w['depth_scale']**depth)*w['adaptive']
    phase=w['phase'].copy()
    for amp,freq,offset in zip(w['amplitudes'],w['freq'],w['offset']):
        phase+=amp*np.sin(np.float32(float(freq)*time+float(offset)))
    if py:
        phase=np.clip(phase,-1000,1000);delta=np.clip(delta,-1000,1000)
    rec=np.zeros_like(base)
    if depth:
        for r in w['refs']:
            position=w['position']+r['position']
            target=next(i for i,x in enumerate(weights) if np.array_equal(x['position'],position))
            if py and target==index:continue
            prev=reference(weights,cb,target,depth-1,time-r['time'],py)
            rec+=np.float32(r['weight'])*(r['matrix']@prev)
    result=base+delta+rec+phase+w['error']
    if py:
        result=np.clip(result,-1e4,1e4)
        gamma=sum(factors)/max(1,len(factors));err=float(np.linalg.norm(w['error']))
        if err>.01 and gamma<1:
            cap=(1-gamma)*err/(1+gamma);result=np.clip(result,-cap,cap)
    return result

def main():
    rng=np.random.default_rng(417)
    worst=0.;count=0
    with tempfile.TemporaryDirectory(prefix='rw-differential-') as td:
        td=Path(td)
        for d in [1,3,8,17]:
            cb=rng.normal(0,.2,(3,d)).astype('f4');weights=[]
            for i in range(3):
                w=dict(index=i,position=np.array([i,0,0,0,0]),phase=rng.normal(0,.03,d).astype('f4'),
                       amplitudes=rng.normal(0,.02,(2,d)).astype('f4'),freq=np.array([.3,1.1],dtype='f4'),
                       offset=np.array([.2,-.1],dtype='f4'),error=rng.normal(0,.001 if d%2 else .02,d).astype('f4'),
                       delta=rng.normal(0,.01,d).astype('f4'),adaptive=rng.uniform(.5,1.2,d).astype('f4'),
                       scale=1.25,depth_scale=.8,refs=[])
                for target in [(i+1)%3,i]:
                    w['refs'].append(dict(weight=float(np.float32(.12)),time=1 if target!=i else 0,
                        position=np.array([target-i,0,0,0,0]),matrix=(np.eye(d)*.5+rng.normal(0,.01,(d,d))).astype('f4')))
                weights.append(w)
            path=td/'system.rwgs';path.write_bytes(archive(weights,cb))
            for py in [False,True]:
                for depth in [0,1,2,4,6]:
                    for time in [-.25,0.,1.7]:
                        for index in [0,2]:
                            args=[str(EXE),'evaluate',str(path),str(index),str(depth),str(time)]+(['python'] if py else [])
                            got=np.array(json.loads(subprocess.check_output(args,text=True)),dtype='f4')
                            expected=reference(weights,cb,index,depth,time,py)
                            err=float(np.max(np.abs(got-expected)));worst=max(worst,err)
                            np.testing.assert_allclose(got,expected,atol=3e-6,rtol=3e-6)
                            count+=1
            w=weights[0].copy();w.update(scale=1.,delta=np.zeros(d,dtype='f4'),adaptive=np.ones(d,dtype='f4'),depth_scale=1.)
            old=td/'python.rwgt';old.write_bytes(encode(w,True));new=td/'native.rwgt'
            subprocess.run([str(EXE),'convert-weight',str(old),str(new)],check=True)
            # Native 1.4 keeps the entire legacy payload unchanged, except version and added extension.
            native=new.read_bytes();legacy=old.read_bytes()
            assert native[:4]==legacy[:4] and native[6:len(legacy)-32]==legacy[6:-32]
            assert hashlib.sha256(native[:-32]).digest()==native[-32:]
    print(json.dumps(dict(cases=count,dimensions=[1,3,8,17],max_absolute_error=worst,legacy_interop_cases=4)))

if __name__=='__main__': main()
