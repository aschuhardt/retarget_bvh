# ------------------------------------------------------------------------------
#   BSD 2-Clause License
#   
#   Copyright (c) 2019, Thomas Larsson
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
from math import sin, cos, atan, pi
from mathutils import *

Deg2Rad = pi/180
Rad2Deg = 180/pi


#-------------------------------------------------------------
#   Blender 2.8 compatibility
#-------------------------------------------------------------

def setActiveObject(context, ob):
    vly = context.view_layer
    vly.objects.active = ob
    vly.update()


def updateScene():
    deps = bpy.context.evaluated_depsgraph_get()
    deps.update()
    scn = bpy.context.scene
    scn.frame_current = scn.frame_current
    
#
#   printMat3(string, mat)
#

def printMat3(string, mat, pad=""):
    if not mat:
        print("%s None" % string)
        return
    print("%s " % string)
    mc = "%s  [" % pad
    for m in range(3):
        s = mc
        for n in range(3):
            s += " %6.3f" % mat[m][n]
        print(s+"]")

def printMat4(string, mat, pad=""):
    if not mat:
        print("%s None" % string)
        return
    print("%s%s " % (pad, string))
    mc = "%s  [" % pad
    for m in range(4):
        s = mc
        for n in range(4):
            s += " %6.3f" % mat[m][n]
        print(s+"]")

#
#  quadDict():
#

def quadDict():
    return {
        0: {},
        1: {},
        2: {},
        3: {},
    }

MhxLayers = 8*[True] + 8*[False] + 8*[True] + 8*[False]
RigifyLayers = 27*[True] + 5*[False]

#
#   Identify rig type
#

def hasAllBones(blist, rig):
    for bname in blist:
        if bname not in rig.pose.bones.keys():
            return False
    return True

def isMhxRig(rig):
    return hasAllBones(["foot.rev.L"], rig)

def isMhOfficialRig(rig):
    return hasAllBones(["risorius03.R"], rig)

def isMhx7Rig(rig):
    return hasAllBones(["FootRev_L"], rig)

def isRigify(rig):
    return hasAllBones(["MCH-spine.flex"], rig)

def isRigify2(rig):
    return hasAllBones(["MCH-upper_arm_ik.L"], rig)

def isGenesis38(rig):
    return (hasAllBones(["abdomenLower", "lShldrBend"], rig) and
            not isGenesis12(rig))

def isGenesis12(rig):
    return hasAllBones(["abdomen2", "lShldr"], rig)

def isMakeHumanRig(rig):
    return ("MhAlpha8" in rig.keys())

#
#   nameOrNone(string):
#

def nameOrNone(string):
    if string == "None":
        return None
    else:
        return string


def canonicalName(string):
    return string.lower().replace(' ','_').replace('-','_')


#
#   getRoll(bone):
#

def getRoll(bone):
    return getRollMat(bone.matrix_local)


def getRollMat(mat):
    quat = mat.to_3x3().to_quaternion()
    if abs(quat.w) < 1e-4:
        roll = pi
    else:
        roll = -2*atan(quat.y/quat.w)
    return roll


#
#   getTrgBone(b):
#

def getTrgBone(bname, rig):
    for pb in rig.pose.bones:
        if pb.McpBone == bname:
            return pb
    return None

#
#
#

def insertLocation(pb, mat):
    pb.location = mat.to_translation()
    pb.keyframe_insert("location", group=pb.name)


def insertRotation(pb, mat):
    q = mat.to_quaternion()
    if pb.rotation_mode == 'QUATERNION':
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", group=pb.name)
    else:
        pb.rotation_euler = q.to_euler(pb.rotation_mode)
        pb.keyframe_insert("rotation_euler", group=pb.name)


def isRotationMatrix(mat):
    mat = mat.to_3x3()
    prod = mat @ mat.transposed()
    diff = prod - Matrix().to_3x3()
    for i in range(3):
        for j in range(3):
            if abs(diff[i][j]) > 1e-3:
                print("Not a rotation matrix")
                print(mat)
                print(prod)
                return False
    return True

#
#   fCurveIdentity(fcu):
#

def fCurveIdentity(fcu):
    words = fcu.data_path.split('"')
    if len(words) < 2:
        return (None, None)
    name = words[1]
    words = fcu.data_path.split('.')
    mode = words[-1]
    return (name, mode)

#
#   findFCurve(path, index, fcurves):
#

def findFCurve(path, index, fcurves):
    for fcu in fcurves:
        if (fcu.data_path == path and
            fcu.array_index == index):
            return fcu
    print('F-curve "%s" not found.' % path)
    return None


def findBoneFCurve(pb, rig, index, mode='rotation'):
    if mode == 'rotation':
        if pb.rotation_mode == 'QUATERNION':
            mode = "rotation_quaternion"
        else:
            mode = "rotation_euler"
    path = 'pose.bones["%s"].%s' % (pb.name, mode)

    if rig.animation_data is None:
        return None
    action = rig.animation_data.action
    if action is None:
        return None
    return findFCurve(path, index, action.fcurves)


def fillKeyFrames(pb, rig, frames, nIndices, mode='rotation'):
    for index in range(nIndices):
        fcu = findBoneFCurve(pb, rig, index, mode)
        if fcu is None:
            return
        for frame in frames:
            y = fcu.evaluate(frame)
            fcu.keyframe_points.insert(frame, y, options={'FAST'})

#
#   isRotation(mode):
#   isLocation(mode):
#

def isRotation(mode):
    return (mode[0:3] == 'rot')

def isLocation(mode):
    return (mode[0:3] == 'loc')


#
#    setRotation(pb, mat, frame, group):
#

def setRotation(pb, rot, frame, group):
    if pb.rotation_mode == 'QUATERNION':
        try:
            quat = rot.to_quaternion()
        except:
            quat = rot
        pb.rotation_quaternion = quat
        pb.keyframe_insert('rotation_quaternion', frame=frame, group=group)
    else:
        try:
            euler = rot.to_euler(pb.rotation_mode)
        except:
            euler = rot
        pb.rotation_euler = euler
        pb.keyframe_insert('rotation_euler', frame=frame, group=group)


#
#   putInRestPose(rig, useSetKeys):
#

def putInRestPose(rig, useSetKeys):
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix()
        setKeys(pb, useSetKeys)
        
        
def setKeys(pb, useSetKeys):        
    if useSetKeys:
        if pb.rotation_mode == 'QUATERNION':
            pb.keyframe_insert('rotation_quaternion')
        else:
            pb.keyframe_insert('rotation_euler')
        pb.keyframe_insert('location')

#
#    setInterpolation(rig):
#

def setInterpolation(rig):
    if not rig.animation_data:
        return
    act = rig.animation_data.action
    if not act:
        return
    for fcu in act.fcurves:
        for pt in fcu.keyframe_points:
            pt.interpolation = 'LINEAR'
        fcu.extrapolation = 'CONSTANT'
    return

#
#   insertRotationKeyFrame(pb, frame):
#

def insertRotationKeyFrame(pb, frame):
    rotMode = pb.rotation_mode
    grp = pb.name
    if rotMode == "QUATERNION":
        pb.keyframe_insert("rotation_quaternion", frame=frame, group=grp)
    elif rotMode == "AXIS_ANGLE":
        pb.keyframe_insert("rotation_axis_angle", frame=frame, group=grp)
    else:
        pb.keyframe_insert("rotation_euler", frame=frame, group=grp)

#
#   checkObjectProblems(self, context):
#

def getObjectProblems(self, context):
    self.problems = ""
    epsilon = 1e-2
    rig = context.object

    eu = rig.rotation_euler
    print(eu)
    if abs(eu.x) + abs(eu.y) + abs(eu.z) > epsilon:
        self.problems += "object rotation\n"

    vec = rig.scale - Vector((1,1,1))
    print(vec, vec.length)
    if vec.length > epsilon:
        self.problems += "object scaling\n"

    if self.problems:
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=300, height=20)
    else:
        return False


def checkObjectProblems(self, context):
    problems = getObjectProblems(self, context)
    if problems:
        return problems
    else:
        return self.execute(context)


def problemFreeFileSelect(self, context):
    problems = getObjectProblems(self, context)
    if problems:
        return problems
    context.window_manager.fileselect_add(self)
    return {'RUNNING_MODAL'}


def drawObjectProblems(self):
    if self.problems:
        self.layout.label(text="MakeWalk cannot use this rig because it has:")
        for problem in self.problems.split("\n"):
            self.layout.label(text="  %s" % problem)
        self.layout.label(text="Apply object transformations before using MakeWalk")

#
#   showProgress(n, frame):
#

def startProgress(string):
    print("%s (0 pct)" % string)


def endProgress(string):
    print("%s (100 pct)" % string)


def showProgress(n, frame, nFrames, step=20):
    if n % step == 0:
        print("%d (%.1f pct)" % (int(frame), (100.0*n)/nFrames))

#
#
#

_category = ""
_errorLines = ""

def setCategory(string):
    global _category
    _category = string

def clearCategory():
    global _category
    _category = "General error"

clearCategory()


class MocapError(Exception):
    def __init__(self, value):
        global _errorLines
        self.value = value
        _errorLines = (
            ["Category: %s" % _category] +
            value.split("\n") +
            ["" +
             "For corrective actions see:",
             "http://www.makehuman.org/doc/node/",
             "  makewalk_errors_and_corrective_actions.html"]
            )
        print("*** Mocap error ***")
        for line in _errorLines:
            print(line)

    def __str__(self):
        return repr(self.value)


class ErrorOperator(bpy.types.Operator):
    bl_idname = "mcp.error"
    bl_label = "Mocap error"

    def execute(self, context):
        clearCategory()
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        global _errorLines
        for line in _errorLines:
            self.layout.label(text=line)

