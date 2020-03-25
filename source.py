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
import os
from collections import OrderedDict
from math import pi
from mathutils import *
from bpy.props import *

from .armature import CArmature
from .utils import *

#----------------------------------------------------------
#   Source classes
#----------------------------------------------------------
          
class CRigInfo:
    def __init__(self, name="Automatic"):
        self.name = name
        self.filepath = "None"
        self.bones = []
        self.parents = {}
        self.optional = []
        self.fingerprint = []

    def testRig(self, name, rig, scn):
        from .armature import validBone
        print("Testing %s" % name)
        pbones = dict([(pb.name,pb) for pb in rig.pose.bones])
        for pb in rig.pose.bones:
            pbones[pb.name.lower()] = pb
        for (bname, mhxname) in self.bones:
            print("BB", bname, mhxname)
            if bname in self.optional:
                continue
            if bname[0:2] == "f_" and not scn.McpIncludeFingers:
                continue
            if bname in pbones.keys():
                pb = pbones[bname]
            else:
                pb = None
            if pb is None or not validBone(pb):
                print("  Did not find bone %s (%s)" % (bname, mhxname))
                print("Bones:")
                for pair in self.bones:
                    print("  %s : %s" % pair)
                raise MocapError(
                    "Armature %s does not\n" % rig.name +
                    "match armature %s.\n" % name +
                    "Did not find bone %s     " % bname)


class CSourceInfo(CArmature, CRigInfo):
    def __init__(self, struct=None):
        CArmature.__init__(self)
        CRigInfo.__init__(self)
        if struct:
            self.name = struct["name"]
            for key,value in struct["bones"].items():
                bname = canonicalName(key)
                mhxname = nameOrNone(value)
                self.boneNames[bname] = mhxname
                self.bones.append((key,mhxname))
            if "optional" in struct.keys():
                for bname in struct["optional"]:
                    self.optional.extend([bname, bname.lower()])
                    
#----------------------------------------------------------
#   Global variables
#----------------------------------------------------------

_sourceInfo = {}
_activeSrcInfo = None

def getSourceArmature(name):
    global _sourceInfo
    return _sourceInfo[name]

def getSourceBoneName(bname):
    global _activeSrcInfo
    lname = canonicalName(bname)
    try:
        return _activeSrcInfo.boneNames[lname]
    except KeyError:
        return None

def getSourceTPoseFile():
    global _activeSrcInfo
    return _activeSrcInfo.tposeFile

def isSourceInited(scn):
    global _sourceInfo
    return (_sourceInfo != {})

def ensureSourceInited(scn):
    if not isSourceInited(scn):
        initSources(scn)

#
#    guessSrcArmatureFromList(rig, scn):
#

def guessSrcArmatureFromList(rig, scn):
    ensureSourceInited(scn)
    bestMisses = 1000

    misses = {}
    for name in _sourceInfo.keys():
        if name == "Automatic":
            continue
        amt = _sourceInfo[name]
        nMisses = 0
        for bone in rig.data.bones:
            try:
                amt.boneNames[canonicalName(bone.name)]
            except KeyError:
                nMisses += 1
        misses[name] = nMisses
        if nMisses < bestMisses:
            best = amt
            bestMisses = nMisses

    if bestMisses == 0:
        scn.McpSourceRig = best.name
        return best
    else:
        print("Number of misses:")
        for (name, n) in misses.items():
            print("  %14s: %2d" % (name, n))
        print("Best bone map for armature %s:" % best.name)
        amt = _sourceInfo[best.name]
        for bone in rig.data.bones:
            try:
                bname = amt.boneNames[canonicalName(bone.name)]
                string = "     "
            except KeyError:
                string = " *** "
                bname = "?"
            print("%s %14s => %s" % (string, bone.name, bname))
        raise MocapError('Did not find matching armature. nMisses = %d' % bestMisses)

#
#   findSourceArmature(context, rig, auto):
#

def findSourceArmature(context, rig, auto):
    global _activeSrcInfo, _sourceInfo
    from .t_pose import autoTPose, defineTPose, putInRestPose
    scn = context.scene

    setCategory("Identify Source Rig")
    ensureSourceInited(scn)
    if auto or scn.McpSourceRig == "Automatic":
        info = _activeSrcInfo = CSourceInfo()
        putInRestPose(rig, True)
        info.findArmature(rig)
        autoTPose(rig, context)
        #defineTPose(rig)
        _sourceInfo["Automatic"] = info
        info.display("Source")
    else:
        _activeSrcInfo = _sourceInfo[scn.McpSourceRig]

    rig.McpArmature = _activeSrcInfo.name
    print("Using matching armature %s." % rig.McpArmature)
    clearCategory()

#
#    setSourceArmature(rig, scn)
#

def setSourceArmature(rig, scn):
    global _activeSrcInfo, _sourceInfo
    name = rig.McpArmature
    if name:
        scn.McpSourceRig = name
    else:
        raise MocapError("No source armature set")
    _activeSrcInfo = _sourceInfo[name]
    print("Set source armature to %s" % name)

#----------------------------------------------------------
#   Class
#----------------------------------------------------------

class Source:
    useAutoSource : BoolProperty(
        name = "Auto Source",
        description = "Find source rig automatically",
        default = True)
        
    def draw(self, context):
        self.layout.prop(self, "useAutoSource")
        if not self.useAutoSource:
            self.layout.prop(context.scene, "McpSourceRig")
        self.layout.separator()

    def findSource(self, context, rig):
        return findSourceArmature(context, rig, self.useAutoSource)

#----------------------------------------------------------
#   Source initialization
#----------------------------------------------------------

class MCP_OT_InitSources(bpy.types.Operator):
    bl_idname = "mcp.init_sources"
    bl_label = "Init Source Panel"
    bl_description = "(Re)load all json files in the source_rigs directory."
    bl_options = {'UNDO'}

    def execute(self, context):
        from .t_pose import initTPoses, initSourceTPose
        setVerbose(True)
        initSources(context.scene)
        initTPoses()
        initSourceTPose(context.scene)
        return{'FINISHED'}


def initSources(scn):
    global _sourceInfo, _srcArmatureEnums

    _sourceInfo = { "Automatic" : CSourceInfo() }
    path = os.path.join(os.path.dirname(__file__), "source_rigs")
    for fname in os.listdir(path):
        file = os.path.join(path, fname)
        (name, ext) = os.path.splitext(fname)
        if ext == ".json" and os.path.isfile(file):    
            armature = readSrcArmature(file, name)
            _sourceInfo[armature.name] = armature
    _srcArmatureEnums = [("Automatic", "Automatic", "Automatic")]
    keys = list(_sourceInfo.keys())
    keys.sort()
    for key in keys:
        _srcArmatureEnums.append((key,key,key))

    bpy.types.Scene.McpSourceRig = EnumProperty(
        items = _srcArmatureEnums,
        name = "Source rig",
        default = 'Automatic')
    scn.McpSourceRig = 'Automatic'
    print("Defined McpSourceRig")


def readSrcArmature(filepath, name):
    import json
    if theVerbose:
        print("Read source file", filepath)
    with open(filepath, "r") as fp:
        struct = json.load(fp)
    return CSourceInfo(struct)

#----------------------------------------------------------
#   List Rig
#
#   (mhx bone, text)
#----------------------------------------------------------

ListedBones = [
    ('hips',         'Root bone'),
    ('spine',        'Lower spine'),
    ('spine-1',      'Lower spine 2'),
    ('chest',        'Upper spine'),
    ('chest-1',      'Upper spine 2'),
    ('neck',         'Neck'),
    ('head',         'Head'),
    None,
    ('shoulder.L',   'L shoulder'),
    ('upper_arm.L',  'L upper arm'),
    ('forearm.L',    'L forearm'),
    ('hand.L',       'L hand'),
    None,
    ('shoulder.R',   'R shoulder'),
    ('upper_arm.R',  'R upper arm'),
    ('forearm.R',    'R forearm'),
    ('hand.R',       'R hand'),
    None,
    ('hip.L',        'L hip'),
    ('thigh.L',      'L thigh'),
    ('shin.L',       'L shin'),
    ('foot.L',       'L foot'),
    ('toe.L',        'L toes'),
    None,
    ('hip.R',        'R hip'),
    ('thigh.R',      'R thigh'),
    ('shin.R',       'R shin'),
    ('foot.R',       'R foot'),
    ('toe.R',        'R toes'),
    None,
	("f_thumb.01.L",   "L thumb 1"),
	("f_thumb.02.L",   "L thumb 2"),
	("f_thumb.03.L",   "L thumb 3"),
	("f_index.01.L",   "L index 1"),
	("f_index.02.L",   "L index 2"),
	("f_index.03.L",   "L index 3"),
	("f_middle.01.L",   "L middle 1"),
	("f_middle.02.L",   "L middle 2"),
	("f_middle.03.L",   "L middle 3"),
	("f_ring.01.L",   "L ring 1"),
	("f_ring.02.L",   "L ring 2"),
	("f_ring.03.L",   "L ring 3"),
	("f_pinky.01.L",   "L pinky 1"),
	("f_pinky.02.L",   "L pinky 2"),
	("f_pinky.03.L",   "L pinky 3"),
    None,
	("f_thumb.01.R",   "R thumb 1"),
	("f_thumb.02.R",   "R thumb 2"),
	("f_thumb.03.R",   "R thumb 3"),
	("f_index.01.R",   "R index 1"),
	("f_index.02.R",   "R index 2"),
	("f_index.03.R",   "R index 3"),
	("f_middle.01.R",   "R middle 1"),
	("f_middle.02.R",   "R middle 2"),
	("f_middle.03.R",   "R middle 3"),
	("f_ring.01.R",   "R ring 1"),
	("f_ring.02.R",   "R ring 2"),
	("f_ring.03.R",   "R ring 3"),
	("f_pinky.01.R",   "R pinky 1"),
	("f_pinky.02.R",   "R pinky 2"),
	("f_pinky.03.R",   "R pinky 3"),
]

class ListRig:
    def draw(self, context):
        bones = self.getBones(context)
        if bones:
            box = self.layout.box()
            for boneText in ListedBones:
                if not boneText:
                    box.separator()
                    continue
                (mhx, text) = boneText
                bnames = self.findKeys(mhx, bones)
                if bnames:
                    for bname in bnames:
                        row = box.row()
                        row.label(text=text)
                        row.label(text=bname)
                else:
                    row = box.row()
                    row.label(text=text)
                    row.label(text="-")


class MCP_OT_ListSourceRig(BvhPropsOperator, ListRig):
    bl_idname = "mcp.list_source_rig"
    bl_label = "List Source Rig"
    bl_description = "List the bone associations of the active source rig"
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return context.scene.McpSourceRig

    def findKeys(self, mhx, bones):
        for bone in bones.keys():
            if mhx == bones[bone]:
                return [bone]
        return []

    def getBones(self, context):  
        amt = getSourceArmature(context.scene.McpSourceRig)
        if amt:
            return amt.boneNames
        else:
            return []


class MCP_OT_VerifySourceRig(BvhOperator):
    bl_idname = "mcp.verify_source_rig"
    bl_label = "Verify Source Rig"
    bl_description = "Verify the source rig type of the active armature"
    bl_options = {'UNDO'}
        
    @classmethod
    def poll(self, context):
        ob = context.object
        return (context.scene.McpSourceRig and ob and ob.type == 'ARMATURE')
                
    def run(self, context):   
        rigtype = context.scene.McpSourceRig     
        info = _sourceInfo[rigtype]
        info.testRig(rigtype, context.object, context.scene)
        raise MocapMessage("Source armature %s verified" % rigtype)


class MCP_OT_IdentifySourceRig(BvhOperator):
    bl_idname = "mcp.identify_source_rig"
    bl_label = "Identify Source Rig"
    bl_description = "Identify the source rig type of the active armature"
    bl_options = {'UNDO'}
        
    @classmethod
    def poll(self, context):
        ob = context.object
        return (ob and ob.type == 'ARMATURE')

    def run(self, context):   
        from .target import guessArmatureFromList
        scn = context.scene
        scn.McpSourceRig = guessArmatureFromList(context.object, scn, _sourceInfo)          
        raise MocapMessage("Identified rig %s" % scn.McpSourceRig)
                      
#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MCP_OT_InitSources,
    MCP_OT_ListSourceRig,
    MCP_OT_VerifySourceRig,
    MCP_OT_IdentifySourceRig,
]

def initialize():
    bpy.types.Scene.McpSourceRig = EnumProperty(
        items = [("Automatic", "Automatic", "Automatic")],
        name = "Source Rig",
        default = "Automatic")  
        
    bpy.types.Scene.McpSourceTPose = EnumProperty(
        items = [("Default", "Default", "Default")],
        name = "Source T-pose",
        default = "Default")              

    bpy.types.Object.McpArmature = StringProperty()

    for cls in classes:
        bpy.utils.register_class(cls)


def uninitialize():
    for cls in classes:
        bpy.utils.unregister_class(cls)
