"""Render recorded route/trajectory data; never commands the robot."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

root=Path(__file__).resolve().parents[1]
mission=json.loads((root/'ros2/src/igvc_gps/config/full_loop.json').read_text())
run=json.loads((root/'artifacts/checks/full-course-live.json').read_text())
geometry=json.loads((root/'artifacts/checks/course-route.json').read_text())
canvas=Image.new('RGB',(1100,1400),'white');draw=ImageDraw.Draw(canvas)
def pixel(p):return (round(240+p[0]*23),round(1250-p[1]*23))
for x in range(-5,36,5):
    draw.line([pixel((x,-3)),pixel((x,47))],fill='#e8ebed')
    draw.text(pixel((x,-4)),str(x)+' m',fill='black')
for y in range(0,46,5):
    draw.line([pixel((-6,y)),pixel((35,y))],fill='#e8ebed')
    draw.text(pixel((-8,y)),str(y)+' m',fill='black')
draw.line([pixel(p) for p in mission['route']['dense_xy']],fill='#bbcdf3',width=5)
for b in geometry['barrel_instances']:
    x,y=pixel(b['xy']);draw.ellipse((x-6,y-6,x+6,y+6),fill='#dc792a')
for index,p in enumerate(mission['waypoints'],1):
    x,y=pixel(p['odom_xy']);draw.ellipse((x-3,y-3,x+3,y+3),fill='#245ca6')
    if index%5==0:draw.text((x+5,y+4),str(index),fill='#245ca6')
if len(run['trajectory'])>1:
    draw.line([pixel(p[1:3]) for p in run['trajectory']],fill='#168452',width=3)
x,y=pixel((0,0));draw.ellipse((x-7,y-7,x+7,y+7),outline='black',width=2)
draw.text((x-40,y+15),'START / FINISH',fill='black')
draw.text((40,25),'IGVC FULL-LOOP RUN: '+run['status'].upper(),fill='black')
draw.text((40,48),f"{run['completed_waypoints']}/{run['total_waypoints']} ordered goals; {run['audit']['traveled_m']:.2f} m driven; {100*run['audit']['fraction']:.2f}% route progress",fill='black')
draw.text((40,71),'Blue: route/numbered guide points    Green: recorded odometry    Orange: barrels',fill='black')
draw.text((40,94),'Synthetic GPS and ideal odometry. Development pauses are retained in the JSON report.',fill='black')
canvas.save(root/'artifacts/checks/full-course-trajectory.png')
