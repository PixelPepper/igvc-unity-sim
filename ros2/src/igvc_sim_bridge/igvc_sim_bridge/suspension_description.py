"""Add simulation-only suspension sliders without changing the canonical CAD URDF."""
import math
import xml.etree.ElementTree as ET


def with_caster_suspension(description, joint_limit):
    if not math.isfinite(joint_limit) or not 0 < joint_limit <= .1:
        raise ValueError('Invalid provisional caster joint travel')
    robot = ET.fromstring(description)
    for side in ('left', 'right'):
        caster = robot.find(f"joint[@name='{side}Caster']")
        if caster is None or caster.find('parent').get('link') != 'base_link':
            raise ValueError('Expected canonical rear caster joint')
        slider_link = f'{side}_caster_suspension_link'
        ET.SubElement(robot, 'link', name=slider_link)
        slider = ET.SubElement(robot, 'joint', name=f'{side}_caster_suspension_joint', type='prismatic')
        origin = caster.find('origin')
        caster.remove(origin)
        slider.append(origin)
        ET.SubElement(slider, 'parent', link='base_link')
        ET.SubElement(slider, 'child', link=slider_link)
        ET.SubElement(slider, 'axis', xyz='0 0 1')
        ET.SubElement(slider, 'limit', lower=str(-joint_limit), upper=str(joint_limit), effort='1000', velocity='10')
        caster.find('parent').set('link', slider_link)
        ET.SubElement(caster, 'origin', xyz='0 0 0', rpy='0 0 0')
    return ET.tostring(robot, encoding='unicode')
