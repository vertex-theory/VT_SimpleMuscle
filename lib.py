import maya.cmds as cmds

import json


def setup(joints, num_joints=1, parent=None, bulge=None, sink=None, triggerLength=None, type=0):
    rig=create_rig_hierarchy(joints[0])
    curves=create_curves(joints)
    typeName = 'Linear'
    if type == 1:
        typeName = 'Cubic'
    surface = create_surface(curves, joints[0], rig, typeName)

    if '_R' in joints[0]:
        right_side = True
    else:
        right_side = False
    def_joints = joints_on_surface(surface, joints[0], rig, num_joints, parent, right_side, bulge, sink, triggerLength)
    return (def_joints)

def create_curves(joints, dir='Z', offsetPercentLength = 10):
    joint_positions = []
    curves = []
    for j in joints:
        joint_positions.append(cmds.xform(j, q=True, rp=True, ws=True))
    curves.append(cmds.curve(p=joint_positions, n=f'{joints[0]}_curveA', d=1))
    curves.append(cmds.curve(p=joint_positions, n=f'{joints[0]}_curveB', d=1))

    offset=get_chain_length(joints)*(offsetPercentLength*0.01)
    tmp = cmds.duplicate(joints[0], po=True)[0]

    cmds.skinCluster(tmp, curves[0])
    cmds.skinCluster(tmp, curves[1])

    cmds.parent(tmp, joints[0])
    cmds.setAttr(f'{tmp}.translate{dir}', offset)
    cmds.delete(curves[0], ch=True)

    cmds.setAttr(f'{tmp}.translate{dir}', offset*-1.0)
    cmds.delete(curves[1], ch=True)

    cmds.delete(tmp)

    return(curves)

def get_chain_length(joints):
    for a in ['.tx','.ty','.tz']:
        val=cmds.getAttr(f'{joints[1]}{a}')
        if val != 0.0:
            return val

def create_surface(curves, name_base, rig, type='Linear'):
    if type == 'Linear':
        degree = 1
    else:
        degree = 3
    surface = cmds.loft(curves[0], curves[1], d=degree, ch=False, ss=1, n=f'{name_base}_surface')[0]
    cmds.rebuildSurface(surface, ch=False, rpo=True, rt=0, end=1, kr=0, kcp=False, kc=False, su=1, du=degree, sv=1, dv=degree,
                        tol=0.01, fr=0, dir=2)
    cmds.reverseSurface(surface, ch=False, rpo=True, d=3)

    shape = cmds.listRelatives(surface, s=True)[0]

    # turn on origins
    cmds.setAttr(f'{shape}.dispOrigin', 1)
    cmds.setAttr(f'{shape}.normalsDisplayScale', 0.1)

    if '_R' in name_base:
        cmds.reverseSurface(surface, ch=False, rpo=True, d=3)
        cmds.reverseSurface(surface, ch=False, rpo=True, d=1)
        cmds.reverseSurface(surface, ch=False, rpo=True, d=3)

    try:
        cmds.delete(curves)
    except:
        pass

    cmds.parent(surface, rig)
    return(surface)

def joints_on_surface(surface, base_name, rig, num_joints=1, parent=None, right_side=False, bulge=None, sink=None, triggerLength=None):
    section_size = 1/(num_joints+1)
    surfaceShape = cmds.listRelatives(surface, s=True)[0]

    follicle_transforms = []
    skin_joints = []
    follicle_shapes = []

    follicle_positions = []
    for i in range(num_joints):
        follicle_positions.append((i + 1) * section_size)
    if right_side:
        # reverse for the right side since the surface is reversed
        follicle_positions.reverse()

    for i in range(num_joints):

        folShape = cmds.createNode('follicle', n=f'{base_name}_follicle_{i+1}')
        folTransTemp = cmds.listRelatives(folShape, p=True)[0]
        folTrans = cmds.rename(folTransTemp, f'{folShape}Trans')
        cmds.parent(folTrans, rig)
        cmds.setAttr(f'{folTrans}.visibility', 0)
        cmds.connectAttr(f'{surfaceShape}.local', f'{folShape}.inputSurface')
        cmds.connectAttr(f'{surfaceShape}.worldMatrix[0]', f'{folShape}.inputWorldMatrix')
        cmds.connectAttr(f'{folShape}.outRotate', f'{folTrans}.rotate')
        cmds.connectAttr(f'{folShape}.outTranslate', f'{folTrans}.translate')
        follicle_transforms.append(follicle_transforms)
        follicle_shapes.append(folShape)

        cmds.setAttr(f'{folShape}.parameterV',0.5)
        cmds.setAttr(f'{folShape}.parameterU', follicle_positions[i])

        skin_joints.append(cmds.createNode('joint', n=f'{base_name}_{i+1}_skin_jnt'))
        constraint = cmds.parentConstraint(folTrans, skin_joints[i], mo=False)[0]
        cmds.parent(constraint, rig)

        cmds.addAttr(f'{skin_joints[i]}', ln='isMuscleJoint', at='bool', dv=True, h=True, k=False)
        cmds.addAttr(f'{skin_joints[i]}', ln='parent', dt='string', h=False)
        if parent:
            cmds.setAttr(f'{skin_joints[i]}.parent', parent, type='string')

    create_flex(surface, skin_joints, base_name, rig, follicle_shapes, bulge, sink, triggerLength)
    return(skin_joints)

def create_flex(surface, joints, base_name, rig, follicleShapes, bulge, sink, triggerLength):
    surfaceShape = cmds.listRelatives(surface, s=True)[0]
    arclength = cmds.createNode('arcLengthDimension', n=f'{base_name}_arcLength')
    arclengthTrans = cmds.listRelatives(arclength, p=True)[0]
    cmds.setAttr(f'{arclengthTrans}.visibility', 0)
    cmds.parent(arclengthTrans, rig)
    cmds.setAttr(f'{arclength}.uParamValue', 1.0)

    cmds.addAttr(surface, ln='length', at='float', h=True, k=False)
    cmds.connectAttr(f'{surfaceShape}.worldSpace[0]', f'{arclength}.nurbsGeometry')
    cmds.connectAttr(f'{arclength}.arcLength', f'{surface}.length')

    #divide current length by the orig length to get a stretch factor and multiply by scale factor
    scale_reader = create_scale_reader()
    divide = cmds.createNode('multiplyDivide', n=f'{base_name}_divide')
    cmds.setAttr(f'{divide}.operation',2)
    cmds.connectAttr(f'{surface}.length', f'{divide}.input1X')

    current_length = cmds.getAttr(f'{surface}.length')
    scale_multiply = cmds.createNode('multDoubleLinear', n=f'{base_name}_scale_multiply')
    cmds.setAttr(f'{scale_multiply}.input2', current_length)
    cmds.connectAttr(f'{scale_reader}.scaleX', f'{scale_multiply}.input1')
    cmds.connectAttr(f'{scale_multiply}.output', f'{divide}.input2X')
    cmds.addAttr(surface, ln='factor', at='float', h=True, k=False)
    cmds.connectAttr(f'{divide}.outputX', f'{surface}.factor')

    #have that drive a setup where the joints start in a neutral position and when
    #the surface stretches the joints sink in and when it compresses they push out
    cmds.addAttr(surface, ln='bulge', at='float', h=False, k=True)
    cmds.addAttr(surface, ln='sink', at='float', h=False, k=True)
    # calculate default values as a percentage of muscle length
    default = (cmds.getAttr(f'{surface}.length')*0.18)
    if bulge == None:
        bulge_value = (cmds.getAttr(f'{surface}.length')*0.18)
    else:
        bulge_value = bulge

    if sink == None:
        sink_value = (cmds.getAttr(f'{surface}.length')*0.18)*0.5
    else:
        sink_value = sink

    cmds.setAttr(f'{surface}.bulge', bulge_value)
    cmds.setAttr(f'{surface}.sink', sink_value)

    if triggerLength == None:
        triggerLength_value = 0.6
    else:
        triggerLength_value = triggerLength

    # cmds.setAttr(f'{surface}.bulge', default)
    # cmds.setAttr(f'{surface}.sink', (default*0.5))

    # add trigger attr for when the shape fires

    cmds.addAttr(surface, ln='triggerLength', at='float', h=False, k=True, min=0.0, max=1.0, dv=triggerLength_value)

    #drive offset on joints
    calculate_offset_factor(joints, follicleShapes, surface)

    # use a remap value node and some math nodes to drive the muscle flex and stretch
    for i in range(len(joints)):

        # above stretch factor of 1.0
        remapAbove = cmds.createNode('remapValue', n=f'{joints[i]}_remapAboveZero')
        cmds.setAttr(f'{remapAbove}.inputMin', 1.0)
        cmds.setAttr(f'{remapAbove}.outputMin', 0.0)

        zeroMinueSink = cmds.createNode('plusMinusAverage', n=f'{joints[i]}_zeroMinusSink')
        cmds.setAttr(f'{zeroMinueSink}.input1D[0]', 0.0)
        cmds.connectAttr(f'{surface}.sink', f'{zeroMinueSink}.input1D[1]')
        cmds.setAttr(f'{zeroMinueSink}.operation', 2)

        sinkTimesMult = cmds.createNode('multDoubleLinear', n=f'{joints[i]}_sinkTimesMult')
        cmds.connectAttr(f'{zeroMinueSink}.output1D', f'{sinkTimesMult}.input1')
        cmds.connectAttr(f'{surface}.{joints[i]}', f'{sinkTimesMult}.input2')

        onePlusTrigger = cmds.createNode('addDoubleLinear', n=f'{joints[i]}onePlusTrigger')
        cmds.connectAttr(f'{surface}.triggerLength', f'{onePlusTrigger}.input1')
        cmds.setAttr(f'{onePlusTrigger}.input2', 1.0)

        cmds.connectAttr(f'{sinkTimesMult}.output', f'{remapAbove}.outputMax')
        cmds.connectAttr(f'{onePlusTrigger}.output', f'{remapAbove}.inputMax')
        cmds.connectAttr(f'{surface}.factor', f'{remapAbove}.inputValue')

        # below a stretch factor of 1.0
        remapBelow = cmds.createNode('remapValue', n=f'{joints[i]}_remapBelowZero')
        cmds.setAttr(f'{remapBelow}.inputMax', 1.0)
        cmds.setAttr(f'{remapBelow}.outputMax', 0.0)
        cmds.connectAttr(f'{surface}.triggerLength', f'{remapBelow}.inputMin')

        bulgeTimesMult = cmds.createNode('multDoubleLinear', n=f'{joints[i]}_bulgeTimesMult')
        cmds.connectAttr(f'{surface}.bulge', f'{bulgeTimesMult}.input1')
        cmds.connectAttr(f'{surface}.{joints[i]}', f'{bulgeTimesMult}.input2')

        cmds.connectAttr(f'{bulgeTimesMult}.output', f'{remapBelow}.outputMin')

        cmds.connectAttr(f'{surface}.factor', f'{remapBelow}.inputValue')

        # setup condition node
        condition = cmds.createNode('condition', n=f'{joints[i]}_condition')
        cmds.connectAttr(f'{surface}.factor', f'{condition}.firstTerm')
        cmds.setAttr(f'{condition}.secondTerm', 1.0)
        cmds.setAttr(f'{condition}.operation', 3)
        cmds.connectAttr(f'{remapBelow}.outValue', f'{condition}.colorIfFalseR')
        cmds.connectAttr(f'{remapAbove}.outValue', f'{condition}.colorIfTrueR')

        constraint = f'{joints[i]}_parentConstraint1'
        cmds.connectAttr(f'{condition}.outColorR', f'{constraint}.target[0].targetOffsetTranslateZ')

    # add normalized driver value to drive corrective shapes with
    cmds.addAttr(surface, ln='shapeDriver', at='float', h=False, k=True)
    shape_remap = cmds.createNode('remapValue', n=f'{base_name}_shape_remap')
    cmds.connectAttr(f'{surface}.triggerLength', f'{shape_remap}.inputMax')
    cmds.setAttr(f'{shape_remap}.inputMin', 1.0)
    cmds.connectAttr(f'{surface}.factor', f'{shape_remap}.inputValue')
    cmds.connectAttr(f'{shape_remap}.outValue', f'{surface}.shapeDriver')

def calculate_offset_factor(joints, follicles, surface):
    curve = cmds.createNode('animCurveTA')
    cmds.setKeyframe(curve, t=0, v=0, itt='spline', ott='spline')
    cmds.setKeyframe(curve, t=0.5, v=1, itt='spline', ott='spline')
    cmds.setKeyframe(curve, t=1.0, v=0, itt='spline', ott='spline')
    cmds.keyTangent(curve, e=True, a=True, t=(0, 0), oa=2.7, ow=1.0)
    cmds.keyTangent(curve, e=True, a=True, t=(1.0, 1.0), oa=-2.7, ow=1.0)

    for i in range(len(joints)):
        position = cmds.getAttr(f'{follicles[i]}.parameterU')
        calc_value = cmds.keyframe('animCurveTA1', q=True, ev=True, t=(position,position))[0]
        cmds.addAttr(surface, ln=f'{joints[i]}', at='float', h=True, k=False, dv=calc_value)

    cmds.delete(curve)

def create_rig_hierarchy(base_name):
    rig=cmds.createNode('transform', n=f'{base_name}_rig')
    cmds.setAttr(f'{rig}.inheritsTransform', 0)
    cmds.addAttr(f'{rig}', ln='muscleRig', at='bool', k=False, h=True)
    return (rig)

def create_muscle(muscle_name, parent, number_jnts, type='Linear'):
    if muscle_name == '':
        cmds.error('you need to enter a valid muscle rig name like "Bicep_L"')
        return()
    if parent == '':
        cmds.error('you need to enter a valid parent in the "Set Muscle Rig Parent" text field')
        return ()


    jointA = cmds.createNode('joint', n=muscle_name)
    cmds.setAttr(f'{jointA}.radius', 2)
    cmds.setAttr(f'{jointA}.displayLocalAxis', True)
    cmds.setAttr(f'{jointA}.overrideEnabled', 1)
    cmds.setAttr(f'{jointA}.overrideColor', 4)
    cmds.addAttr(f'{jointA}', ln='parent', dt='string', h=False)
    cmds.setAttr(f'{jointA}.parent', parent, type='string', cb=True)
    cmds.addAttr(f'{jointA}', ln='numJoints', at='short', h=False, k=False)
    cmds.setAttr(f'{jointA}.numJoints', number_jnts, cb=True)
    cmds.addAttr(f'{jointA}', ln='surfType', at='enum', en='Linear:Cubic', h=False, k=False)

    if type == 'Linear':
        typeVal = 0
    else:
        typeVal = 1

    cmds.setAttr(f'{jointA}.surfType', typeVal, cb=True)

    cmds.addAttr(f'{jointA}', ln='bulge', at='float', h=False, k=False)
    cmds.addAttr(f'{jointA}', ln='sink', at='float', h=False, k=False)
    cmds.addAttr(f'{jointA}', ln='triggerLength', at='float', h=False, k=False)

    jointB = cmds.createNode('joint', n=f'{muscle_name}_End')
    cmds.setAttr(f'{jointB}.radius', 2)
    cmds.parent(jointB, jointA)
    cmds.setAttr(f'{jointB}.translateX', 10)

    # lock and hide attrs on end bone
    for attr in ['.ty', '.tz', '.rx', '.ry', '.rz', '.sx', '.sy', '.sz', '.visibility', '.radius']:
        cmds.setAttr(f'{jointB}{attr}', k=False, cb=False, l=True)

def mirror_guides():
    to_mirror = []
    selection = cmds.ls(sl=True)
    if selection:
        for item in selection:
            if check_for_attr(item, 'parent', 'joint'):
                to_mirror.append(item)
    else:
        all_joints = cmds.ls(type='joint')
        for joint in all_joints:
            if '_L' or '_l' in joint and check_for_attr(joint, 'parent', 'joint'):
                to_mirror.append(joint)

    for guide in to_mirror:
        if '_L' in guide:
            right_guide = cmds.mirrorJoint(guide, sr =['_L','_R'], myz=True, mb=True)[0]
        elif '_l' in guide:
            right_guide = cmds.mirrorJoint(guide, sr=['_l', '_r'], myz=True, mb=True)[0]

        # mirror parent attr
        parent_left = cmds.getAttr(f'{guide}.parent')
        if '_L' in guide:
            parent_right = parent_left.replace('_L','_R')
        elif '_l' in guide:
            parent_right = parent_left.replace('_l', '_r')

        if cmds.objExists(parent_right):
            cmds.setAttr(f'{right_guide}.parent', parent_right, type='string')
        else:
            print(f"the right side parent for {right_guide} doesnt exist. Setting to nothing")
            cmds.setAttr(f'{right_guide}.parent', '', type='string')

def mirror_rig_settings():
    objs = cmds.ls('*_surface')
    to_mirror = []
    for o in objs:

        if '_L' in o and check_for_attr(o, 'bulge'):
            to_mirror.append(o)

    for surface in to_mirror:
        bulge = cmds.getAttr(f'{surface}.bulge')
        sink = cmds.getAttr(f'{surface}.sink')
        triggerLength = cmds.getAttr(f'{surface}.triggerLength')
        right_surface = surface.replace('_L', '_R')
        cmds.setAttr(f'{right_surface}.bulge', bulge)
        cmds.setAttr(f'{right_surface}.sink', sink)
        cmds.setAttr(f'{right_surface}.triggerLength', triggerLength)

def check_for_attr(toCheck, attr, type=None):
    attrs = cmds.listAttr(toCheck, ud=True)
    objectType = cmds.objectType(toCheck)

    if attrs:
        if type:
            if objectType == type and attr in attrs:
                return True
        else:
            if attr in attrs:
                return True
    else:
        return False

def create_scale_reader():
    reader = 'Scale_Constrain_To_Rig'
    # check if one exists
    if cmds.objExists('Scale_Constrain_To_Rig'):
        return (reader)
    else:
        cmds.createNode('transform', n=reader)
        return (reader)

def select_def_joints():
    all_joints = cmds.ls(type='joint')
    def_joints = []
    for joint in all_joints:
        if check_for_attr(joint, 'isMuscleJoint'):
            def_joints.append(joint)
    cmds.select(def_joints)

def parent_def_joints():
    all_joints = cmds.ls(type='joint')
    for joint in all_joints:
        if check_for_attr(joint, 'isMuscleJoint'):
            try:
                parent = cmds.getAttr(f'{joint}.parent')
                cmds.parent(joint, parent)
            except:
                print(f'{joint} either has no parent set or is already a child of the parent')

def unparent_def_joints():
    all_joints = cmds.ls(type='joint')
    for joint in all_joints:
        if check_for_attr(joint, 'isMuscleJoint', 'joint'):
            try:
                cmds.parent(joint, w=True)
            except:
                print(f'{joint} is already a child of the world')

def build_all_rigs():
    # either builds on selected joints only or all joints
    selection = cmds.ls(sl=True, type='joint')
    if len(selection) == 0:
        all_joints = cmds.ls(type='joint')
    else:
        all_joints = selection

    for joint in all_joints:
        if check_for_attr(joint, 'parent'):
            parent = cmds.getAttr(f'{joint}.parent')
            num_joints = cmds.getAttr(f'{joint}.numJoints')
            end_joint = cmds.listRelatives(joint, c=True)[0]

            bulge = cmds.getAttr(f'{joint}.bulge')
            sink = cmds.getAttr(f'{joint}.sink')
            triggerLength = cmds.getAttr(f'{joint}.triggerLength')
            type = cmds.getAttr(f'{joint}.surfType')

            if triggerLength == 0.0:
                def_joints = setup([joint,end_joint], num_joints, parent, None, None, None, type=type)
            else:
                def_joints = setup([joint, end_joint], num_joints, parent, bulge, sink, triggerLength, type=type)

            for j in def_joints:
                try:
                    cmds.parent(j, parent)
                except:
                    print(f"The parent for {j} named {parent} wasn't found. Rig was not parented")

def delete_all_rigs():
    all_transforms = cmds.ls(type='transform')
    for t in all_transforms:
        if cmds.objExists(t) and check_for_attr(t, 'muscleRig'):
            cmds.delete(t)
    all_joints = cmds.ls(type='joint')
    for joint in all_joints:
        if check_for_attr(joint, 'isMuscleJoint', 'joint'):
            cmds.delete(joint)
    return ()

def export_guides(file_path):
    to_export = []
    all_joints = cmds.ls(type='joint')
    for joint in all_joints:
        if check_for_attr(joint, 'parent', 'joint') and check_for_attr(joint, 'numJoints', 'joint'):
            to_export.append(joint)

    current_selection = cmds.ls(sl=True)
    cmds.select(to_export)
    cmds.file(file_path, es=True, type='mayaAscii')
    cmds.select(current_selection)

def bake_to_guides():
    all_joints = cmds.ls(type='joint')
    for joint in all_joints:
        if check_for_attr(joint, 'parent'):
            surface = f'{joint}_surface'

            if cmds.objExists(surface):
                bulge = cmds.getAttr(f'{surface}.bulge')
                sink = cmds.getAttr(f'{surface}.sink')
                triggerLength = cmds.getAttr(f'{surface}.triggerLength')

                cmds.setAttr(f'{joint}.bulge', bulge)
                cmds.setAttr(f'{joint}.sink', sink)
                cmds.setAttr(f'{joint}.triggerLength', triggerLength)
            else:
                pass

def import_guides(file_path):
    cmds.file(file_path, i=True)

def update_guides():
    all_joints = cmds.ls(type='joint')
    for joint in all_joints:
        if check_for_attr(joint, 'parent'):
            cmds.addAttr(joint, ln='surfType', at='enum', en='Linear:Cubic', h=False, k=True)

#############################################
## push joints
'''
ToDo:
add mirror rig function
add mirror settings function
add export and import functions
'''
def create_push_joints(driver_joint, name):

    if cmds.objExists(f'{name}_pushBase'):
        cmds.warning(f'{name}_pushBase already exists skipping')
        return
    else:
        hinge_axis = get_joint_hinge_axis(driver_joint)
        push_axis = get_push_axis(driver_joint, hinge_axis)

        # base_joint = cmds.createNode('joint', n=f'{name}_pushBase')
        base_joint = cmds.duplicate(driver_joint, po=True)[0]
        pos_up_joint = cmds.createNode('joint', n=f'{name}_pushPosUp')
        pos_dn_joint = cmds.createNode('joint', n=f'{name}_pushPosDn')
        neg_up_joint = cmds.createNode('joint', n=f'{name}_pushNegUp')
        neg_dn_joint = cmds.createNode('joint', n=f'{name}_pushNegDn')

        # set joint appearance
        for j in [pos_up_joint, pos_dn_joint, neg_up_joint, neg_dn_joint]:
            cmds.setAttr(f'{j}.displayLocalAxis', True)
            cmds.setAttr(f'{j}.overrideEnabled', 1)
            cmds.setAttr(f'{j}.overrideColor', 9)

        cmds.parent(pos_up_joint, base_joint)
        cmds.parent(pos_dn_joint, base_joint)
        cmds.parent(neg_up_joint, base_joint)
        cmds.parent(neg_dn_joint, base_joint)

        cmds.matchTransform(base_joint, driver_joint)
        driver_parent = cmds.listRelatives(driver_joint, p=True, type='joint')[0]
        driver_child = cmds.listRelatives(driver_joint, c=True, type='joint')[0]
        # cmds.parent(base_joint, driver_parent)
        cmds.parent(base_joint, driver_joint)

        # create group to hold constraint nodes
        if not cmds.objExists('push_constraints_grp'):
            cmds.createNode('transform', n='push_constraints_grp')

        # get usable default values
        aim_axis = get_aim_axis(driver_joint)
        length = cmds.getAttr(f'{driver_joint}.translate{aim_axis}')
        start = length * 0.2
        end = length * 0.4
        side_offset = length * 0.0125

        # add attrs to the base joint
        cmds.addAttr(base_joint, ln='drvStart', at='float', h=False, k=True)
        cmds.addAttr(base_joint, ln='drvEnd', at='float', dv=135, h=False, k=True)
        cmds.addAttr(base_joint, ln='posStart', at='float', dv=start, h=False, k=True)
        cmds.addAttr(base_joint, ln='posEnd', at='float', dv=end, h=False, k=True)
        cmds.addAttr(base_joint, ln='negStart', at='float', dv=start*-1, h=False, k=True)
        cmds.addAttr(base_joint, ln='negEnd', at='float', dv=end*-1, h=False, k=True)
        cmds.addAttr(base_joint, ln='joint', dt='string')
        cmds.setAttr(f'{base_joint}.joint', driver_joint, type='string')

        # create remap nodes for pos and neg
        pos_remap = cmds.createNode('remapValue', n=f'{name}_pos_remap')
        neg_remap = cmds.createNode('remapValue', n=f'{name}_neg_remap')

        # create transforms to read the world space pos of each joint
        parent_reader = cmds.createNode('transform', n=f'{name}_parent_reader')
        driver_reader = cmds.createNode('transform', n=f'{name}_driver_reader')
        child_reader = cmds.createNode('transform', n=f'{name}_child_reader')

        cmds.pointConstraint(driver_parent, parent_reader, mo=False)
        cmds.pointConstraint(driver_joint, driver_reader, mo=False)
        cmds.pointConstraint(driver_child, child_reader, mo=False)

        # get the vectors to find the angle between them
        child_minus_driver = cmds.createNode('plusMinusAverage', n=f'{name}_child_minus_driver')
        cmds.setAttr(f'{child_minus_driver}.operation', 2)
        parent_minus_driver = cmds.createNode('plusMinusAverage', n=f'{name}_parent_minus_driver')
        cmds.setAttr(f'{parent_minus_driver}.operation', 2)

        cmds.connectAttr(f'{child_reader}.translate', f'{child_minus_driver}.input3D[0]')
        cmds.connectAttr(f'{driver_reader}.translate', f'{child_minus_driver}.input3D[1]')

        cmds.connectAttr(f'{parent_reader}.translate', f'{parent_minus_driver}.input3D[0]')
        cmds.connectAttr(f'{driver_reader}.translate', f'{parent_minus_driver}.input3D[1]')

        angle_between = cmds.createNode('angleBetween', n=f'{name}_angle')

        cmds.connectAttr(f'{child_minus_driver}.output3D', f'{angle_between}.vector1')
        cmds.connectAttr(f'{parent_minus_driver}.output3D', f'{angle_between}.vector2')

        # div that angle by 2 to find the half way angle
        multiply = cmds.createNode('multDoubleLinear', n=f'{name}_multiply')
        cmds.setAttr(f'{multiply}.input2', 0.5)
        cmds.connectAttr(f'{angle_between}.angle', f'{multiply}.input1')

        # drive base joint hinge axis
        cmds.connectAttr(f'{multiply}.output', f'{base_joint}.rotate{hinge_axis}')

        cmds.connectAttr(f'{angle_between}.angle', f'{pos_remap}.inputValue')
        cmds.connectAttr(f'{angle_between}.angle', f'{neg_remap}.inputValue')

        start_angle = cmds.getAttr(f'{angle_between}.angle')
        cmds.setAttr(f'{base_joint}.drvStart', start_angle)
        cmds.setAttr(f'{base_joint}.drvEnd', 0.00)

        # drive push translate on push joints
        # connect attrs from base joint to remap nodes
        # we need to do the opposite for the right side
        if '_r' or '_R' in name:

            cmds.connectAttr(f'{pos_remap}.outValue', f'{pos_up_joint}.translate{aim_axis}')
            cmds.connectAttr(f'{pos_remap}.outValue', f'{pos_dn_joint}.translate{aim_axis}')
            cmds.connectAttr(f'{neg_remap}.outValue', f'{neg_up_joint}.translate{aim_axis}')
            cmds.connectAttr(f'{neg_remap}.outValue', f'{neg_dn_joint}.translate{aim_axis}')

            cmds.connectAttr(f'{base_joint}.drvStart', f'{pos_remap}.inputMin')
            cmds.connectAttr(f'{base_joint}.drvEnd', f'{pos_remap}.inputMax')
            cmds.connectAttr(f'{base_joint}.posStart', f'{pos_remap}.outputMin')
            cmds.connectAttr(f'{base_joint}.posEnd', f'{pos_remap}.outputMax')

            cmds.connectAttr(f'{base_joint}.drvStart', f'{neg_remap}.inputMin')
            cmds.connectAttr(f'{base_joint}.drvEnd', f'{neg_remap}.inputMax')
            cmds.connectAttr(f'{base_joint}.negStart', f'{neg_remap}.outputMin')
            cmds.connectAttr(f'{base_joint}.negEnd', f'{neg_remap}.outputMax')
        else:

            cmds.connectAttr(f'{pos_remap}.outValue', f'{pos_up_joint}.translate{aim_axis}')
            cmds.connectAttr(f'{pos_remap}.outValue', f'{pos_dn_joint}.translate{aim_axis}')
            cmds.connectAttr(f'{neg_remap}.outValue', f'{neg_up_joint}.translate{aim_axis}')
            cmds.connectAttr(f'{neg_remap}.outValue', f'{neg_dn_joint}.translate{aim_axis}')

            cmds.connectAttr(f'{base_joint}.drvStart', f'{pos_remap}.inputMin')
            cmds.connectAttr(f'{base_joint}.drvEnd', f'{pos_remap}.inputMax')
            cmds.connectAttr(f'{base_joint}.posStart', f'{pos_remap}.outputMin')
            cmds.connectAttr(f'{base_joint}.posEnd', f'{pos_remap}.outputMax')

            cmds.connectAttr(f'{base_joint}.drvStart', f'{neg_remap}.inputMin')
            cmds.connectAttr(f'{base_joint}.drvEnd', f'{neg_remap}.inputMax')
            cmds.connectAttr(f'{base_joint}.negStart', f'{neg_remap}.outputMin')
            cmds.connectAttr(f'{base_joint}.negEnd', f'{neg_remap}.outputMax')

        # offset the up and dn joints a little so they don't overlap
        cmds.setAttr(f'{pos_up_joint}.translate{push_axis}', side_offset * -1)
        cmds.setAttr(f'{pos_dn_joint}.translate{push_axis}', side_offset)
        cmds.setAttr(f'{neg_up_joint}.translate{push_axis}', side_offset * -1)
        cmds.setAttr(f'{neg_dn_joint}.translate{push_axis}', side_offset)

        # orient constrain up and dn joints to the parent and driver joints
        # skip all axes except the hinge axis
        skip = []
        for a in ['X', 'Y', 'Z']:
            if a != hinge_axis:
                skip.append(a.lower())
        pos_up_orient = cmds.orientConstraint(driver_parent, pos_up_joint, mo=False, skip=skip)[0]
        neg_up_orient = cmds.orientConstraint(driver_parent, neg_up_joint, mo=False, skip=skip)[0]
        pos_dn_orient = cmds.orientConstraint(driver_joint, pos_dn_joint, mo=False, skip=skip)[0]
        neg_dn_orient = cmds.orientConstraint(driver_joint, neg_dn_joint, mo=False, skip=skip)[0]
        cmds.parent(pos_up_orient, pos_dn_orient, neg_up_orient, neg_dn_orient, 'push_constraints_grp')

def get_aim_axis(driver_joint):
    # Get the children of the driver_joint
    children = cmds.listRelatives(driver_joint, type='joint', children=True)
    if not children:
        cmds.warning(f"No child joint found for {driver_joint}.")
        return None

    child_joint = children[0]

    # Get the translate values of the child joint relative to the driver_joint
    translate_values = cmds.getAttr(f"{child_joint}.translate")[0]

    # Find the axis with the largest absolute translation value
    axes = ['x', 'y', 'z']
    axis_index = max(range(3), key=lambda i: abs(translate_values[i]))
    sign = '-' if translate_values[axis_index] < 0 else ''

    return f"{axes[axis_index].capitalize()}"

def get_push_axis(driver_joint, hinge_axis='Z'):
    aim_axis = get_aim_axis(driver_joint)
    push_axis = None
    for axis in ['X', 'Y', 'Z']:
        if axis != aim_axis and axis != hinge_axis:
            push_axis = axis

    return push_axis

def get_joint_hinge_axis(joint):
    parent = cmds.listRelatives(joint, p=True, type='joint')[0]
    reader = cmds.createNode('transform')
    cmds.matchTransform(reader, joint)
    cmds.parent(reader, parent)

    if not cmds.objectType(joint, isType="joint"):
        cmds.error(f"The specified object '{joint}' is not a joint.")
        return None

    # Get the joint's rotate axis
    rotate = cmds.getAttr(f"{reader}.rotate")[0]

    # Check if all rotation values are zero (default state)
    if all(value == 0.0 for value in rotate):
        cmds.warning(f"The joint '{joint}' has no specific rotateAxis set. It might hinge along the default axis.")

    # Calculate the dominant axis
    abs_values = [abs(value) for value in rotate]
    max_index = abs_values.index(max(abs_values))
    axes = ['x', 'y', 'z']

    cmds.delete(reader)

    return axes[max_index].capitalize()

def mirror_push_rigs():
    # either mirror selected base joints or mirror all push rigs
    to_mirror = []
    selection = cmds.ls(sl=True)
    if selection:
        for item in selection:
            if check_for_attr(item, 'drvStart', 'joint'):
                to_mirror.append(item)
    else:
        all_joints = cmds.ls(type='joint')
        for joint in all_joints:
            if '_L' or '_l' in joint:
                if check_for_attr(joint, 'drvStart', 'joint'):
                    to_mirror.append(joint)

    for base_joint in to_mirror:
        driver_joint_L = cmds.getAttr(f'{base_joint}.joint')
        driver_joint_R = ''
        name_L = base_joint.split('_pushBase')[0]
        name_R = ''
        if '_L' in base_joint:
            driver_joint_R = driver_joint_L.replace('L', 'R')
        elif '_l' in base_joint:
            driver_joint_R = driver_joint_L.replace('l', 'r')

        if '_L' in name_L:
            name_R = name_L.replace('_L','_R')
        if '_l' in name_L:
            name_R = name_L.replace('_l', '_r')

        create_push_joints(driver_joint_R, name_R)
        mirror_push_rig_settings(base_joint)

def mirror_all_push_rig_settings():
    # either mirror selected base joints or mirror all push rigs
    to_mirror = []
    selection = cmds.ls(sl=True)
    if selection:
        for item in selection:
            if check_for_attr(item, 'drvStart', 'joint'):
                to_mirror.append(item)
    else:
        all_joints = cmds.ls(type='joint')
        for joint in all_joints:
            if '_L' or '_l' in joint:
                if check_for_attr(joint, 'drvStart', 'joint'):
                    to_mirror.append(joint)

    for push_base in to_mirror:
        mirror_push_rig_settings(push_base)

def mirror_push_rig_settings(push_base_L):
    push_base_R = ''
    joint_L = cmds.getAttr(f'{push_base_L}.joint')
    joint_R = ''
    if '_L' in push_base_L:
        push_base_R = push_base_L.replace('_L', '_R')
    elif '_l' in push_base_L:
        push_base_R = push_base_L.replace('_l', '_r')
    if '_L' in joint_L:
        joint_R = joint_L.replace('_L', '_R')
    if '_l' in joint_L:
        joint_R = joint_L.replace('_l', '_r')

    if cmds.objExists(push_base_R):
        drvStart = cmds.getAttr(f'{push_base_L}.drvStart')
        drvEnd = cmds.getAttr(f'{push_base_L}.drvEnd')
        posStart = cmds.getAttr(f'{push_base_L}.posStart')
        posEnd = cmds.getAttr(f'{push_base_L}.posEnd')
        negStart = cmds.getAttr(f'{push_base_L}.negStart')
        negEnd = cmds.getAttr(f'{push_base_L}.negEnd')

        cmds.setAttr(f'{push_base_R}.drvStart', drvStart)
        cmds.setAttr(f'{push_base_R}.drvEnd', drvEnd)
        cmds.setAttr(f'{push_base_R}.posStart', posStart*-1)
        cmds.setAttr(f'{push_base_R}.posEnd', posEnd*-1)
        cmds.setAttr(f'{push_base_R}.negStart', negStart*-1)
        cmds.setAttr(f'{push_base_R}.negEnd', negEnd*-1)
        cmds.setAttr(f'{push_base_R}.joint', joint_R, type='string')

def export_push_rigs(file_path):
    data = {}
    all_joints = cmds.ls(type='joint')
    for joint in all_joints:
        if check_for_attr(joint, 'drvStart', 'joint') and check_for_attr(joint, 'drvEnd', 'joint'):
            rig_name = joint.split('_pushBase')[0]
            driver_joint = cmds.getAttr(f'{joint}.joint')
            drvStart = cmds.getAttr(f'{joint}.drvStart')
            drvEnd = cmds.getAttr(f'{joint}.drvEnd')
            posStart = cmds.getAttr(f'{joint}.posStart')
            posEnd = cmds.getAttr(f'{joint}.posEnd')
            negStart = cmds.getAttr(f'{joint}.negStart')
            negEnd = cmds.getAttr(f'{joint}.negEnd')
            data[driver_joint] = {
                'rig_name':rig_name,
                'drvStart':drvStart,
                'drvEnd':drvEnd,
                'posStart':posStart,
                'posEnd':posEnd,
                'negStart':negStart,
                'negEnd':negEnd
            }

    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=4)

def import_push_rigs(file_path):
    with open(file_path, "r") as json_file:
        loaded_data = json.load(json_file)

    for key in loaded_data.keys():
        create_push_joints(key, loaded_data[key]['rig_name'])

    base_name = f"{loaded_data[key]['rig_name']}_pushBase"
    if cmds.objExists(base_name):
        cmds.setAttr(f'{base_name}.drvStart', loaded_data[key]['drvStart'])
        cmds.setAttr(f'{base_name}.drvEnd', loaded_data[key]['drvEnd'])
        cmds.setAttr(f'{base_name}.posStart', loaded_data[key]['posStart'])
        cmds.setAttr(f'{base_name}.posEnd', loaded_data[key]['posEnd'])
        cmds.setAttr(f'{base_name}.negStart', loaded_data[key]['negStart'])
        cmds.setAttr(f'{base_name}.negEnd', loaded_data[key]['negEnd'])














