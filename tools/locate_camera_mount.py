"""Read-only top-pole STL analysis in original source coordinates."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('C:/Users/brand/Downloads/OneDrive_2026-03-04/R3-a (Spring 2025)/R3-a URDF/meshes/base_link.STL')
OUT=ROOT/'artifacts/checks/camera-mount-analysis'
data=np.fromfile(SOURCE,dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]),offset=84)
v=data['vertices'].astype(float); n=data['normal'].astype(float)
mask=v[:,:,2].min(axis=1)>.65
vv=v[mask];p=np.unique(np.round(vv.reshape(-1,3),8),axis=0)
area=np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)/2
report={'source':str(SOURCE),'region_z_above':.65,'bounds_source':[p.min(axis=0).tolist(),p.max(axis=0).tolist()],'triangles':len(vv),'dominant_planes':{},'pin_circle_fits':[],'attachment_faces':[],'reference_meshes':[]}
for axis in range(3):
    flat=mask&(np.ptp(v[:,:,axis],axis=1)<1e-6)&(np.abs(n[:,axis])>.99)
    levels={}
    for level,a in zip(np.round(v[flat,0,axis],7),area[flat]):levels[level]=levels.get(level,0)+a
    report['dominant_planes']['xyz'[axis]]=sorted(levels.items(),key=lambda t:-t[1])[:20]
im=Image.new('RGB',(1600,850),'white');d=ImageDraw.Draw(im)
for panel,(aa,bb,label) in enumerate([(0,2,'Source X/Z'),(1,2,'Source Y/Z')]):
    lo=p[:,aa].min();hi=p[:,aa].max();scale=min(700/(hi-lo),650/(p[:,bb].max()-p[:,bb].min()))
    for tri in vv:
        pp=[(int((pt[aa]-lo)*scale+panel*800+40),int((p[:,bb].max()-pt[bb])*scale+70)) for pt in tri]
        d.line(pp+[pp[0]],fill=(50,80,110))
    d.text((panel*800+40,20),label+' +horizontal right, +Z up',fill='black')
im.save(str(OUT)+'.png')
Path(str(OUT)+'.json').write_text(json.dumps(report,indent=2))
for level in [-.021,-.015,.015,.021]:
    pp=p[np.abs(p[:,1]-level)<1e-6][:,[0,2]]
    rng=np.random.default_rng(9);best=[]
    for _ in range(8000):
        q=pp[rng.choice(len(pp),3,replace=False)]
        try: c=np.linalg.solve(2*(q[1:]-q[0]),(q[1:]**2).sum(axis=1)-(q[0]**2).sum())
        except np.linalg.LinAlgError:continue
        r=np.linalg.norm(q[0]-c)
        if not .001<r<.025:continue
        residual=np.abs(np.linalg.norm(pp-c,axis=1)-r)
        best.append((int((residual<1e-6).sum()),c.tolist(),float(r)))
    fit=sorted(best,key=lambda t:-t[0])[0]
    report['pin_circle_fits'].append({'source_y_plane':level,'inliers_at_1um':fit[0],'source_center_xz':fit[1],'radius':fit[2]})
plate=mask&(v[:,:,0].max(axis=1)<.307)
normals={}
for normal,a in zip(np.round(n[plate],5),area[plate]):
    key=tuple(normal);normals[key]=normals.get(key,0)+a
report['dominant_plate_normals_area']=[{'normal':list(nn),'area':aa} for nn,aa in sorted(normals.items(),key=lambda t:-t[1])[:10]]
for sign in [-1,1]:
    face=plate&(sign*n[:,0]>.99)
    cent=(v[face].mean(axis=1)*area[face,None]).sum(axis=0)/area[face].sum()
    report['attachment_faces'].append({'source_normal':n[face][0].tolist(),'source_centroid':cent.tolist(),'bounds_source':[v[face].reshape(-1,3).min(axis=0).tolist(),v[face].reshape(-1,3).max(axis=0).tolist()]})
for name in ['Camera_Mount.STL','Camera_Hinge.STL','R2-a (Arm).STL']:
    source=SOURCE.parents[2]/'Attachements/Camera/STL'/name
    dd=np.fromfile(source,dtype=data.dtype,offset=84);points=dd['vertices'].reshape(-1,3)
    report['reference_meshes'].append({'source':str(source),'bounds_stl_units':[points.min(axis=0).tolist(),points.max(axis=0).tolist()],'triangles':len(dd),'units_note':'Dimensions suggest millimetres; original standalone exports differ from base-link metre coordinates.'})
pin=np.array([-.34396836,0,.8]);seat=np.array([-.2924297025,0,.80080009435]);angle=np.arctan2(.07140202075,.9974476099)
R=np.array([[np.cos(angle),0,-np.sin(angle)],[0,1,0],[np.sin(angle),0,np.cos(angle)]])
report.update({'pitch_pin_canonical_xyz':pin.tolist(),'pitch_axis_canonical':[0,1,0],
               'seat_center_canonical_xyz_current_cad':seat.tolist(),'seat_outward_normal_canonical':[.9974476099,0,-.07140202075],
               'current_cad_downward_pitch_degrees':float(np.degrees(angle)),
               'level_correction_ros_y_degrees':float(-np.degrees(angle)),
               'seat_center_after_leveling_whole_bracket_about_pin':(pin+R@(seat-pin)).tolist(),
               'limitation':'Base STL lumps this bracket into base_link and defines no movable camera joint. Pivot movement requires extracting moving bracket geometry. Camera body/optical-center offsets are not measured by this bracket analysis.'})
Path(str(OUT)+'.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['pitch_pin_canonical_xyz','seat_center_canonical_xyz_current_cad','current_cad_downward_pitch_degrees','seat_center_after_leveling_whole_bracket_about_pin']},indent=2))
