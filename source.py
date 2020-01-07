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

#
#   Global variables
#

#_sourceArmatures = { "Automatic" : None }
_sourceArmatures = {}
_srcArmature = None

def getSourceArmature(name):
    global _sourceArmatures
    return _sourceArmatures[name]

def getSourceBoneName(bname):
    global _srcArmature
    lname = canonicalName(bname)
    try:
        return _srcArmature.boneNames[lname]
    except KeyError:
        return None

def getSourceTPoseFile():
    global _srcArmature
    return _srcArmature.tposeFile

def isSourceInited(scn):
    global _sourceArmatures
    return (_sourceArmatures != {})

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
    for name in _sourceArmatures.keys():
        if name == "Automatic":
            continue
        amt = _sourceArmatures[name]
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
        amt = _sourceArmatures[best.name]
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
    global _srcArmature, _sourceArmatures
    from .t_pose import autoTPose, defineTPose, putInRestPose
    scn = context.scene

    setCategory("Identify Source Rig")
    ensureSourceInited(scn)
    if auto or scn.McpSourceRig == "Automatic":
        amt = _srcArmature = CArmature()
        putInRestPose(rig, True)
        amt.findArmature(rig)
        autoTPose(rig, context)
        #defineTPose(rig)
        _sourceArmatures["Automatic"] = amt
        amt.display("Source")
    else:
        _srcArmature = _sourceArmatures[scn.McpSourceRig]

    rig.McpArmature = _srcArmature.name
    print("Using matching armature %s." % rig.McpArmature)
    clearCategory()

#
#    setSourceArmature(rig, scn)
#

def setSourceArmature(rig, scn):
    global _srcArmature, _sourceArmatures
    name = rig.McpArmature
    if name:
        scn.McpSourceRig = name
    else:
        raise MocapError("No source armature set")
    _srcArmature = _sourceArmatures[name]
    print("Set source armature to %s" % name)

#
#   findSourceKey(mhx, struct):
#

def findSourceKey(bname, struct):
    for bone in struct.keys():
        if bname == struct[bone]:
            return bone
    return None

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
        from .source import findSourceArmature
        return findSourceArmature(context, rig, self.useAutoSource)

#----------------------------------------------------------
#   Source initialization
#----------------------------------------------------------

class MCP_OT_InitSources(bpy.types.Operator):
    bl_idname = "mcp.init_sources"
    bl_label = "Init Source Panel"
    bl_options = {'UNDO'}

    def execute(self, context):
        from .t_pose import initTPoses, initSourceTPose
        setVerbose(True)
        initSources(context.scene)
        initTPoses()
        initSourceTPose(context.scene)
        return{'FINISHED'}


def initSources(scn):
    global _sourceArmatures, _srcArmatureEnums

    _sourceArmatures = { "Automatic" : CArmature() }
    path = os.path.join(os.path.dirname(__file__), "source_rigs")
    for fname in os.listdir(path):
        file = os.path.join(path, fname)
        (name, ext) = os.path.splitext(fname)
        if ext == ".json" and os.path.isfile(file):    
            armature = readSrcArmature(file, name)
            _sourceArmatures[armature.name] = armature
    _srcArmatureEnums = [("Automatic", "Automatic", "Automatic")]
    keys = list(_sourceArmatures.keys())
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
    armature = CArmature()
    armature.name = struct["name"]
    bones = armature.boneNames
    for key,value in struct["armature"].items():
        bones[canonicalName(key)] = nameOrNone(value)
    return armature


#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MCP_OT_InitSources,
]

def initialize():
    bpy.types.Scene.McpSourceRig = EnumProperty(
        items = [("Automatic", "Automatic", "Automatic")],
        name = "Source rig",
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
