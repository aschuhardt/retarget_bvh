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

#
#    readDirectory(directory, prefix):
#    class MCP_OT_Batch(bpy.types.Operator):
#

def readDirectory(directory, prefix):
    import os
    realdir = os.path.realpath(os.path.expanduser(directory))
    files = os.listdir(realdir)
    n = len(prefix)
    paths = []
    for fileName in files:
        (name, ext) = os.path.splitext(fileName)
        if name[:n] == prefix and ext == ".bvh":
            paths.append("%s/%s" % (realdir, fileName))
    return paths


class MCP_OT_Batch(bpy.types.Operator):
    bl_idname = "mcp.batch"
    bl_label = "Batch run"
    bl_options = {'UNDO'}

    def execute(self, context):
        paths = readDirectory(context.scene.McpDirectory, context.scene.McpPrefix)
        trgRig = context.object
        for filepath in paths:
            setActiveObject(context, trgRig)
            loadRetargetSimplify(context, filepath)
        return{"FINISHED"}

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MCP_OT_Batch,
]

def initialize():
    # Showing

    bpy.types.Scene.McpShowDetailSteps = BoolProperty(
        name="Detailed Steps",
        description="Show retarget steps",
        default=False)

    bpy.types.Scene.McpShowIK = BoolProperty(
        name="Inverse Kinematics",
        description="Show inverse kinematics",
        default=False)

    bpy.types.Scene.McpShowGlobal = BoolProperty(
        name="Global Edit",
        description="Show global edit",
        default=False)

    bpy.types.Scene.McpShowDisplace = BoolProperty(
        name="Local Edit",
        description="Show local edit",
        default=False)

    bpy.types.Scene.McpShowFeet = BoolProperty(
        name="Feet",
        description="Show feet",
        default=False)

    bpy.types.Scene.McpShowLoop = BoolProperty(
        name="Loop And Repeat",
        description="Show loop and repeat",
        default=False)

    bpy.types.Scene.McpShowStitch = BoolProperty(
        name="Stitching",
        description="Show stitching",
        default=False)

    bpy.types.Scene.McpShowDefaultSettings = BoolProperty(
        name="Default Settings",
        description="Show default settings",
        default=False)

    bpy.types.Scene.McpShowActions = BoolProperty(
        name="Manage Actions",
        description="Show manage actions",
        default=False)

    bpy.types.Scene.McpShowPosing = BoolProperty(
        name="Posing",
        description="Show posing",
        default=False)


    # Load and retarget

    bpy.types.Scene.McpBvhScale = FloatProperty(
        name="Scale",
        description="Scale the BVH by this value",
        min=0.0001, max=1000000.0,
        soft_min=0.001, soft_max=100.0,
        default=0.65)

    bpy.types.Scene.McpAutoScale = BoolProperty(
        name="Auto Scale",
        description="Rescale skeleton to match target",
        default=True)

    bpy.types.Scene.McpUseLimits = BoolProperty(
        name="Use Limits",
        description="Restrict angles to Limit Rotation constraints",
        default=True)

    bpy.types.Scene.McpStartFrame = IntProperty(
        name="Start Frame",
        description="Default starting frame for the animation",
        default=1)

    bpy.types.Scene.McpEndFrame = IntProperty(
        name="Last Frame",
        description="Default last frame for the animation",
        default=250)

    bpy.types.Scene.McpRot90Anim = BoolProperty(
        name="Rotate 90 deg",
        description="Rotate 90 degress so Z points up",
        default=True)

    bpy.types.Scene.McpClearLocks = BoolProperty(
        name="Unlock Rotation",
        description="Clear X and Z rotation locks",
        default=False)

    bpy.types.Scene.McpFlipYAxis = BoolProperty(
        name="Flix Y Axis",
        description="Rotate 180 degress so Y points down (for Ni-Mate)",
        default=False)

    bpy.types.Scene.McpDoSimplify = BoolProperty(
        name="Simplify FCurves",
        description="Simplify FCurves",
        default=True)

    bpy.types.Object.McpIsTargetRig = BoolProperty(
        name="Is Target Rig",
        default=False)

    bpy.types.Object.McpIsSourceRig = BoolProperty(
        name="Is Source Rig",
        default=False)

    bpy.types.Object.McpRenamed = BoolProperty(default = False)


    # Subsample and rescale

    bpy.types.Scene.McpSubsample = BoolProperty(
        name="Subsample",
        default=True)

    bpy.types.Scene.McpSSFactor = IntProperty(
        name="Subsample Factor",
        description="Sample only every n:th frame",
        min=1, default=1)

    bpy.types.Scene.McpRescale = BoolProperty(
        name="Rescale",
        description="Rescale F-curves after loading",
        default=False)

    bpy.types.Scene.McpRescaleFactor = FloatProperty(
        name="Rescale Factor",
        description="Factor for rescaling time",
        min=0.01, max=100, default=1.0)

    bpy.types.Scene.McpDefaultSS = BoolProperty(
        name="Use default subsample",
        default=True)

    # Simplify

    bpy.types.Scene.McpSimplifyVisible = BoolProperty(
        name="Only Visible",
        description="Simplify only visible F-curves",
        default=False)

    bpy.types.Scene.McpSimplifyMarkers = BoolProperty(
        name="Only Between Markers",
        description="Simplify only between markers",
        default=False)

    bpy.types.Scene.McpErrorLoc = FloatProperty(
        name="Max Loc Error",
        description="Max error for location FCurves when doing simplification",
        min=0.001,
        default=0.01)

    bpy.types.Scene.McpErrorRot = FloatProperty(
        name="Max Rot Error",
        description="Max error for rotation (degrees) FCurves when doing simplification",
        min=0.001,
        default=0.1)

    # Inverse kinematics

    bpy.types.Scene.McpIkAdjustXY = BoolProperty(
        name="IK Adjust XY",
        description="Adjust XY coordinates of IK handle",
        default=True)

    bpy.types.Scene.McpFkIkArms = BoolProperty(
        name="Arms",
        description="Include arms in FK/IK snapping",
        default=False)

    bpy.types.Scene.McpFkIkLegs = BoolProperty(
        name="Legs",
        description="Include legs in FK/IK snapping",
        default=True)

    # Floor

    bpy.types.Scene.McpFloorLeft = BoolProperty(
        name="Left",
        description="Keep left foot above floor",
        default=True)

    bpy.types.Scene.McpFloorRight = BoolProperty(
        name="Right",
        description="Keep right foot above floor",
        default=True)

    bpy.types.Scene.McpFloorHips = BoolProperty(
        name="Hips",
        description="Also adjust character COM when keeping feet above floor",
        default=True)

    bpy.types.Scene.McpBendElbows = BoolProperty(
        name="Elbows",
        description="Keep elbow bending positive",
        default=True)

    bpy.types.Scene.McpBendKnees = BoolProperty(
        name="Knees",
        description="Keep knee bending positive",
        default=True)

    bpy.types.Scene.McpDoBendPositive = BoolProperty(
        name="Bend Positive",
        description="Ensure that elbow and knee bending is positive",
        default=True)

    # Loop

    bpy.types.Scene.McpLoopBlendRange = IntProperty(
        name="Blend Range",
        min=1,
        default=5)

    bpy.types.Scene.McpLoopInPlace = BoolProperty(
        name="Loop in place",
        description="Remove Location F-curves",
        default=False)

    bpy.types.Scene.McpLoopZInPlace = BoolProperty(
        name="In Place Affects Z",
        default=False)

    bpy.types.Scene.McpRepeatNumber = IntProperty(
        name="Repeat Number",
        min=1,
        default=1)

    bpy.types.Scene.McpFirstEndFrame = IntProperty(
        name="First End Frame",
        default=1)

    bpy.types.Scene.McpSecondStartFrame = IntProperty(
        name="Second Start Frame",
        default=1)

    bpy.types.Scene.McpActionTarget = EnumProperty(
        items = [('Stitch new', 'Stitch new', 'Stitch new'),
                 ('Prepend second', 'Prepend second', 'Prepend second')],
        name = "Action Target")

    bpy.types.Scene.McpOutputActionName = StringProperty(
        name="Output Action Name",
        maxlen=24,
        default="Action")

    bpy.types.Scene.McpFixX = BoolProperty(
        name="X",
        description="Fix Local X Location",
        default=True)

    bpy.types.Scene.McpFixY = BoolProperty(
        name="Y",
        description="Fix Local Y Location",
        default=True)

    bpy.types.Scene.McpFixZ = BoolProperty(
        name="Z",
        description="Fix Local Z Location",
        default=True)

    # Edit

    bpy.types.Object.McpUndoAction = StringProperty(
        default="")

    bpy.types.Object.McpActionName = StringProperty(
        default="")

    # Props

    bpy.types.Scene.McpDirectory = StringProperty(
        name="Directory",
        description="Directory",
        maxlen=1024,
        default="")

    bpy.types.Scene.McpPrefix = StringProperty(
        name="Prefix",
        description="Prefix",
        maxlen=24,
        default="")

    # T_Pose

    bpy.types.Scene.McpAutoCorrectTPose = BoolProperty(
        name = "Auto Correct T-Pose",
        description = "Automatically F-curves to fit T-pose at frame 0",
        default = True)

    bpy.types.Object.McpTPoseDefined = BoolProperty(
        default = False)

    bpy.types.Object.McpTPoseFile = StringProperty(
        default = "")

    bpy.types.Object.McpArmatureName = StringProperty(
        default = "")

    bpy.types.Object.McpArmatureModifier = StringProperty(
        default = "")

    bpy.types.PoseBone.McpQuat = FloatVectorProperty(size=4, default=(1,0,0,0))

    # Source and Target

    bpy.types.Scene.McpMakeHumanTPose = BoolProperty(
        name = "MakeHuman T-pose",
        description = "Use MakeHuman T-pose for MakeHuman characters",
        default = True)

    bpy.types.Object.MhReverseHip = BoolProperty(
        name = "Reverse Hip",
        description = "The rig has a reverse hip",
        default = False)

    bpy.types.Scene.McpIgnoreHiddenLayers = BoolProperty(
        name = "Ignore Hidden Layers",
        description = "Ignore bones on hidden layers when identifying target rig",
        default = True)

    bpy.types.Scene.McpSaveTargetTPose = BoolProperty(
        name = "Save T-Pose",
        description = "Save the current pose as T-pose when saving target file",
        default = False)

    bpy.types.PoseBone.McpBone = StringProperty(
        description = "MakeHuman bone corresponding to this bone",
        default = "")

    bpy.types.PoseBone.McpParent = StringProperty(
        description = "Parent of this bone for retargeting purposes",
        default = "")


    # Manage actions

    bpy.types.Scene.McpFilterActions = BoolProperty(
        name="Filter",
        description="Filter action names",
        default=False)

    bpy.types.Scene.McpReallyDelete = BoolProperty(
        name="Really Delete",
        description="Delete button deletes action permanently",
        default=False)

    bpy.types.Scene.McpActions = EnumProperty(
        items = [],
        name = "Actions")

    bpy.types.Scene.McpFirstAction = EnumProperty(
        items = [],
        name = "First Action")

    bpy.types.Scene.McpSecondAction = EnumProperty(
        items = [],
        name = "Second Action")

    bpy.types.Object.McpArmature = StringProperty()
    bpy.types.Object.McpLimitsOn = BoolProperty(default=True)
    bpy.types.Object.McpChildOfsOn = BoolProperty(default=False)
    bpy.types.Object.MhAlpha8 = BoolProperty(default=False)

    for cls in classes:
        bpy.utils.register_class(cls)


def uninitialize():
    for cls in classes:
        bpy.utils.unregister_class(cls)
