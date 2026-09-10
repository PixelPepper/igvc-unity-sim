"""Inspect the pinned source course; never invent an undocumented closing edge."""
import json
import math
from pathlib import Path
import re
import struct
import sys
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ros2/src/igvc_gps'))
from igvc_gps.geodesy import LocalFrame
SOURCE = ROOT / 'artifacts/vendor/scr_simulator/Assets/Scenes/Maps/IGVC_2026_AutoNav.unity'


def rotate(q, v):
    x, y, z, w = (q[k] for k in ('x', 'y', 'z', 'w'))
    a, b, c = v
    return ((1-2*y*y-2*z*z)*a+(2*x*y-2*z*w)*b+(2*x*z+2*y*w)*c,
            (2*x*y+2*z*w)*a+(1-2*x*x-2*z*z)*b+(2*y*z-2*x*w)*c,
            (2*x*z-2*y*w)*a+(2*y*z+2*x*w)*b+(1-2*x*x-2*y*y)*c)


def vec(v):
    return tuple(v[k] for k in ('x', 'y', 'z'))


def xy(v):
    return (v[0]+2.61, v[2]+20.57)


def main():
    text = SOURCE.read_text()
    blocks = re.split(r'^--- !u!\d+ &[^\n]+\n', text, flags=re.M)[1:]
    docs = [yaml.safe_load(b) for b in blocks]
    spline = next(d['MonoBehaviour'] for d in docs if 'm_Splines' in d.get('MonoBehaviour', {}))
    curves = []
    for s in spline['m_Splines']:
        points = []
        for a, b in zip(s['m_Knots'], s['m_Knots'][1:]):
            p0, p3 = vec(a['Position']), vec(b['Position'])
            u = rotate(a['Rotation']['value'], vec(a['TangentOut']))
            v = rotate(b['Rotation']['value'], vec(b['TangentIn']))
            p1 = tuple(x+y for x, y in zip(p0, u))
            p2 = tuple(x+y for x, y in zip(p3, v))
            for i in range(300):
                t = i/300
                points.append(xy(tuple((1-t)**3*p0[k]+3*(1-t)**2*t*p1[k]+3*(1-t)*t*t*p2[k]+t**3*p3[k] for k in range(3))))
        points.append(xy(vec(s['m_Knots'][-1]['Position'])))
        curves.append(points)
    mesh = next(d['Mesh'] for d in docs if d.get('Mesh', {}).get('m_Name') == 'Road')
    data = mesh['m_VertexData']
    raw = bytes.fromhex(str(data['_typelessdata']))
    stride = len(raw)//data['m_VertexCount']
    vertices = [xy(struct.unpack_from('<fff', raw, i*stride)) for i in range(data['m_VertexCount'])]
    indicesraw = bytes.fromhex(str(mesh['m_IndexBuffer']))
    indices = struct.unpack('<'+'H'*(len(indicesraw)//2), indicesraw)
    barrels = []
    for d in docs:
        p = d.get('PrefabInstance', {})
        modifications = p.get('m_Modification', {}).get('m_Modifications', [])
        attrs = {a['propertyPath']: a.get('value') for a in modifications}
        if (p.get('m_SourcePrefab',{}).get('guid') == 'b65e5813885621a47b96e74eaae29dd0'
                and all('m_LocalPosition.'+k in attrs for k in ('x','y','z'))):
            # Source prefab scene instances are the barrel FBX; retain source GUID for audit.
            position = tuple(float(attrs['m_LocalPosition.'+k]) for k in ('x','y','z'))
            barrels.append({'xy': xy(position), 'source_guid': p.get('m_SourcePrefab',{}).get('guid')})
    # Explicitly approved unmarked link; alternate around the barrel pairs.
    anchors=[curves[1][0],(27.,20.7),(28.7,25.3),(27.,31.4),curves[0][-1]]
    connector=[]
    for j in range(len(anchors)-1):
        a,b=anchors[j],anchors[j+1]
        prev=anchors[j-1] if j else (a[0],a[1]-3)
        nxt=anchors[j+2] if j+2<len(anchors) else (b[0],b[1]+3)
        ma=tuple((b[k]-prev[k])*.5 for k in range(2)) if j else (0.,3.)
        mb=tuple((nxt[k]-a[k])*.5 for k in range(2)) if j+2<len(anchors) else (0.,3.)
        for i in range(150):
            t=i/150
            connector.append(tuple((2*t**3-3*t*t+1)*a[k]+(t**3-2*t*t+t)*ma[k]+(-2*t**3+3*t*t)*b[k]+(t**3-t*t)*mb[k] for k in range(2)))
    connector.append(anchors[-1])
    start=min(range(len(curves[1])),key=lambda i:math.hypot(*curves[1][i]))
    route=[(0.,0.)]+list(reversed(curves[1][:start+1]))+connector[1:]+list(reversed(curves[0]))[1:]+list(reversed(curves[1][start:]))[1:]+[(0.,0.)]
    modes=['painted']*(start+2)+['unmarked']*(len(connector)-1)+['painted']*(len(route)-(start+2)-(len(connector)-1))
    lengths=[0.]
    for a,b in zip(route,route[1:]):lengths.append(lengths[-1]+math.dist(a,b))
    origin=json.loads((ROOT/'ros2/src/igvc_gps/config/origin.json').read_text())
    frame=LocalFrame(origin)
    goals=[]
    # Goals stay near the source centerline; local perception still determines each path.
    targets=[i*2. for i in range(1,int(lengths[-1]/2)+1)]+[lengths[-1]]
    for target in targets:
        idx=min(range(len(lengths)),key=lambda i:abs(lengths[i]-target))
        p=route[idx];before=route[max(0,idx-2)];after=route[min(len(route)-1,idx+2)]
        yaw=math.atan2(after[1]-before[1],after[0]-before[0])
        def clearance(p):return min(math.dist(p,b['xy']) for b in barrels)
        def footprint_clearance(p):
            c,s=math.cos(yaw),math.sin(yaw)
            distances=[]
            for barrel in barrels:
                dx,dy=barrel['xy'][0]-p[0],barrel['xy'][1]-p[1]
                x,y=c*dx+s*dy,-s*dx+c*dy
                distances.append(math.hypot(max(-1.1-x,0.,x-.6),max(abs(y)-.5,0.))-.2682114)
            return min(distances)
        chosen=p;offset=0.
        for candidate_offset in [v for step in range(1,8) for v in (.2*step,-.2*step)]:
            if clearance(chosen)>=1.1 and footprint_clearance(chosen)>=.20:break
            candidate=(p[0]-math.sin(yaw)*candidate_offset,p[1]+math.cos(yaw)*candidate_offset)
            if footprint_clearance(candidate)>footprint_clearance(chosen):chosen,offset=candidate,candidate_offset
        if target==lengths[-1]:chosen=(0.,0.);yaw=0.;offset=0.
        lat,lon,alt=frame.to_geodetic(*chosen)
        goals.append(dict(name=f'loop_{len(goals)+1:03}',latitude=lat,longitude=lon,altitude=alt,yaw=yaw,
                          odom_xy=chosen,route_s_m=lengths[idx],mode=modes[idx],lateral_offset_m=offset,
                          barrel_center_clearance_m=clearance(chosen),footprint_barrel_clearance_m=footprint_clearance(chosen)))
    mission={'origin':origin,'note':'Source-spline full circuit with explicitly planned unmarked barrel connector. Live perception remains authoritative.',
             'waypoints':goals,'route':{'frame':'odom','dense_xy':route,'dense_s_m':lengths,'dense_modes':modes,'length_m':lengths[-1],
             'unmarked_connector_anchors_xy':anchors,'barrel_radius_m':.2682114}}
    (ROOT/'ros2/src/igvc_gps/config/full_loop.json').write_text(json.dumps(mission,indent=2))
    out = ROOT/'artifacts/checks/course-route.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {'source':str(SOURCE.relative_to(ROOT)), 'frame':'odom',
              'status':'source_open_splines_with_explicit_approved_unmarked_connector',
              'spline_closed_flags':[s['m_Closed'] for s in spline['m_Splines']],
              'serialized_links':spline['m_Knots'], 'splines_xy':curves,
              'lengths_m':[sum(math.dist(a,b) for a,b in zip(c,c[1:])) for c in curves],
              'unlinked_endpoints_xy':[curves[0][-1],curves[1][0]],
              'gap_m':math.dist(curves[0][-1],curves[1][0]),
              'barrel_instances':barrels, 'mesh_triangles':len(indices)//3,
              'route_length_m':lengths[-1],'waypoint_count':len(goals),
              'connector_min_barrel_center_clearance_m':min(math.dist(p,b['xy']) for p in connector for b in barrels),
              'minimum_waypoint_barrel_center_clearance_m':min(g['barrel_center_clearance_m'] for g in goals),
              'minimum_waypoint_footprint_barrel_clearance_m':min(g['footprint_barrel_clearance_m'] for g in goals),
              'centerline_barrel_conflicts':[b for b in barrels if min(math.dist(p,b['xy']) for p in route)<.77]}
    out.write_text(json.dumps(report,indent=2))
    image = Image.new('RGB',(1300,1450),'#f4f4f0')
    draw=ImageDraw.Draw(image)
    def pixel(p): return (round(330+p[0]*24),round(1280-p[1]*24))
    for x in range(-5,36,5):
        draw.line([pixel((x,-3)),pixel((x,48))], fill='#dddddd')
        draw.text(pixel((x,-4)),str(x),fill='black')
    for y in range(0,46,5):
        draw.line([pixel((-6,y)),pixel((36,y))],fill='#dddddd')
        draw.text(pixel((-7,y)),str(y),fill='black')
    for i in range(0,len(indices),3):
        draw.polygon([pixel(vertices[j]) for j in indices[i:i+3]],fill='#bbbbae')
    for curve,color in zip(curves,('#1967d2','#158047')):
        draw.line([pixel(p) for p in curve], fill=color,width=3)
    draw.line([pixel(p) for p in connector],fill='#b02ead',width=4)
    for i,g in enumerate(goals,1):
        x,y=pixel(g['odom_xy']);draw.ellipse((x-3,y-3,x+3,y+3),fill='black')
        draw.text((x+4,y-12),str(i),fill='black')
    for barrel in barrels:
        x,y=pixel(barrel['xy']);r=7
        draw.ellipse((x-r,y-r,x+r,y+r),fill='#d66815',outline='black')
    for label,p in [('OPEN A',curves[0][-1]),('OPEN B',curves[1][0]),('JOIN',curves[0][0]),('SPAWN',(0,0))]:
        x,y=pixel(p);draw.ellipse((x-6,y-6,x+6,y+6),fill='red');draw.text((x+9,y),label,fill='black')
    draw.text((60,30),'Pinned Sooner AutoNav: baked road surface, spline centerlines, barrel instances',fill='black')
    draw.text((60,50),'ROS odom +X east/right, +Y north/up. Purple: explicitly planned unmarked connector around barrels.',fill='black')
    draw.text((60,70),'Numbered goals; grey = actual road mesh; blue/green = source splines. Local obstacle detours required.',fill='black')
    image.save(out.with_suffix('.png'))
    print(json.dumps({k:v for k,v in report.items() if k not in ('splines_xy','barrel_instances')},indent=2))


if __name__ == '__main__':
    main()
