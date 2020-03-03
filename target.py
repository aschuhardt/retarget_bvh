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
from bpy_extras.io_utils import ExportHelper
import math
import os

from .utils import *
from .armature import CArmature


class CTargetInfo:
    def __init__(self, name):
        self.name = name
        self.filepath = "None"
        self.bones = []
        self.parents = {}
        self.optional = []
        self.fingerprint = []
        

    def readFile(self, filepath):
        import json
        if theVerbose:
            print("Read target file", filepath)
        self.filepath = filepath
        with open(filepath, "r") as fp:
            struct = json.load(fp)
        self.name = struct["name"]
        self.bones = [(key, nameOrNone(value)) for key,value in struct["bones"].items()]
        if "parents" in struct.keys():
            self.parents = struct["parents"]
        if "optional" in struct.keys():
            self.optional = struct["optional"]
        if "fingerprint" in struct.keys():
            self.fingerprint = struct["fingerprint"]
        

    def addAutoBones(self, rig):
        self.bones = []
        for pb in rig.pose.bones:
            if pb.McpBone:
                self.bones.append( (pb.name, pb.McpBone) )
        self.addParents(rig)
        

    def addManualBones(self, rig):
        for pb in rig.pose.bones:
            pb.McpBone = ""
        for bname,mhx in self.bones:
            if bname in rig.pose.bones.keys():
                rig.pose.bones[bname].McpBone = mhx
            else:
                print("  ", bname)
        self.addParents(rig)
        
        
    def addParents(self, rig):        
        for pb in rig.pose.bones:
            if pb.McpBone:
                pb.McpParent = ""
                par = pb.parent
                while par:
                    if par.McpBone:
                        pb.McpParent = par.name
                        break
                    par = par.parent
        for bname,pname in self.parents.items():
            pb = rig.pose.bones[bname]
            pb.McpParent = pname
    
        if theVerbose:
            print("Parents")
            for pb in rig.pose.bones:
                if pb.McpBone:
                    print("  ", pb.name, pb.McpParent)
          

    def testRig(self, name, rig, includeFingers):
        from .armature import validBone
        print("Testing %s" % name)
        for (bname, mhxname) in self.bones:
            if bname in self.optional:
                continue
            if bname[0:2] == "f_" and not includeFingers:
                continue
            try:
                pb = rig.pose.bones[bname]
            except KeyError:
                pb = None
            if pb is None or not validBone(pb):
                print("  Did not find bone %s (%s)" % (bname, mhxname))
                print("Bones:")
                for pair in self.bones:
                    print("  %s : %s" % pair)
                raise MocapError("Target armature %s does not\nmatch armature %s." % (rig.name, name))

#
#   Global variables
#

_targetInfo = {}

def getTargetInfo(rigname):
    global _targetInfo
    return _targetInfo[rigname]

def loadTargets():
    global _targetInfo
    _targetInfo = {}

def isTargetInited(scn):
    return ( _targetInfo != {} )

def ensureTargetInited(scn):
    if not isTargetInited(scn):
        initTargets(scn)

#
#   findTargetArmature(context, rig, auto, includeFingers):
#

def findTargetArmature(context, rig, auto, includeFingers):
    from .t_pose import putInRestPose
    global _targetInfo

    scn = context.scene
    setCategory("Identify Target Rig")
    ensureTargetInited(scn)

    if auto or scn.McpTargetRig == "Automatic":
        name = guessTargetArmatureFromList(rig, scn)
    else:
        name = scn.McpTargetRig

    if name == "Automatic":
        setCategory("Automatic Target Rig")
        amt = CArmature()
        amt.findArmature(rig, ignoreHiddenLayers=scn.McpIgnoreHiddenLayers)
        scn.McpTargetRig = "Automatic"
        amt.display("Target")

        info = _targetInfo[name] = CTargetInfo(name)
        info.addAutoBones(rig)
        rig.McpTPoseFile = ""
        clearCategory()
        return info

    else:
        setCategory("Manual Target Rig")
        scn.McpTargetRig = name
        info = _targetInfo[name]
        if not info.testRig(name, rig, includeFingers):
            pass
        print("Target armature %s" % name)
        info.addManualBones(rig)
        clearCategory()
        return info


def guessTargetArmatureFromList(rig, scn):
    ensureTargetInited(scn)
    print("Guessing target")
    for name,info in _targetInfo.items():
        if name == "Automatic":
            continue
        elif matchAllBones(rig, info):
            return name
    else:
        return "Automatic"


def matchAllBones(rig, info):
    if not hasAllBones(info.fingerprint, rig):
        return False
    for bname,mhx in info.bones:
        if bname in info.optional or mhx[0:2] == "f_":
            continue
        elif bname not in rig.data.bones.keys():
            if theVerbose:
                print("Missing bone:", bname)
            return False
    return True

###############################################################################
#
#    Target initialization
#
###############################################################################

def initTargets(scn):
    global _targetInfo
    _targetInfo = { "Automatic" : CTargetInfo("Automatic") }
    path = os.path.join(os.path.dirname(__file__), "target_rigs")
    for fname in os.listdir(path):
        filepath = os.path.join(path, fname)
        (name, ext) = os.path.splitext(fname)
        if ext == ".json" and os.path.isfile(filepath):
            info = CTargetInfo("Manual")
            info.readFile(filepath)
            _targetInfo[info.name] = info

    enums =[]
    keys = list(_targetInfo.keys())
    keys.sort()
    for key in keys:
        enums.append((key,key,key))

    bpy.types.Scene.McpTargetRig = EnumProperty(
        items = enums,
        name = "Target rig",
        default = 'Automatic')
    print("Defined McpTargetRig")


class MCP_OT_InitTargets(BvhOperator):
    bl_idname = "mcp.init_targets"
    bl_label = "Init Target Panel"
    bl_description = "(Re)load all .trg files in the target_rigs directory."
    bl_options = {'UNDO'}

    def run(self, context):
        from .t_pose import initTPoses, initTargetTPose
        initTPoses()
        initTargetTPose(context.scene)
        initTargets(context.scene)


class IncludeFingers:
    includeFingers : BoolProperty(
        name = "Include Fingers",
        description = "Include finger bones",
        default = False)    

    def draw(self, context):
        self.layout.prop(self, "includeFingers")


class MCP_OT_GetTargetRig(BvhOperator, IsArmature, IncludeFingers):
    bl_idname = "mcp.get_target_rig"
    bl_label = "Identify Target Rig"
    bl_description = "Identify the target rig type of the active armature."
    bl_options = {'UNDO'}

    def prequel(self, context):
        from .retarget import changeTargetData
        return changeTargetData(context.object, context.scene)
    
    def run(self, context):
        setVerbose(True)
        context.scene.McpTargetRig = "Automatic"        
        findTargetArmature(context, context.object, True, self.includeFingers)
        
    def sequel(self, context, data):
        from .retarget import restoreTargetData
        restoreTargetData(data)


#----------------------------------------------------------
#   List Rig
#----------------------------------------------------------

from .source import ListRig

class MCP_OT_ListTargetRig(BvhPropsOperator, ListRig):
    bl_idname = "mcp.list_target_rig"
    bl_label = "List Target Rig"
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return context.scene.McpTargetRig

    def findKeys(self, mhx, bones):
        keys = []
        for (bone, mhx1) in bones:
            if mhx1 == mhx:
                keys.append(bone)
        return keys

    def getBones(self, context):
        info = getTargetInfo(context.scene.McpTargetRig)    
        if info:
            return info.bones
        else:
            return []


class MCP_OT_VerifyTargetRig(BvhPropsOperator, IncludeFingers):
    bl_idname = "mcp.verify_target_rig"
    bl_label = "Verify Target Rig"
    bl_options = {'UNDO'}
        
    @classmethod
    def poll(self, context):
        ob = context.object
        return (context.scene.McpTargetRig and ob and ob.type == 'ARMATURE')
                
    def run(self, context):   
        rigtype = context.scene.McpTargetRig     
        info = _targetInfo[rigtype]
        rig = context.object
        info.testRig(rigtype, rig, self.includeFingers)
        print("Target armature %s verified" % rigtype)
        
#----------------------------------------------------------
#   Target armature
#----------------------------------------------------------

class Target:
    useAutoTarget : BoolProperty(
        name = "Auto Target",
        description = "Find target rig automatically",
        default = True)

    includeFingers : BoolProperty(
        name = "Include Fingers",
        description = "Include finger bones",
        default = False)

    def draw(self, context):
        self.layout.prop(self, "useAutoTarget")
        if not self.useAutoTarget:
            self.layout.prop(context.scene, "McpTargetRig")
        self.layout.separator()
        self.layout.prop(self, "includeFingers")
        self.layout.separator()        

    def findTarget(self, context, rig):
        return findTargetArmature(context, rig, self.useAutoTarget, self.includeFingers)

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MCP_OT_InitTargets,
    MCP_OT_GetTargetRig,
    MCP_OT_ListTargetRig,
    MCP_OT_VerifyTargetRig,
]

def initialize():
    bpy.types.Scene.McpTargetRig = EnumProperty(
        items = [("Automatic", "Automatic", "Automatic")],
        name = "Target Rig",
        default = "Automatic")    
        
    bpy.types.Scene.McpTargetTPose = EnumProperty(
        items = [("Default", "Default", "Default")],
        name = "Target T-pose",
        default = "Default")              

    bpy.types.Object.McpReverseHip = BoolProperty(
        name = "Reverse Hip",
        description = "The rig has a reverse hip",
        default = False)

    bpy.types.Scene.McpIgnoreHiddenLayers = BoolProperty(
        name = "Ignore Hidden Layers",
        description = "Ignore bones on hidden layers when identifying target rig",
        default = True)

    bpy.types.PoseBone.McpBone = StringProperty(
        name = "MakeHuman Bone",
        description = "MakeHuman bone corresponding to this bone",
        default = "")

    bpy.types.PoseBone.McpParent = StringProperty(
        name = "Parent",
        description = "Parent of this bone for retargeting purposes",
        default = "")


    for cls in classes:
        bpy.utils.register_class(cls)


def uninitialize():
    for cls in classes:
        bpy.utils.unregister_class(cls)
