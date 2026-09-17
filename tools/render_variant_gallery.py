"""Plot saved course geometry and measured trajectories; never controls ROS."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from generate_course_variant import boundaries, headings, obstacle_box

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds',type=int,nargs='+',default=[2027,2028,2029])
    args=parser.parse_args()
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font=ImageFont.truetype(font_path,17)
    title=ImageFont.truetype(font_path,24)
    image=Image.new('RGB',(540*len(args.seeds),900),'#f4f6f8')
    draw=ImageDraw.Draw(image)
    summary=[]
    for panel,seed in enumerate(args.seeds):
        folder=ROOT/f'artifacts/courses/seed-{seed}'
        course=json.loads((folder/'course.json').read_text())
        run=json.loads((folder/'run.json').read_text()) if (folder/'run.json').exists() else {}
        audit=json.loads((folder/'validation.json').read_text()) if (folder/'validation.json').exists() else {}
        pts=[(p['x'],p['y']) for p in course['centerline']]
        xmin=min(p[0] for p in pts)-4;ymax=max(p[1] for p in pts)+4
        scale=min(470/(max(p[0] for p in pts)-xmin+4),615/(ymax-min(p[1] for p in pts)+4))
        def px(p):return (panel*540+35+(p[0]-xmin)*scale,130+(ymax-p[1])*scale)
        ramp=course.get('ramps',[None])[0]
        ramp_center=(ramp['x']-ramp['rise_length']-ramp['deck_length']/2) if ramp else 14.
        left,right=boundaries(pts,headings(pts),ramp_center)
        for i in range(len(pts)-1):
            draw.polygon([px(left[i]),px(left[i+1]),px(right[i+1]),px(right[i])],fill='#bdc5ba')
            if course['centerline'][i]['painted'] and course['centerline'][i+1]['painted']:
                for edge in (left,right):draw.line([px(edge[i]),px(edge[i+1])],fill='white',width=2)
        draw.line([px(p) for p in pts],fill='#81918d',width=1)
        for o in course['obstacles']:
            color=o.get('color','orange') if o['kind']=='barrel' else {'barricade':'#c04032','pothole':'#20262d'}[o['kind']]
            if o['kind']=='barricade':draw.polygon([px(p) for p in obstacle_box(o)],fill=color)
            else:
                x,y=px((o['x'],o['y']));r=max(2,o['width']*scale/2)
                draw.ellipse((x-r,y-r,x+r,y+r),fill=color)
        trajectory=run.get('trajectory',[])
        if len(trajectory)>1:draw.line([px(p[1:3]) for p in trajectory],fill='#1265c7',width=3)
        x,y=px((0,0));draw.rectangle((x-4,y-4,x+4,y+4),fill='#143e72')
        draw.text((x+8,y-9),'Start / finish',font=font,fill='#143e72')
        passed=audit.get('passed',False)
        draw.text((panel*540+25,20),f"Seed {seed} / {course['difficulty']}",font=title,fill='#182536')
        draw.text((panel*540+25,57),'PASS' if passed else run.get('status','NOT RUN').upper(),font=title,fill='#167248' if passed else '#a54a21')
        n=run.get('completed_waypoints',0);total=run.get('total_waypoints','?')
        clearance=audit.get('minimum_sampled_clearance') or {}
        draw.text((panel*540+25,765),f"{n}/{total} checkpoints | {len(course['obstacles'])} obstacles",font=font,fill='#26364b')
        if passed:
            draw.text((panel*540+25,793),f"Min clearance {clearance['clearance_m']:.2f} m | max {audit['maximum_chord_speed_mps']:.2f} m/s",font=font,fill='#26364b')
            draw.text((panel*540+25,821),f"Finish error {audit['final_distance_to_origin_m']:.2f} m | line blocks {audit['line_blocks']}",font=font,fill='#26364b')
        summary.append({'seed':seed,'difficulty':course['difficulty'],'validation':audit})
    draw.text((25,868),'Blue: measured trajectory. Orange: barrels. Red: barricades. Black: potholes. Ideal planar motion; no contact physics.',font=font,fill='#45566c')
    out=ROOT/'artifacts/courses'
    image.save(out/'variant-comparison.png')
    (out/'validation-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'variant-comparison.png')


if __name__=='__main__':main()
