"""Read-only CAD surface investigation; outputs only lidar-mount-analysis artifacts."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('C:/Users/brand/Downloads/OneDrive_2026-03-04/R3-a (Spring 2025)/R3-a URDF/meshes/base_link.STL')
OUT = ROOT / 'artifacts/checks/lidar-mount-analysis'
dtype = np.dtype([('normal','<f4',(3,)), ('vertices','<f4',(3,3)), ('attribute','<u2')])
data = np.fromfile(SOURCE, dtype=dtype, offset=84)
v = data['vertices'].astype(float)
n = data['normal'].astype(float)
area = np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)/2
flat = (np.ptp(v[:,:,2],axis=1)<1e-6) & (np.abs(n[:,2])>.99)
levels = {}
for z,a in zip(np.round(v[flat,0,2],6),area[flat]): levels[z]=levels.get(z,0)+a
top = sorted(levels.items(), key=lambda p:p[1], reverse=True)[:30]
report={'source':str(SOURCE),'horizontal_levels_z_area':top,'hole_fits_source':[], 'vertical_intersections':[]}
mask=(v[:,:,2].mean(axis=1)>.2)&(v[:,:,2].mean(axis=1)<.65)&(np.abs(n[:,2])<.98)
points=v[mask].reshape(-1,3)
im=Image.new('RGB',(1400,1200),'white'); draw=ImageDraw.Draw(im)
for x,y,z in points:
    draw.point((int((x+.4)*1300+40),int((.4-y)*1300+80)), fill=(int(255*(z-.2)/.45),60,120))
draw.text((30,20),'Original +X right, +Y up. 1300 pixels/metre; sides at 0.2<z<0.65m',fill='black')
im.save(str(OUT)+'.png')
region=(v[:,:,0].mean(axis=1)<-.18)&(v[:,:,0].mean(axis=1)>-.33)&(np.abs(v[:,:,1].mean(axis=1))<.09)&(v[:,:,2].mean(axis=1)>.25)
rv=np.unique(np.round(v[region].reshape(-1,3),8),axis=0)
zs,counts=np.unique(np.round(rv[:,2],6),return_counts=True)
for z,c in zip(zs,counts):
    if c<12: continue
    p=rv[np.abs(rv[:,2]-z)<1e-6]
im=Image.new('RGB',(1300,1000),'white'); d=ImageDraw.Draw(im)
roi=(np.min(v[:,:,0],axis=1)>-.32)&(np.max(v[:,:,0],axis=1)<-.19)&(np.max(np.abs(v[:,:,1]),axis=1)<.07)&(v[:,:,2].mean(axis=1)>.289)
for tri in v[roi]:
    pp=[(int((x+.32)*8500+60),int((.05-y)*8500+50)) for x,y,z in tri]
    z=tri[:,2].mean();color=(int(np.clip((z-.289)/.012,0,1)*230),90,150)
    d.line(pp+[pp[0]],fill=color,width=1)
d.text((20,20),'Mount sourceXY detail: +X right +Y up, 8500 px/m; triangle edges z>.289',fill='black')
im.save(str(OUT)+'.detail.png')
for z in [.2908,.2935,.295,.29675,.3]:
    p=rv[(np.abs(rv[:,2]-z)<1e-6)&(rv[:,0]>-.315)&(rv[:,0]<-.2)&(np.abs(rv[:,1])<.05),:2]
    rng=np.random.default_rng(7); best=[]
    for _ in range(5000):
        q=p[rng.choice(len(p),3,replace=False)]
        try: c=np.linalg.solve(2*(q[1:]-q[0]),(q[1:]**2).sum(axis=1)-(q[0]**2).sum())
        except np.linalg.LinAlgError: continue
        r=np.linalg.norm(q[0]-c)
        if not .015<r<.1 or abs(c[1])>.005 or c[0]>-.25:continue
        residual=np.abs(np.linalg.norm(p-c,axis=1)-r)
        count=int((residual<2e-6).sum())
        best.append((count,c.tolist(),r))
    # The large end has no strong exact-circle consensus: retain measured contour, not a guessed radius.
pp=rv[np.abs(rv[:,2]-.2908)<1e-6,:2]
for xs in [True,False]:
    for ys in [True,False]:
        p=pp[((pp[:,0]<-.26)==xs)&((pp[:,1]>0)==ys)]
        A=np.column_stack([2*p[:,0],2*p[:,1],np.ones(len(p))]);b=(p*p).sum(axis=1)
        sol=np.linalg.lstsq(A,b,rcond=None)[0];r=np.sqrt(sol[2]+sum(sol[:2]**2))
        residual=np.abs(np.linalg.norm(p-sol[:2],axis=1)-r)
        report['hole_fits_source'].append({'center_xy':sol[:2].tolist(),'radius':float(r),'points':len(p),'max_radial_residual':float(residual.max())})
sel=region&flat
report['local_horizontal_faces_z_area']=[(float(z),float(area[sel&(np.abs(v[:,0,2]-z)<1e-6)].sum())) for z in np.unique(np.round(v[sel,0,2],6))]
p=rv[(np.abs(rv[:,2]-.2935)<1e-6)&(rv[:,0]>-.315)&(rv[:,0]<-.24)&(rv[:,1]>.025),:2]
report['large_end_contour_z_2935']=p.tolist()
for x,y in [(-.2700228,0),(-.2285816,0),(-.2980228,.02803123),(-.296,.028),(-.26,.015)]+[(-.2980228+d,.02803123) for d in [.0025,.003,.004,.005,.006,-.003]]:
    a=v[:,0,:2]; b=v[:,1,:2]-a; c=v[:,2,:2]-a; q=np.array([x,y])-a
    den=b[:,0]*c[:,1]-b[:,1]*c[:,0]
    with np.errstate(divide='ignore',invalid='ignore'):
        u=(q[:,0]*c[:,1]-q[:,1]*c[:,0])/den;w=(b[:,0]*q[:,1]-b[:,1]*q[:,0])/den
    with np.errstate(invalid='ignore'):
        hit=(u>=-1e-7)&(w>=-1e-7)&(u+w<=1+1e-7)&(np.abs(den)>1e-14)
    zh=v[hit,0,2]+u[hit]*(v[hit,1,2]-v[hit,0,2])+w[hit]*(v[hit,2,2]-v[hit,0,2])
    report['vertical_intersections'].append({'source_xy':[x,y],'z_above_25cm':np.unique(np.round(zh[zh>.25],7)).tolist()})
report['recommended_seating_origin_canonical']=[.2700228,0,.295]
report['rotor_xy_basis']='Hole-pattern match to sensor IGES supplied by workflow_docs: rotor 28mm from wider hole pair,42mm from narrower pair. Not inferred from a bounding-box midpoint.'
report['roof_top_z']=.283175
report['seat_boss_top_z']=.295
report['small_end_arc_source']={'center_xy':[-.2285816,0],'radius_at_z_300':.0241}
report['large_end_radius']='Not circular: no single exact radius established; outer transverse half-width is about41.15mm. Rotor cap radius must come from sensor model.'
report['scan_frame']='Axis canonical+Z, XY(.2700228,0); scan Z=.295+sensor optical-plane height above footbottom. Optical-plane height not established by robot mesh.'
Path(str(OUT)+'.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['recommended_seating_origin_canonical','roof_top_z','seat_boss_top_z','scan_frame']},indent=2))
