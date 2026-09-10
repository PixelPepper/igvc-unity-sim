"""Assess exact STL connectivity before extracting any articulated camera bracket."""
from pathlib import Path
import json
import hashlib
import struct
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'ros2/src/igvc_description/meshes/camera_mount'
SOURCE=Path('C:/Users/brand/Downloads/OneDrive_2026-03-04/R3-a (Spring 2025)/R3-a URDF/meshes/base_link.STL')
DTYPE=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
data=np.fromfile(SOURCE,dtype=DTYPE,offset=84)
verts,indices=np.unique(data['vertices'].reshape(-1,3),axis=0,return_inverse=True)
indices=indices.reshape(-1,3)
parent=np.arange(len(verts))
def find(a):
    while parent[a]!=a:
        parent[a]=parent[parent[a]];a=parent[a]
    return a
def union(a,b):
    a,b=find(a),find(b)
    if a!=b: parent[max(a,b)]=min(a,b)
for a,b,c in indices:
    union(a,b);union(a,c)
labels=np.array([find(a) for a in indices[:,0]])
tops=[]
for label in np.unique(labels[np.max(data['vertices'][:,:,2],axis=1)>.75]):
    selection=labels==label;p=data['vertices'][selection].reshape(-1,3)
    tops.append({'label':int(label),'triangles':int(selection.sum()),'min':p.min(axis=0).tolist(),'max':p.max(axis=0).tolist()})
OUT.mkdir(parents=True,exist_ok=True)
report={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'connectivity':'Exact shared vertex coordinates; no tolerance weld or geometric cut','components_total':int(len(np.unique(labels))),'components_reaching_top':tops}
candidate=[item for item in tops if item['min'][2]>.75 and item['max'][1]-item['min'][1]>.09]
if len(candidate)!=1:raise RuntimeError('Moving arm is not uniquely separable; export refused.')
moving=labels==candidate[0]['label']
ids=indices[moving]
edges=np.sort(np.concatenate([ids[:,[0,1]],ids[:,[1,2]],ids[:,[2,0]]]),axis=1)
_,edge_counts=np.unique(edges,axis=0,return_counts=True)
if not np.all(edge_counts==2):raise RuntimeError('Moving component is not a closed manifold; export refused.')
pin=np.array([-.34396836,0,.8])
angle=np.arctan2(.07140202075,.9974476099)
C=np.diag([-1.,-1.,1.])
R=np.array([[np.cos(angle),0,-np.sin(angle)],[0,1,0],[np.sin(angle),0,np.cos(angle)]])
arm=data[moving].copy()
canonical=data['vertices'][moving].astype(float)@C.T
arm['vertices']=(canonical-pin)@R.T
arm['normal']=data['normal'][moving].astype(float)@C.T@R.T
def write_stl(name,mesh):
    dest=OUT/name
    with dest.open('wb') as out:
        out.write(b'R3a camera component extraction; see assessment.json'.ljust(80,b' '))
        out.write(struct.pack('<I',len(mesh)));mesh.tofile(out)
    return {'path':str(dest.relative_to(ROOT)),'triangles':len(mesh),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
static=write_stl('base_static_source_basis.stl',data[~moving])
arm_file=write_stl('moving_bracket_pivot_level.stl',arm)
reconstructed=arm['vertices'].astype(float)@R+pin
report.update({'separation_status':'clean_closed_component','moving_component':candidate[0],
               'moving_mesh_closed_edge_count':int(len(edge_counts)),
               'stationary_base':static,'moving_bracket':arm_file,
               'static_coordinate_contract':'Original source XYZ; retain canonical base visual rpy=(0,0,pi). Only moving component removed; original source untouched.',
               'moving_coordinate_contract':'Canonical physical-forward XYZ, pivot-relative, level orientation; visual origin identity. Vertex=(R_y(-4.0945186569deg))*(diag(-1,-1,1)*source-pivot). Proper rotations preserve winding.',
               'joint_origin_canonical':pin.tolist(),'joint_axis_canonical':[0,1,0],
               'level_correction_ros_y_degrees':float(-np.degrees(angle)),
               'arm_bounds_local':[arm['vertices'].reshape(-1,3).min(axis=0).tolist(),arm['vertices'].reshape(-1,3).max(axis=0).tolist()],
               'float32_roundtrip_max_error_m':float(np.abs(reconstructed-canonical).max()),
               'current_cad_pose_joint_angle_degrees':float(np.degrees(angle)),
               'limitations':'Visual extraction only. No inertial split or collision changes. Collision proxy may still cover old arm region. Zero joint pose levels extracted arm; original CAD pose recovered at +4.0945186569 degrees. Static base remains large and needs separate visual simplification.'})
if '--simplify' in sys.argv[1:]:
    from simplify_robot import simplify
    import importlib.metadata
    target=OUT/'base_static_source_basis_simplified.stl'
    result=simplify(OUT/'base_static_source_basis.stl',target,101237,.005)
    result['path']=str(target.relative_to(ROOT))
    result['algorithm']='fast_simplification quadric reduction, agg=7'
    result['versions']={'numpy':np.__version__,'fast_simplification':importlib.metadata.version('fast-simplification')}
    result['coordinate_contract']='Original source basis; retain existing base visual Z=pi rotation.'
    result['limitation']='Bounds/finite/normals checks do not establish silhouette, topology, Hausdorff distance or sensor fidelity.'
    report['stationary_base_simplified']=result
(OUT/'assessment.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['separation_status','stationary_base','moving_bracket','joint_origin_canonical','float32_roundtrip_max_error_m']},indent=2))
if 'stationary_base_simplified' in report:
    print(json.dumps(report['stationary_base_simplified'],indent=2))
