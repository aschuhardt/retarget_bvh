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

"""
Abstract
Tool for loading bvh files onto the MHX rig in Blender 2.5x

Place the script in the .blender/scripts/addons dir
Activate the script in the "Add-Ons" tab (user preferences).
Access from UI panel (N-key) when MHX rig is active.

Alternatively, run the script in the script editor (Alt-P), and access from UI panel.
"""

bl_info = {
    "name": "Retarget BVH",
    "author": "Thomas Larsson",
    "version": (2,0),
    "blender": (2,80,0),
    "location": "View3D > Tools > Retarget BVH",
    "description": "Mocap retargeting tool",
    "warning": "",
    'wiki_url': "http://diffeomorphic.blogspot.com/retarget-bvh/",
    "category": "Animation"}

# To support reload properly, try to access a package var, if it's there, reload everything
if "bpy" in locals():
    print("Reloading BVH Retargeter")
    import imp
    imp.reload(utils)
    imp.reload(io_json)
    imp.reload(props)
    imp.reload(t_pose)
    imp.reload(armature)
    imp.reload(source)
    imp.reload(target)
    imp.reload(load)
    imp.reload(retarget)
    imp.reload(fkik)
    imp.reload(simplify)
    imp.reload(action)
    imp.reload(loop)
    imp.reload(edit)
    imp.reload(floor)
else:
    print("Loading BVH Retargeter")
    import bpy

    from . import utils
    from . import io_json
    from . import props
    from . import t_pose
    from . import armature
    from . import source
    from . import target
    from . import load
    from . import retarget
    from . import fkik
    from . import simplify
    from . import action
    from . import loop
    from . import edit
    from . import floor

def inset(layout):
    split = layout.split(factor=0.05)
    split.label(text="")
    return split.column()

########################################################################
#
#   class Main(bpy.types.Panel):
#

class MCP_PT_Main(bpy.types.Panel):
    bl_category = "Retarget BVH"
    bl_label = "Retarget BVH v %d.%d: Main" % bl_info["version"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        ob = context.object
        scn = context.scene
        layout.operator("mcp.load_and_retarget")
        layout.separator()
        layout.prop(scn, "McpStartFrame")
        layout.prop(scn, "McpEndFrame")
        
        layout.separator()
        if target.isTargetInited(scn):
            text = "Reinit Target Panel"
        else:
            text = "Init Target Panel"
        layout.operator("mcp.init_targets", text=text)
        layout.prop(scn, "McpTargetRig")
        layout.prop(scn, "McpTargetTPose")
        
        layout.separator()
        layout.prop(scn, "McpShowDetailSteps")
        if scn.McpShowDetailSteps:
            ins = inset(layout)
            ins.operator("mcp.load_bvh")
            if ob and ob.type == 'ARMATURE':
                ins.operator("mcp.rename_bvh")
                ins.operator("mcp.load_and_rename_bvh")

                ins.separator()
                ins.operator("mcp.retarget_mhx")

                ins.separator()
                ins.operator("mcp.simplify_fcurves")
                ins.operator("mcp.rescale_fcurves")

########################################################################
#
#   class MCP_PT_Options(bpy.types.Panel):
#

class MCP_PT_Options(bpy.types.Panel):
    bl_category = "Retarget BVH"
    bl_label = "Options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.object and context.object.type == 'ARMATURE':
            return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        rig = context.object

        layout.prop(scn, "McpAutoScale")
        layout.prop(scn, "McpBvhScale")
        layout.prop(scn, "McpUseLimits")
        layout.prop(scn, "McpClearLocks")
        layout.prop(scn, "McpIgnoreHiddenLayers")
        layout.prop(scn, "McpDoBendPositive")

        layout.separator()
        layout.label(text="SubSample and Rescale")
        ins = inset(layout)
        ins.prop(scn, "McpDefaultSS")
        if not scn.McpDefaultSS:
            ins.prop(scn, "McpSubsample")
            ins.prop(scn, "McpSSFactor")
            ins.prop(scn, "McpRescale")
            ins.prop(scn, "McpRescaleFactor")
            ins.operator("mcp.rescale_fcurves")

        layout.separator()
        layout.label(text="Simplification")
        ins = inset(layout)
        ins.prop(scn, "McpDoSimplify")
        ins.prop(scn, "McpErrorLoc")
        ins.prop(scn, "McpErrorRot")
        ins.prop(scn, "McpSimplifyVisible")
        ins.prop(scn, "McpSimplifyMarkers")


########################################################################
#
#   class MCP_PT_Edit(bpy.types.Panel):
#

class MCP_PT_Edit(bpy.types.Panel):
    bl_category = "Retarget BVH"
    bl_label = "Edit Actions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.object and context.object.type == 'ARMATURE':
            return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        rig = context.object

        layout.prop(scn, "McpShowIK")
        if scn.McpShowIK:
            ins = inset(layout)
            row = ins.row()
            row.prop(scn, "McpFkIkArms")
            row.prop(scn, "McpFkIkLegs")
            ins.operator("mcp.transfer_to_ik")
            ins.operator("mcp.transfer_to_fk")
            ins.operator("mcp.clear_animation", text="Clear IK Animation").type = "IK"
            ins.operator("mcp.clear_animation", text="Clear FK Animation").type = "FK"

        layout.separator()
        layout.prop(scn, "McpShowGlobal")
        if scn.McpShowGlobal:
            ins = inset(layout)
            ins.operator("mcp.shift_bone")

            #ins.separator()
            #row = ins.row()
            #row.prop(scn, "McpBendElbows")
            #row.prop(scn, "McpBendKnees")
            #ins.operator("mcp.limbs_bend_positive")

            ins.separator()
            row = ins.row()
            row.prop(scn, "McpFixX")
            row.prop(scn, "McpFixY")
            row.prop(scn, "McpFixZ")
            ins.operator("mcp.fixate_bone")

            ins.separator()
            ins.prop(scn, "McpRescaleFactor")
            ins.operator("mcp.rescale_fcurves")

        layout.separator()
        layout.prop(scn, "McpShowDisplace")
        if scn.McpShowDisplace:
            ins = inset(layout)
            ins.operator("mcp.start_edit")
            ins.operator("mcp.undo_edit")

            row = ins.row()
            props = row.operator("mcp.insert_key", text="Loc")
            props.loc = True
            props.rot = False
            props.delete = False
            props = row.operator("mcp.insert_key", text="Rot")
            props.loc = False
            props.rot = True
            props.delete = False
            row = ins.row()
            props = row.operator("mcp.insert_key", text="LocRot")
            props.loc = True
            props.rot = True
            props.delete = False
            props = row.operator("mcp.insert_key", text="Delete")
            props.loc = True
            props.rot = True
            props.delete = True

            row = ins.row()
            props = row.operator("mcp.move_to_marker", text="|<")
            props.left = True
            props.last = True
            props = row.operator("mcp.move_to_marker", text="<")
            props.left = True
            props.last = False
            props = row.operator("mcp.move_to_marker", text=">")
            props.left = False
            props.last = False
            props = row.operator("mcp.move_to_marker", text=">|")
            props.left = False
            props.last = True

            ins.operator("mcp.confirm_edit")

        layout.separator()
        layout.prop(scn, "McpShowFeet")
        if scn.McpShowFeet:
            ins = inset(layout)
            row = ins.row()
            row.prop(scn, "McpFloorLeft")
            row.prop(scn, "McpFloorRight")
            row.prop(scn, "McpFloorHips")
            ins.operator("mcp.offset_toe")
            ins.operator("mcp.floor_foot")

        layout.separator()
        layout.prop(scn, "McpShowLoop")
        if scn.McpShowLoop:
            ins = inset(layout)
            ins.prop(scn, "McpLoopBlendRange")
            ins.prop(scn, "McpLoopInPlace")
            ins.operator("mcp.loop_fcurves")

            ins.separator()
            ins.prop(scn, "McpRepeatNumber")
            ins.operator("mcp.repeat_fcurves")

        layout.separator()
        layout.prop(scn, "McpShowStitch")
        if scn.McpShowStitch:
            ins = inset(layout)
            ins.operator("mcp.update_action_list")
            ins.separator()
            ins.prop(scn, "McpFirstAction")
            split = ins.split(0.75)
            split.prop(scn, "McpFirstEndFrame")
            split.operator("mcp.set_current_action").prop = "McpFirstAction"
            ins.separator()
            ins.prop(scn, "McpSecondAction")
            split = ins.split(0.75)
            split.prop(scn, "McpSecondStartFrame")
            split.operator("mcp.set_current_action").prop = "McpSecondAction"
            ins.separator()
            ins.prop(scn, "McpLoopBlendRange")
            ins.prop(scn, "McpOutputActionName")
            ins.operator("mcp.stitch_actions")

########################################################################
#
#    class MCP_PT_MhxSourceBones(bpy.types.Panel):
#

class MCP_PT_MhxSourceBones(bpy.types.Panel):
    bl_category = "Retarget BVH"
    bl_label = "Source armature"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE')

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        rig = context.object

        if not source.isSourceInited(scn):
            layout.operator("mcp.init_sources", text="Init Source Panel")
            return
        layout.operator("mcp.init_sources", text="Reinit Source Panel")
        layout.prop(scn, "McpSourceRig")
        layout.prop(scn, "McpSourceTPose")
        
        if scn.McpSourceRig:
            from .source import getSourceArmature

            amt = getSourceArmature(scn.McpSourceRig)
            if amt:
                bones = amt.boneNames
                box = layout.box()
                for boneText in target.TargetBoneNames:
                    if not boneText:
                        box.separator()
                        continue
                    (mhx, text) = boneText
                    bone = source.findSourceKey(mhx, bones)
                    if bone:
                        row = box.row()
                        row.label(text=text)
                        row.label(text=bone)

########################################################################
#
#    class MCP_PT_MhxTargetBones(bpy.types.Panel):
#

class MCP_PT_MhxTargetBones(bpy.types.Panel):
    bl_category = "Retarget BVH"
    bl_label = "Target armature"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE')

    def draw(self, context):
        layout = self.layout
        rig = context.object
        scn = context.scene

        if not target.isTargetInited(scn):
            layout.operator("mcp.init_targets", text="Init Target Panel")
            return
        layout.operator("mcp.init_targets", text="Reinit Target Panel")
        layout.separator()
        layout.prop(scn, "McpTargetRig")
        layout.prop(scn, "McpTargetTPose")

        layout.separator()
        layout.prop(scn, "McpIgnoreHiddenLayers")
        layout.prop(rig, "MhReverseHip")
        layout.operator("mcp.get_target_rig")
        layout.separator()
        layout.prop(scn, "McpSaveTargetTPose")
        layout.operator("mcp.save_target_file")

        layout.separator()

        if scn.McpTargetRig:
            from .target import getTargetInfo, TargetBoneNames, findTargetKeys

            (bones, ikBones, bendTwist) = getTargetInfo(scn.McpTargetRig)

            layout.label(text="FK bones")
            box = layout.box()
            for boneText in TargetBoneNames:
                if not boneText:
                    box.separator()
                    continue
                (mhx, text) = boneText
                bnames = findTargetKeys(mhx, bones)
                if bnames:
                    for bname in bnames:
                        row = box.row()
                        row.label(text=text)
                        row.label(text=bname)
                else:
                    row = box.row()
                    row.label(text=text)
                    row.label(text="-")

            if ikBones:
                row = layout.row()
                row.label(text="IK bone")
                row.label(text="FK bone")
                box = layout.box()
                for (ikBone, fkBone) in ikBones:
                    row = box.row()
                    row.label(text=ikBone)
                    row.label(text=fkBone)

            if bendTwist:
                row = layout.row()
                row.label(text="Bend bone")
                row.label(text="Twist bone")
                box = layout.box()
                for (bendBone, twistBone) in bendTwist:
                    row = box.row()
                    row.label(text=bendBone)
                    row.label(text=twistBone)


########################################################################
#
#   class MCP_PT_Utility(bpy.types.Panel):
#

class MCP_PT_Poses(bpy.types.Panel):
    bl_category = "Retarget BVH"
    bl_label = "Poses"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.object and context.object.type == 'ARMATURE':
            return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        rig = context.object

        layout.prop(scn, "McpSourceTPose")
        layout.prop(scn, "McpTargetTPose")
        layout.separator()
        layout.operator("mcp.put_in_t_pose")
        layout.separator()
        layout.operator("mcp.define_t_pose")
        layout.operator("mcp.undefine_t_pose")
        layout.separator()
        layout.operator("mcp.load_pose")
        layout.operator("mcp.save_pose")
        layout.separator()
        layout.operator("mcp.rest_current_pose")

########################################################################
#
#   class MCP_PT_Utility(bpy.types.Panel):
#

class MCP_PT_Utility(bpy.types.Panel):
    bl_category = "Retarget BVH"
    bl_label = "Utilities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.object and context.object.type == 'ARMATURE':
            return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        rig = context.object

        layout.prop(scn, "McpShowDefaultSettings")
        if scn.McpShowDefaultSettings:
            ins = inset(layout)
            ins.operator("mcp.save_defaults")
            ins.operator("mcp.load_defaults")

        layout.separator()
        layout.prop(scn, "McpShowActions")
        if scn.McpShowActions:
            ins = inset(layout)
            ins.prop_menu_enum(context.scene, "McpActions")
            ins.prop(scn, 'McpFilterActions')
            ins.operator("mcp.update_action_list")
            ins.operator("mcp.set_current_action").prop = 'McpActions'
            ins.operator("mcp.delete")
            ins.operator("mcp.delete_hash")


        layout.separator()
        layout.operator("mcp.clear_temp_props")

        return
        layout.operator("mcp.copy_angles_fk_ik")

        layout.separator()
        layout.label(text="Batch conversion")
        layout.prop(scn, "McpDirectory")
        layout.prop(scn, "McpPrefix")
        layout.operator("mcp.batch")

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MCP_PT_Main,
    MCP_PT_Options,
    MCP_PT_Edit,
    MCP_PT_MhxSourceBones,
    MCP_PT_MhxTargetBones,
    MCP_PT_Poses,
    MCP_PT_Utility,

    utils.ErrorOperator
]

def register():
    action.initialize()
    edit.initialize()
    fkik.initialize()
    floor.initialize()
    load.initialize()
    loop.initialize()
    props.initialize()
    retarget.initialize()
    simplify.initialize()
    source.initialize()
    t_pose.initialize()
    target.initialize()

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    action.uninitialize()
    edit.uninitialize()
    fkik.uninitialize()
    floor.uninitialize()
    load.uninitialize()
    loop.uninitialize()
    props.uninitialize()
    retarget.uninitialize()
    simplify.uninitialize()
    source.uninitialize()
    t_pose.uninitialize()
    target.uninitialize()

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

print("BVH Retargeter loaded")

