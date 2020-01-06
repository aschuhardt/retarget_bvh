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
    imp.reload(armature)
    imp.reload(source)
    imp.reload(target)
    imp.reload(t_pose)
    imp.reload(simplify)
    imp.reload(load)
    imp.reload(fkik)
    imp.reload(retarget)
    imp.reload(action)
    imp.reload(loop)
    imp.reload(edit)
    imp.reload(floor)
else:
    print("Loading BVH Retargeter")
    import bpy

    from . import utils
    from . import io_json
    from . import armature
    from . import source
    from . import target
    from . import t_pose
    from . import simplify
    from . import load
    from . import fkik
    from . import retarget
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
    bl_category = "BVH"
    bl_label = "Retarget BVH v %d.%d: Main" % bl_info["version"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        ob = context.object
        scn = context.scene
        layout.operator("mcp.load_and_retarget")
        layout.separator()
        layout.operator("mcp.load_bvh")        
        layout.separator()
        layout.operator("mcp.rename_bvh")
        layout.operator("mcp.load_and_rename_bvh")
        layout.operator("mcp.retarget_mhx")

########################################################################
#
#   class MCP_PT_Options(bpy.types.Panel):
#

class MCP_PT_Options(bpy.types.Panel):
    bl_category = "BVH"
    bl_label = "Options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scn = context.scene
        self.layout.prop(scn, "McpUseLimits")
        self.layout.prop(scn, "McpClearLocks")
        self.layout.prop(scn, "McpIgnoreHiddenLayers")

########################################################################
#
#   class MCP_PT_Edit(bpy.types.Panel):
#

class MCP_PT_Edit(bpy.types.Panel, utils.IsArmature):
    bl_category = "BVH"
    bl_label = "Edit Actions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        rig = context.object

        layout.prop(scn, "McpShowIK")
        if scn.McpShowIK:
            ins = inset(layout)
            ins.operator("mcp.offset_toes")
            ins.operator("mcp.transfer_to_ik")
            ins.operator("mcp.transfer_to_fk")
            ins.operator("mcp.clear_animation", text="Clear IK Animation").type = "IK"
            ins.operator("mcp.clear_animation", text="Clear FK Animation").type = "FK"

        layout.separator()
        layout.prop(scn, "McpShowGlobal")
        if scn.McpShowGlobal:
            ins = inset(layout)
            ins.operator("mcp.shift_bone")
            ins.operator("mcp.floor_foot")
            ins.operator("mcp.limbs_bend_positive")
            ins.operator("mcp.fixate_bone")
            ins.operator("mcp.simplify_fcurves")
            ins.operator("mcp.timescale_fcurves")

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
            ins.separator()
            ins.operator("mcp.clear_temp_props")

        layout.separator()
        layout.prop(scn, "McpShowLoop")
        if scn.McpShowLoop:
            ins = inset(layout)
            ins.operator("mcp.loop_fcurves")
            ins.operator("mcp.repeat_fcurves")
            ins.operator("mcp.stitch_actions")

########################################################################
#
#    class MCP_PT_MhxSourceBones(bpy.types.Panel):
#

class MCP_PT_MhxSourceBones(bpy.types.Panel, utils.IsArmature):
    bl_category = "BVH"
    bl_label = "Source armature"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

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

class MCP_PT_MhxTargetBones(bpy.types.Panel, utils.IsArmature):
    bl_category = "BVH"
    bl_label = "Target armature"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

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
        layout.prop(rig, "McpReverseHip")
        layout.operator("mcp.get_target_rig")
        layout.separator()
        layout.prop(scn, "McpSaveTargetTPose")
        layout.operator("mcp.save_target_file")

        layout.separator()

        if scn.McpTargetRig:
            from .target import getTargetInfo, TargetBoneNames, findTargetKeys

            info = getTargetInfo(scn.McpTargetRig)

            layout.label(text="Bones")
            box = layout.box()
            for boneText in TargetBoneNames:
                if not boneText:
                    box.separator()
                    continue
                (mhx, text) = boneText
                bnames = findTargetKeys(mhx, info.bones)
                if bnames:
                    for bname in bnames:
                        row = box.row()
                        row.label(text=text)
                        row.label(text=bname)
                else:
                    row = box.row()
                    row.label(text=text)
                    row.label(text="-")

########################################################################
#
#   class MCP_PT_Poses(bpy.types.Panel):
#

class MCP_PT_Poses(bpy.types.Panel, utils.IsArmature):
    bl_category = "BVH"
    bl_label = "Poses"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

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
#   class MCP_PT_Actions(bpy.types.Panel):
#

class MCP_PT_Actions(bpy.types.Panel, utils.IsArmature):
    bl_category = "BVH"
    bl_label = "Actions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        rig = context.object

        layout.operator("mcp.set_current_action")
        layout.operator("mcp.set_fake_user")
        layout.operator("mcp.delete_action")
        layout.operator("mcp.delete_hash")

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
    MCP_PT_Actions,

    utils.ErrorOperator
]

def register():
    from bpy.props import BoolProperty
    
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

    bpy.types.Scene.McpShowLoop = BoolProperty(
        name="Loop And Repeat",
        description="Show loop and repeat",
        default=False)
        
    action.initialize()
    edit.initialize()
    fkik.initialize()
    floor.initialize()
    load.initialize()
    loop.initialize()
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

