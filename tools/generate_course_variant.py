"""Seeded course geometry; no Unity/ROS mutations. Run with Python + Pillow."""
import argparse
import bisect
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'ros2/src/igvc_gps'))
from igvc_gps.geodesy import LocalFrame

MARGIN = .2
BODY_RADIUS = math.hypot(1.1, .5)
DEFAULT_RAMP = dict(id='ramp-001', x=2., y=0., yaw=0., width=3.,
                    rise_length=3., deck_length=2., height=.4)
RAMP_CHECKPOINTS = ((1., 'approach'), (2., 'start'), (5., 'deck_start'),
                    (7., 'deck_end'), (10., 'exit'), (11., 'departure'))


def point_segment(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    den = dx*dx+dy*dy
    t = max(0., min(1., ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0.
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)


def box(x, y, yaw, xmin, xmax, ymin, ymax):
    c, s = math.cos(yaw), math.sin(yaw)
    return [(x+c*a-s*b, y+s*a+c*b) for a,b in ((xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax))]


def edges(poly):
    return zip(poly, poly[1:]+poly[:1])


def polygon_distance(a, b):
    # Separating-axis overlap test followed by exact convex edge distance.
    separated = False
    for poly in (a,b):
        for p,q in edges(poly):
            nx,ny = p[1]-q[1], q[0]-p[0]
            aa = [x*nx+y*ny for x,y in a]; bb = [x*nx+y*ny for x,y in b]
            if max(aa)<min(bb) or max(bb)<min(aa): separated=True
    if not separated: return 0.
    return min([point_segment(p,u,v) for p in a for u,v in edges(b)] +
               [point_segment(p,u,v) for p in b for u,v in edges(a)])


def point_box(p, obstacle):
    dx,dy = p[0]-obstacle['x'],p[1]-obstacle['y']
    c,s = math.cos(obstacle['yaw']),math.sin(obstacle['yaw'])
    return math.hypot(max(abs(c*dx+s*dy)-obstacle['length']/2,0.),
                      max(abs(-s*dx+c*dy)-obstacle['width']/2,0.))


def obstacle_box(o):
    return box(o['x'],o['y'],o['yaw'],-o['length']/2,o['length']/2,-o['width']/2,o['width']/2)


def obstacle_distance(a,b):
    ac,bc = a['kind']!='barricade',b['kind']!='barricade'
    if ac and bc:return math.hypot(a['x']-b['x'],a['y']-b['y'])-(a['width']+b['width'])/2
    if ac:return point_box((a['x'],a['y']),b)-a['width']/2
    if bc:return point_box((b['x'],b['y']),a)-b['width']/2
    return polygon_distance(obstacle_box(a),obstacle_box(b))


def body_clearance(p, yaw, obstacle):
    if obstacle['kind']=='barricade':
        return polygon_distance(box(*p,yaw,-1.1,.6,-.5,.5),obstacle_box(obstacle))
    c,s = math.cos(yaw),math.sin(yaw)
    dx,dy = obstacle['x']-p[0],obstacle['y']-p[1]
    x,y = c*dx+s*dy,-s*dx+c*dy
    return math.hypot(max(-1.1-x,0.,x-.6),max(abs(y)-.5,0.))-obstacle['width']/2


def arcs(points):
    result=[0.]
    for a,b in zip(points,points[1:]):result.append(result[-1]+math.dist(a,b))
    return result


def resample(points, modes, spacing=.25):
    ss=arcs(points); total=ss[-1]; count=math.ceil(total/spacing)
    result=[]; output_modes=[]
    for i in range(count+1):
        s=total*i/count; k=min(len(points)-2,max(0,bisect.bisect_right(ss,s)-1))
        t=(s-ss[k])/(ss[k+1]-ss[k]) if ss[k+1]>ss[k] else 0.
        result.append(tuple(points[k][j]+t*(points[k+1][j]-points[k][j]) for j in range(2)))
        output_modes.append(modes[k])
    result[0]=result[-1]=(0.,0.)
    return result,output_modes


def headings(points):
    values=[]
    for i in range(len(points)-1):
        prev=points[i-1] if i else points[-2]; nxt=points[i+1]
        values.append(math.atan2(nxt[1]-prev[1],nxt[0]-prev[0]))
    values.append(values[0]);values[0]=values[-1]=0.
    return values


def sweep_bounds(points,yaws):
    bounds=[]
    for i in range(len(points)):
        candidates=[]
        for j in (max(0,i-1),min(len(points)-1,i+1)):
            angle=abs(math.atan2(math.sin(yaws[j]-yaws[i]),math.cos(yaws[j]-yaws[i])))
            candidates.append(math.dist(points[i],points[j])+BODY_RADIUS*angle)
        bounds.append(max(candidates))
    return bounds


def lane_half_width(p):
    # Opening ramp paint lies fully on the 3 m surface: center at +/-1.44 m.
    if abs(p[1])>.7 or not 0<=p[0]<=12:return 3.
    blend=min(1.,p[0]/2,(12-p[0])/2)
    blend=blend*blend*(3-2*blend)
    return 3.-1.56*blend


def boundaries(points,yaws):
    return [[(p[0]-side*lane_half_width(p)*math.sin(y),p[1]+side*lane_half_width(p)*math.cos(y)) for p,y in zip(points,yaws)] for side in (-1,1)]


def check_boundary(points,yaws,modes):
    lines=boundaries(points,yaws); bounds=sweep_bounds(points,yaws)
    segments=[]
    for line in lines:
        segments.extend((a,b) for i,(a,b) in enumerate(zip(line,line[1:])) if modes[i]=='painted')
    lowest=math.inf
    for p,yaw,pad in zip(points,yaws,bounds):
        body=box(*p,yaw,-1.1,.6,-.5,.5)
        reach=max(4.,BODY_RADIUS+pad+MARGIN)
        for a,b in segments:
            if (p[0]<min(a[0],b[0])-reach or p[0]>max(a[0],b[0])+reach or
                    p[1]<min(a[1],b[1])-reach or p[1]>max(a[1],b[1])+reach):continue
            distance=polygon_distance(body,[a,b])
            lowest=min(lowest,distance-pad)
            if distance-pad<MARGIN:return False,lowest
    return True,lowest


def generate(seed=2027,difficulty='normal',base=None):
    if difficulty not in ('easy','normal','hard'):raise ValueError('Unknown difficulty')
    if base is None:base=json.loads((ROOT/'ros2/src/igvc_gps/config/full_loop.json').read_text())
    rng=random.Random(seed)
    original, modes=resample(base['route']['dense_xy'],base['route']['dense_modes'])
    ss=arcs(original); yaws=headings(original)
    amplitude=rng.uniform(1.,2.); phase=rng.uniform(-math.pi,math.pi); wavelength=rng.uniform(28.,40.)
    # Bounded fallback progressively reduces shape change, never geometry clearance.
    for multiplier in (1.,.75,.5,.25,0.):
        shaped=[]
        for p,s,yaw in zip(original,ss,yaws):
            near=min(s,ss[-1]-s)
            blend=max(0.,min(1.,(near-8)/12));blend=blend*blend*(3-2*blend)
            offset=amplitude*multiplier*blend*math.sin(2*math.pi*s/wavelength+phase)
            x,y=p[0]-math.sin(yaw)*offset,p[1]+math.cos(yaw)*offset
            start_blend=max(0.,min(1.,(near-3)/5));start_blend=start_blend**2*(3-2*start_blend)
            opening=max(0.,min(1.,(s-12)/12));opening=opening*opening*(3-2*opening)
            shaped.append((x,y*start_blend*opening))
        points,route_modes=resample(shaped,modes)
        yaw=headings(points)
        good,boundary_margin=check_boundary(points,yaw,route_modes)
        if good:break
    else:raise ValueError('Base geometry cannot provide the required painted-boundary clearance')
    # Insert exact opening anchors into the dense route; no nearest-point jumps.
    for x, _ in RAMP_CHECKPOINTS:
        candidates=[i for i,(a,b) in enumerate(zip(points,points[1:]))
                    if a[0] <= x <= b[0] and abs(a[1])<1e-9 and abs(b[1])<1e-9]
        if not candidates:raise ValueError('Opening cannot traverse the default ramp center')
        i=candidates[0]
        if math.dist(points[i],(x,0.))>1e-8 and math.dist(points[i+1],(x,0.))>1e-8:
            points.insert(i+1,(x,0.));route_modes.insert(i+1,route_modes[i])
    yaw=headings(points)
    ss=arcs(points); sweep=sweep_bounds(points,yaw)
    ramp=dict(DEFAULT_RAMP)
    reserved=box(ramp['x'],ramp['y'],ramp['yaw'],-1.,9.,-2.,2.)
    for p in points:
        if 2 <= p[0] <= 10 and abs(p[1])<2 and abs(p[1])>=.65:
            raise ValueError('Route enters ramp reservation away from center')
    counts={'easy':(16,4,1),'normal':(24,8,2),'hard':(36,12,3)}[difficulty]
    obstacles=[]; obstacle_margins=[]
    for kind,count in zip(('barrel','barricade','pothole'),counts):
        for index in range(count):
            for attempt in range(1000):
                i=rng.randrange(1,len(points)-1)
                if min(ss[i],ss[-1]-ss[i])<10:continue
                side=rng.choice((-1,1));lateral=side*rng.uniform(2.05,2.35)
                diameter=rng.uniform(.7,1.1) if kind=='pothole' else .6
                o=dict(id=f'{kind}-{index+1:03}',kind=kind,
                       x=points[i][0]-math.sin(yaw[i])*lateral,y=points[i][1]+math.cos(yaw[i])*lateral,
                       yaw=yaw[i]+(math.pi/2 if kind=='barricade' else 0.),
                       length=1.5 if kind=='barricade' else diameter,
                       width=.25 if kind=='barricade' else diameter,
                       height=.8 if kind=='barricade' else (.9 if kind=='barrel' else 0.),
                       depth=rng.uniform(.12,.25) if kind=='pothole' else 0.)
                # Include the full synthetic pothole cutout/rim, not just bowl diameter.
                if kind=='barricade':
                    if polygon_distance(reserved,obstacle_box(o))<=0:continue
                else:
                    radius=max(o['length'],o['width'])/2+.85 if kind=='pothole' else o['width']/2
                    reservation=dict(x=6.,y=0.,yaw=0.,length=10.,width=4.)
                    if point_box((o['x'],o['y']),reservation)<=radius:continue
                if any(obstacle_distance(o,b)<MARGIN for b in obstacles):continue
                conservative=math.inf
                for p,angle,pad in zip(points,yaw,sweep):
                    reach=max(4.,BODY_RADIUS+pad+math.hypot(o['length'],o['width'])/2+MARGIN)
                    if math.hypot(o['x']-p[0],o['y']-p[1])>reach:continue
                    conservative=min(conservative,body_clearance(p,angle,o)-pad)
                if conservative<MARGIN:continue
                obstacles.append(o);obstacle_margins.append(conservative);break
            else:raise ValueError(f'Bounded placement exhausted for {kind}; no unsafe fallback')
    course=dict(schema_version=1,seed=seed,difficulty=difficulty,units='m',frame='odom',lane_width_m=6.,
                camera_pitch_rad=.1745329252,
                centerline=[dict(x=p[0],y=p[1],painted=m=='painted',half_width=lane_half_width(p)) for p,m in zip(points,route_modes)],
                obstacles=obstacles,ramps=[ramp],
                generation=dict(shape_amplitude_m=amplitude*multiplier,shape_fallback_multiplier=multiplier,
                                clearance_margin_m=MARGIN,footprint=[-1.1,.6,-.5,.5],
                                boundary_conservative_clearance_m=boundary_margin,
                                obstacle_conservative_clearance_m=min(obstacle_margins),
                                clearance_model='Oriented rectangles/circles; endpoint distance minus translation+angular sweep bound. No contact physics.'))
    frame=LocalFrame(base['origin']);goals=[]
    count=math.ceil(ss[-1]/2)
    for j in range(1,count+1):
        target=ss[-1]*j/count;i=min(range(len(ss)),key=lambda k:abs(ss[k]-target));p=points[i]
        lat,lon,alt=frame.to_geodetic(*p)
        goals.append(dict(name=f'variant_{j:03}',latitude=lat,longitude=lon,altitude=alt,yaw=yaw[i],
                          odom_xy=p,route_s_m=ss[i],mode=route_modes[i]))
    # Remove nearby regular samples, then merge required ramp poses by route arc.
    critical=[]
    for x,label in RAMP_CHECKPOINTS:
        i=next(i for i,p in enumerate(points) if math.dist(p,(x,0.))<1e-8)
        lat,lon,alt=frame.to_geodetic(x,0.)
        critical.append(dict(name='ramp_001_'+label,latitude=lat,longitude=lon,altitude=alt,
                             yaw=0.,odom_xy=(x,0.),route_s_m=ss[i],mode=route_modes[i],
                             ramp_id=ramp['id'],ramp_checkpoint=label))
    goals=[g for g in goals if all(abs(g['route_s_m']-c['route_s_m'])>.4 for c in critical)]
    goals=sorted(goals+critical,key=lambda g:g['route_s_m'])
    goals[-1].update(odom_xy=[0.,0.],yaw=0.)
    mission=dict(origin=base['origin'],seed=seed,difficulty=difficulty,waypoints=goals,
                 route=dict(frame='odom',dense_xy=points,dense_s_m=ss,dense_modes=route_modes,length_m=ss[-1]),
                 note='Procedural guide route, not an input to perception; ideal geometric clearance only.')
    return course,mission


def render(course,path):
    from PIL import Image,ImageDraw
    points=[(p['x'],p['y']) for p in course['centerline']]
    xmin=min(p[0] for p in points)-5;ymax=max(p[1] for p in points)+5
    spanx=max(p[0] for p in points)-xmin+5;spany=ymax-min(p[1] for p in points)+5
    scale=min(1050/spanx,1100/spany)
    def px(p):return (int(65+(p[0]-xmin)*scale),int(85+(ymax-p[1])*scale))
    image=Image.new('RGB',(1200,1300),'#eceee7');draw=ImageDraw.Draw(image)
    lines=boundaries(points,headings(points))
    for i in range(len(points)-1):
        draw.polygon([px(lines[0][i]),px(lines[0][i+1]),px(lines[1][i+1]),px(lines[1][i])],fill='#c3c9b6')
        if course['centerline'][i]['painted']:
            for line in lines:draw.line([px(line[i]),px(line[i+1])],fill='white',width=3)
    for ramp in course.get('ramps',[]):
        length=2*ramp['rise_length']+ramp['deck_length']
        outline=box(ramp['x'],ramp['y'],ramp['yaw'],0.,length,-ramp['width']/2,ramp['width']/2)
        draw.polygon([px(p) for p in outline],fill='#d6bd80',outline='#806529')
        draw.text(px((ramp['x'],ramp['y']-ramp['width']/2-.4)),
                  f"{ramp['id']} {ramp['height']:.2f} m",fill='#604710')
    draw.line([px(p) for p in points],fill='#426ba5',width=2)
    for o in course['obstacles']:
        color={'barrel':'#d86a25','barricade':'#b33427','pothole':'#48494a'}[o['kind']]
        if o['kind']=='barricade':draw.polygon([px(p) for p in obstacle_box(o)],fill=color)
        else:
            x,y=px((o['x'],o['y']));r=o['width']*scale/2;draw.ellipse((x-r,y-r,x+r,y+r),fill=color)
    x,y=px((0,0));draw.text((x,y+8),'START / FINISH +X',fill='black')
    draw.text((40,20),f"Seed {course['seed']} | {course['difficulty']} | 6 m lane | orange barrels / red barricades / grey potholes",fill='black')
    draw.text((40,42),'Blue: clearance-checked guide. White: painted boundaries. Unmarked section retains camera processing.',fill='black')
    image.save(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=2027)
    parser.add_argument('--difficulty',choices=('easy','normal','hard'),default='normal')
    args=parser.parse_args();course,mission=generate(args.seed,args.difficulty)
    output=ROOT/f'artifacts/courses/seed-{args.seed}';output.mkdir(parents=True,exist_ok=True)
    if (output/'run.json').exists():
        import datetime, shutil
        archive=output/('previous-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        archive.mkdir()
        for name in ('course.json','mission.json','overview.png','run.json','validation.json','sensors.json','unity.log','hazard-rgb.png','hazard-mask.png'):
            if (output/name).is_file():shutil.copy2(output/name,archive/name)
        # The previous run is retained in the archive; a new layout has no run yet.
        for name in ('run.json','validation.json','sensors.json'):
            if (output/name).is_file():(output/name).unlink()
    (output/'course.json').write_text(json.dumps(course,indent=2)+'\n')
    import hashlib
    mission['course_sha256']=hashlib.sha256((output/'course.json').read_bytes()).hexdigest()
    (output/'mission.json').write_text(json.dumps(mission,indent=2)+'\n')
    render(course,output/'overview.png')
    print(json.dumps(dict(output=str(output),obstacles=len(course['obstacles']),waypoints=len(mission['waypoints']),
                         length_m=mission['route']['length_m'],generation=course['generation']),indent=2))


if __name__=='__main__':main()
