# ------------------------------------------------------------------------------
#   BSD 2-Clause License
#   
#   Copyright (c) 2019-2020, Thomas Larsson
#   All rights reserved.
#   
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#   
#   1. Redistributions of source code must retain the above copyright notice, this
#      list of conditions and the following disclaimer.
#   
#   2. Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#   
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#   DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#   FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#   DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#   SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#   CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#   OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#   OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------

import bpy
from bpy.props import *
from bpy_extras.io_utils import ImportHelper, ExportHelper

import os
from math import sqrt, pi
from mathutils import Quaternion, Matrix
from .utils import *
from .io_json import *

#------------------------------------------------------------------
#   
#------------------------------------------------------------------

_t_poses = {}

def isTPoseInited():
    global _t_poses
    return (_t_poses != {})

def ensureTPoseInited(scn):
    if not isTPoseInited():
        initTPoses()
        initSourceTPose(scn)
        initTargetTPose(scn)

#------------------------------------------------------------------
#   Classes
#------------------------------------------------------------------

class JsonFile:
    filename_ext = ".json"
    filter_glob : StringProperty(default="*.json", options={'HIDDEN'})
    filepath : StringProperty(name="File Path", description="Filepath to json file", maxlen=1024, default="")


class Rigger:
    autoRig : BoolProperty(
        name = "Auto Rig",
        description = "Find rig automatically",
        default = True)

    def draw(self, context):
        self.layout.prop(self, "autoRig")
        
            
    def initRig(self, context):
        from .target import findTargetArmature
        from .source import findSourceArmature
        from .fkik import setRigifyFKIK, setRigify2FKIK
    
        rig = context.object
        pose = [(pb, pb.matrix_basis.copy()) for pb in rig.pose.bones]
    
        if rig.McpIsSourceRig:
            findSourceArmature(context, rig, self.autoRig)
        else:
            findTargetArmature(context, rig, self.autoRig)

        for pb,mat in pose:
            pb.matrix_basis = mat

        if isRigify(rig):
            setRigifyFKIK(rig, 0.0)
        elif isRigify2(rig):
            setRigify2FKIK(rig, 1.0)

        return rig

#------------------------------------------------------------------
#   Define current pose as rest pose
#------------------------------------------------------------------

def applyRestPose(context, value):
    rig = context.object
    children = []
    for ob in context.view_layer.objects:
        if ob.type != 'MESH':
            continue

        setActiveObject(context, ob)
        if ob != context.object:
            raise StandardError("Context switch did not take:\nob = %s\nc.ob = %s\nc.aob = %s" %
                (ob, context.object, context.active_object))

        if (ob.McpArmatureName == rig.name and
            ob.McpArmatureModifier != ""):
            mod = ob.modifiers[ob.McpArmatureModifier]
            ob.modifiers.remove(mod)
            ob.data.shape_keys.key_blocks[ob.McpArmatureModifier].value = value
            children.append(ob)
        else:
            for mod in ob.modifiers:
                if (mod.type == 'ARMATURE' and
                    mod.object == rig):
                    children.append(ob)
                    bpy.ops.object.modifier_apply(apply_as='SHAPE', modifier=mod.name)
                    ob.data.shape_keys.key_blocks[mod.name].value = value
                    ob.McpArmatureName = rig.name
                    ob.McpArmatureModifier = mod.name
                    break

    setActiveObject(context, rig)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply()
    for ob in children:
        name = ob.McpArmatureModifier
        setActiveObject(context, ob)
        mod = ob.modifiers.new(name, 'ARMATURE')
        mod.object = rig
        mod.use_vertex_groups = True
        bpy.ops.object.modifier_move_up(modifier=name)
        #setShapeKey(ob, name, value)

    setActiveObject(context, rig)
    print("Applied pose as rest pose")


def setShapeKey(ob, name, value):
    if not ob.data.shape_keys:
        return
    skey = ob.data.shape_keys.key_blocks[name]
    skey.value = value


class MCP_OT_RestCurrentPose(BvhPropsOperator, IsArmature, Rigger):
    bl_idname = "mcp.rest_current_pose"
    bl_label = "Current Pose => Rest Pose"
    bl_description = "Change rest pose to current pose"
    bl_options = {'UNDO'}

    def run(self, context):
        self.initRig(context)
        applyRestPose(context, 1.0)
        print("Set current pose to rest pose")

#------------------------------------------------------------------
#   Automatic T-Pose
#------------------------------------------------------------------

TPose = {
    "shoulder.L" : (0, 0, -90*D, 'XYZ'),
    "upper_arm.L" : (0, 0, -90*D, 'XYZ'),
    "forearm.L" :   (0, 0, -90*D, 'XYZ'),
    "hand.L" :      (0, 0, -90*D, 'XYZ'),

    "shoulder.R" : (0, 0, 90*D, 'XYZ'),
    "upper_arm.R" : (0, 0, 90*D, 'XYZ'),
    "forearm.R" :   (0, 0, 90*D, 'XYZ'),
    "hand.R" :      (0, 0, 90*D, 'XYZ'),

    "thigh.L" :     (-90*D, 0, 0, 'XYZ'),
    "shin.L" :      (-90*D, 0, 0, 'XYZ'),
    #"foot.L" :      (None, 0, 0, 'XYZ'),
    #"toe.L" :       (pi, 0, 0, 'XYZ'),

    "thigh.R" :     (-90*D, 0, 0, 'XYZ'),
    "shin.R" :      (-90*D, 0, 0, 'XYZ'),
    #"foot.R" :      (None, 0, 0, 'XYZ'),
    #"toe.R" :       (pi, 0, 0, 'XYZ'),
    
    "f_thumb.01.L": (0, 0, -120*D, 'XYZ'),
    "f_thumb.02.L": (0, 0, -120*D, 'XYZ'),
    "f_thumb.03.L": (0, 0, -120*D, 'XYZ'),
    "f_index.01.L": (0, 0, -105*D, 'XYZ'),
    "f_index.02.L": (0, 0, -105*D, 'XYZ'),
    "f_index.03.L": (0, 0, -105*D, 'XYZ'),
    "f_middle.01.L": (0, 0, -90*D, 'XYZ'),
    "f_middle.02.L": (0, 0, -90*D, 'XYZ'),
    "f_middle.03.L": (0, 0, -90*D, 'XYZ'),
    "f_ring.01.L": (0, 0, -75*D, 'XYZ'),
    "f_ring.02.L": (0, 0, -75*D, 'XYZ'),
    "f_ring.03.L": (0, 0, -75*D, 'XYZ'),
    "f_pinky.01.L": (0, 0, -60*D, 'XYZ'),
    "f_pinky.02.L": (0, 0, -60*D, 'XYZ'),
    "f_pinky.03.L": (0, 0, -60*D, 'XYZ'),
    
    "f_thumb.01.R": (0, 0, 120*D, 'XYZ'),
    "f_thumb.02.R": (0, 0, 120*D, 'XYZ'),
    "f_thumb.03.R": (0, 0, 120*D, 'XYZ'),
    "f_index.01.R": (0, 0, 105*D, 'XYZ'),
    "f_index.02.R": (0, 0, 105*D, 'XYZ'),
    "f_index.03.R": (0, 0, 105*D, 'XYZ'),
    "f_middle.01.R": (0, 0, 90*D, 'XYZ'),
    "f_middle.02.R": (0, 0, 90*D, 'XYZ'),
    "f_middle.03.R": (0, 0, 90*D, 'XYZ'),
    "f_ring.01.R": (0, 0, 75*D, 'XYZ'),
    "f_ring.02.R": (0, 0, 75*D, 'XYZ'),
    "f_ring.03.R": (0, 0, 75*D, 'XYZ'),
    "f_pinky.01.R": (0, 0, 60*D, 'XYZ'),
    "f_pinky.02.R": (0, 0, 60*D, 'XYZ'),
    "f_pinky.03.R": (0, 0, 60*D, 'XYZ'),
    
}

def autoTPose(rig, context):
    print("Auto T-pose", rig.name)
    putInRestPose(rig, True)
    for pb in rig.pose.bones:
        if pb.McpBone in TPose.keys():
            ex,ey,ez,order = TPose[pb.McpBone]
        else:
            continue

        euler = pb.matrix.to_euler(order)
        if ex is None:
            ex = euler.x
        if ey is None:
            ey = euler.y
        if ez is None:
            ez = euler.z
        euler = Euler((ex,ey,ez), order)
        mat = euler.to_matrix().to_4x4()
        mat.col[3] = pb.matrix.col[3]

        loc = pb.bone.matrix_local
        if pb.parent:
            mat = pb.parent.matrix.inverted() @ mat
            loc = pb.parent.bone.matrix_local.inverted() @ loc
        mat =  loc.inverted() @ mat
        euler = mat.to_euler('YZX')
        euler.y = 0
        pb.matrix_basis = euler.to_matrix().to_4x4()
        updateScene()
        setKeys(pb)

#------------------------------------------------------------------
#   Put in rest and T pose
#------------------------------------------------------------------

def putInRestPose(rig, useSetKeys):
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix()
        if useSetKeys:
            setKeys(pb)
    updateScene()            
                


def setKeys(pb):        
    if pb.rotation_mode == "QUATERNION":
        pb.keyframe_insert("rotation_quaternion", group=pb.name)
    elif pb.rotation_mode == "AXIS_ANGLE":
        pb.keyframe_insert("rotation_axis_angle", group=pb.name)
    else:
        pb.keyframe_insert("rotation_euler", group=pb.name)
    #pb.keyframe_insert('location', group=pb.name)
        

def putInTPose(rig, tpname, context):
    global _t_poses
    if rig.McpTPoseDefined:
        getStoredTPose(rig)
    elif tpname == "Default":
        autoTPose(rig, context)
    else:
        if tpname in _t_poses.keys():
            struct = _t_poses[tpname]
        else:
            filepath = ("t_poses/%s.json" % tpname.lower())
            struct = loadPose(rig, filepath)
            _t_poses[tpname] = struct
        setTPose(rig, struct)
    updateScene()
    

class MCP_OT_PutInTPose(BvhPropsOperator, IsArmature, Rigger):
    bl_idname = "mcp.put_in_t_pose"
    bl_label = "Put In T-pose"
    bl_description = "Put the character into T-pose"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = self.initRig(context)
        putInTPose(rig, context.scene.McpTargetTPose, context)
        print("Pose set to T-pose")

#------------------------------------------------------------------
#   Set T-Pose
#------------------------------------------------------------------

def getStoredTPose(rig):
    for pb in rig.pose.bones:
        pb.matrix_basis = getStoredBonePose(pb)


def getStoredBonePose(pb):
    quat = Quaternion(pb.McpQuat)
    return quat.to_matrix().to_4x4()


def defineTPose(rig):
    for pb in rig.pose.bones:
        pb.McpQuat = pb.matrix_basis.to_quaternion()
    rig.McpTPoseDefined = True


class MCP_OT_DefineTPose(BvhPropsOperator, IsArmature, Rigger):
    bl_idname = "mcp.define_t_pose"
    bl_label = "Define T-pose"
    bl_description = "Define T-pose as current pose"
    bl_options = {'UNDO'}

    problems = ""

    def run(self, context):
        if self.problems:
            return
        rig = self.initRig(context)
        defineTPose(rig)
        print("T-pose defined as current pose")

    def invoke(self, context, event):
        from .load import checkObjectProblems
        return checkObjectProblems(self, context)

    def draw(self, context):
        from .load import drawObjectProblems
        drawObjectProblems(self)

#------------------------------------------------------------------
#   Undefine stored T-pose
#------------------------------------------------------------------

def setRestPose(rig):
    unit = Matrix()
    for pb in rig.pose.bones:
        pb.matrix_basis = unit


class MCP_OT_UndefineTPose(BvhPropsOperator, IsArmature, Rigger):
    bl_idname = "mcp.undefine_t_pose"
    bl_label = "Undefine T-pose"
    bl_description = "Remove definition of T-pose"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = self.initRig(context)
        rig.McpTPoseDefined = False
        quat = Quaternion()
        for pb in rig.pose.bones:            
            pb.McpQuat = quat    
        print("Undefined T-pose")

#------------------------------------------------------------------
#   Load T-pose from file
#------------------------------------------------------------------

def loadPose(rig, filename):
    if filename:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        filepath = os.path.normpath(filepath)
        print("Loading %s" % filepath)
        struct = loadJson(filepath)
        rig.McpTPoseFile = filename
        setTPose(rig, struct)
        return struct
    else:
        return None
    

def setTPose(rig, struct):
    setRestPose(rig)
    for name,value in struct:
        bname = getBoneName(rig, name)
        if bname in rig.pose.bones.keys():
            pb = rig.pose.bones[bname]
            quat = Quaternion(value)
            pb.matrix_basis = quat.to_matrix().to_4x4()
            setKeys(pb)


def getBoneName(rig, name):
    if rig.McpIsSourceRig:
        return name
    else:
        pb = getTrgBone(name, rig)
        if pb:
            return pb.name
        else:
            return ""


class MCP_OT_LoadPose(BvhPropsOperator, IsArmature, ExportHelper, JsonFile, Rigger):
    bl_idname = "mcp.load_pose"
    bl_label = "Load Pose"
    bl_description = "Load pose from file"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = self.initRig(context)
        filename = os.path.relpath(self.filepath, os.path.dirname(__file__))
        loadPose(rig, filename)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

#------------------------------------------------------------------
#   Save current pose to file
#------------------------------------------------------------------

def savePose(context, filepath):
    rig = context.object
    struct = []
    for pb in rig.pose.bones:
        bmat = pb.matrix
        rmat = pb.bone.matrix_local
        if pb.parent:
            bmat = pb.parent.matrix.inverted() @ bmat
            rmat = pb.parent.bone.matrix_local.inverted() @ rmat
        mat = rmat.inverted() @ bmat
        q = mat.to_quaternion()
        magn = math.sqrt( (q.w-1)*(q.w-1) + q.x*q.x + q.y*q.y + q.z*q.z )
        if magn > 1e-4:
            if pb.McpBone:
                struct.append((pb.McpBone, tuple(q)))

    if os.path.splitext(filepath)[1] != ".json":
        filepath = filepath + ".json"
    filepath = os.path.join(os.path.dirname(__file__), filepath)
    print("Saving %s" % filepath)
    saveJson(struct, filepath)


class MCP_OT_SavePose(BvhOperator, IsArmature, ExportHelper, JsonFile):
    bl_idname = "mcp.save_pose"
    bl_label = "Save Pose"
    bl_description = "Save current pose as .json file"
    bl_options = {'UNDO'}

    def run(self, context):
        savePose(context, self.filepath)
        print("Saved current pose")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

#----------------------------------------------------------
#   T-pose initialization
#----------------------------------------------------------

def initTPoses():
    global _tposeEnums

    keys = []
    path = os.path.join(os.path.dirname(__file__), "t_poses")
    for fname in os.listdir(path):
        file = os.path.join(path, fname)
        (name, ext) = os.path.splitext(fname)
        if ext == ".json" and os.path.isfile(file):
            key = name.capitalize()
            keys.append((key,key,key))
    keys.sort()
    _tposeEnums = [("Default", "Default", "Default")] + keys


def initSourceTPose(scn):
    bpy.types.Scene.McpSourceTPose = EnumProperty(
        items = _tposeEnums,
        name = "Source T-Pose",
        default = 'Default')
    scn.McpSourceTPose = 'Default'


def initTargetTPose(scn):
    bpy.types.Scene.McpTargetTPose = EnumProperty(
        items = _tposeEnums,
        name = "Target T-Pose",
        default = 'Default')
    scn.McpTargetTPose = 'Default'


class MCP_OT_InitTPoses(BvhOperator):
    bl_idname = "mcp.init_t_poses"
    bl_label = "Init T-poses"
    bl_options = {'UNDO'}

    def run(self, context):
        initTPoses()
        initSourceTPose(context.scene)
        initTargetTPose(context.scene)
        print("T-poses initialized")

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MCP_OT_RestCurrentPose,
    MCP_OT_PutInTPose,
    MCP_OT_DefineTPose,
    MCP_OT_UndefineTPose,
    MCP_OT_LoadPose,
    MCP_OT_SavePose,
]

def initialize():
    bpy.types.Object.McpTPoseDefined = BoolProperty(default = False)
    bpy.types.Object.McpTPoseFile = StringProperty(default = "")
    bpy.types.Object.McpArmatureName = StringProperty(default = "")
    bpy.types.Object.McpArmatureModifier = StringProperty(default = "")
    bpy.types.PoseBone.McpQuat = FloatVectorProperty(size=4, default=(1,0,0,0))
    bpy.types.Object.McpIsSourceRig = BoolProperty(default=False)

    for cls in classes:
        bpy.utils.register_class(cls)


def uninitialize():
    for cls in classes:
        bpy.utils.unregister_class(cls)
