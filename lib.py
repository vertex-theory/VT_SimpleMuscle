import maya.cmds as cmds

'''

'''

def setup(joints, num_joints=1, parent=None):
    rig=create_rig_hierarchy(joints[0])
    curves=create_curves(joints)
    surface = create_surface(curves, joints[0], rig)
    if '_R' in joints[0]:
        right_side = True
    else:
        right_side = False
    def_joints = joints_on_surface(surface, joints[0], rig, num_joints, parent, right_side)
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

def create_surface(curves, name_base, rig):
    surface = cmds.loft(curves[0], curves[1], d=1, ch=False, ss=1, n=f'{name_base}_surface')[0]
    cmds.rebuildSurface(surface, ch=False, rpo=True, rt=0, end=1, kr=0, kcp=False, kc=False, su=1, du=1, sv=1, dv=1,
                        tol=0.01, fr=0, dir=2)
    cmds.reverseSurface(surface, ch=False, rpo=True, d=3)

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

def joints_on_surface(surface, base_name, rig, num_joints=1, parent=None, right_side=False):
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


    create_flex(surface, skin_joints, base_name, rig, follicle_shapes)
    return(skin_joints)

def create_flex(surface, joints, base_name, rig, follicleShapes):
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
    cmds.addAttr(surface, ln='bulge', at='float', h=False, k=True, min=0.0)
    cmds.addAttr(surface, ln='sink', at='float', h=False, k=True, min=0.0)
    # calculate default values as a percentage of muscle length
    default = (cmds.getAttr(f'{surface}.length')*0.18)
    cmds.setAttr(f'{surface}.bulge', default)
    cmds.setAttr(f'{surface}.sink', (default*0.5))

    # add trigger attr for when the shape fires
    cmds.addAttr(surface, ln='triggerLength', at='float', h=False, k=True, min=0.0, max=1.0, dv=0.6)

    #drive offset on joints
    calculate_offset_factor(joints, follicleShapes, surface)

    # use a remap value node and some math nodes to drive the muscle flex and stretch
    for i in range(len(joints)):
        # remap = cmds.createNode('remapValue', n=f'{joints[i]}_remap')
        # bulgePlusSink = cmds.createNode('addDoubleLinear', n=f'{joints[i]}_bulgePlusSink')
        # onePlusTrigger = cmds.createNode('addDoubleLinear', n=f'{joints[i]}_onePlusTrigger')
        # timesMultiplier = cmds.createNode('multDoubleLinear', n=f'{joints[i]}_timesMultiplier')
        # cmds.connectAttr(f'{surface}.bulge', f'{bulgePlusSink}.input1')
        # cmds.connectAttr(f'{surface}.sink', f'{bulgePlusSink}.input2')
        # cmds.connectAttr(f'{surface}.triggerLength', f'{onePlusTrigger}.input1')
        # cmds.setAttr(f'{onePlusTrigger}.input2', 1.0)
        # cmds.connectAttr(f'{onePlusTrigger}.output', f'{remap}.inputMax')
        # cmds.connectAttr(f'{bulgePlusSink}.output', f'{timesMultiplier}.input1')
        # cmds.connectAttr(f'{surface}.{joints[i]}', f'{timesMultiplier}.input2')
        # cmds.connectAttr(f'{timesMultiplier}.output', f'{remap}.outputMin')
        # cmds.connectAttr(f'{surface}.triggerLength', f'{remap}.inputMin')
        # cmds.connectAttr(f'{surface}.factor', f'{remap}.inputValue')
        # cmds.setAttr(f'{remap}.outputMax', 0.0)
        # constraint = f'{joints[i]}_parentConstraint1'
        # cmds.connectAttr(f'{remap}.outValue', f'{constraint}.target[0].targetOffsetTranslateZ')

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

def create_muscle(muscle_name, parent, number_jnts):
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
            if '_L' in joint and check_for_attr(joint, 'parent', 'joint'):
                to_mirror.append(joint)

    for guide in to_mirror:
        right_guide = cmds.mirrorJoint(guide, sr =['_L','_R'], myz=True, mb=True)[0]
        # mirror parent attr
        parent_left = cmds.getAttr(f'{guide}.parent')
        parent_right = parent_left.replace('_L','_R')
        if cmds.objExists(parent_right):
            cmds.setAttr(f'{right_guide}.parent', parent_right, type='string')
        else:
            print(f"the right side parent for {right_guide} doesnt exist. Setting to nothing")
            cmds.setAttr(f'{right_guide}.parent', '', type='string')

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
    all_joints = cmds.ls(type='joint')
    for joint in all_joints:
        if check_for_attr(joint, 'parent'):
            parent = cmds.getAttr(f'{joint}.parent')
            num_joints = cmds.getAttr(f'{joint}.numJoints')
            end_joint = cmds.listRelatives(joint, c=True)[0]
            def_joints = setup([joint,end_joint], num_joints, parent)

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

def import_guides(file_path):
    cmds.file(file_path, i=True)









