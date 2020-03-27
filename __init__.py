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

bl_info = {
    "name": "BVH Retargeter",
    "author": "Thomas Larsson",
    "version": (2,0),
    "blender": (2,80,0),
    "location": "View3D > Tools > Retarget BVH",
    "description": "Mocap retargeting tool",
    "warning": "",
    'wiki_url': "https://diffeomorphic.blogspot.com/p/bvh-retargeter.html",
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

from bpy.props import BoolProperty
    

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
        layout.separator()
        layout.operator("mcp.test")        

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
        self.layout.prop(scn, "McpVerbose")
        self.layout.prop(scn, "McpIncludeFingers")
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

        if not utils.isMhxRig(rig):
            pass
        elif not scn.McpShowIK:
            layout.prop(scn, "McpShowIK", icon="RIGHTARROW", emboss=False)
            layout.separator()
        else:
            layout.prop(scn, "McpShowIK", icon="DOWNARROW_HLT", emboss=False)
            layout.operator("mcp.offset_toes")
            layout.operator("mcp.transfer_to_ik")
            layout.operator("mcp.transfer_to_fk")
            layout.operator("mcp.clear_animation", text="Clear IK Animation").type = "IK"
            layout.operator("mcp.clear_animation", text="Clear FK Animation").type = "FK"
            layout.separator()

        if not scn.McpShowGlobal:
            layout.prop(scn, "McpShowGlobal", icon="RIGHTARROW", emboss=False)
        else:
            layout.prop(scn, "McpShowGlobal", icon="DOWNARROW_HLT", emboss=False)
            layout.operator("mcp.shift_animation")
            layout.operator("mcp.floor_foot")
            #layout.operator("mcp.limbs_bend_positive")
            layout.operator("mcp.fixate_bone")
            layout.operator("mcp.simplify_fcurves")
            layout.operator("mcp.timescale_fcurves")

        layout.separator()
        if not scn.McpShowDisplace:
            layout.prop(scn, "McpShowDisplace", icon="RIGHTARROW", emboss=False)
        else:
            layout.prop(scn, "McpShowDisplace", icon="DOWNARROW_HLT", emboss=False)
            layout.operator("mcp.start_edit")
            layout.operator("mcp.undo_edit")

            row = layout.row()
            props = row.operator("mcp.insert_key", text="Loc")
            props.loc = True
            props.rot = False
            props.delete = False
            props = row.operator("mcp.insert_key", text="Rot")
            props.loc = False
            props.rot = True
            props.delete = False
            row = layout.row()
            props = row.operator("mcp.insert_key", text="LocRot")
            props.loc = True
            props.rot = True
            props.delete = False
            props = row.operator("mcp.insert_key", text="Delete")
            props.loc = True
            props.rot = True
            props.delete = True

            row = layout.row()
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

            layout.operator("mcp.confirm_edit")
            layout.separator()
            layout.operator("mcp.clear_temp_props")

        layout.separator()
        if not scn.McpShowLoop:
            layout.prop(scn, "McpShowLoop", icon="RIGHTARROW", emboss=False)
        else:
            layout.prop(scn, "McpShowLoop", icon="DOWNARROW_HLT", emboss=False)
            layout.operator("mcp.loop_fcurves")
            layout.operator("mcp.repeat_fcurves")
            layout.operator("mcp.stitch_actions")

########################################################################
#
#    class MCP_PT_MhxSourceBones(bpy.types.Panel):
#

class MCP_PT_MhxSourceBones(bpy.types.Panel, utils.IsArmature):
    bl_category = "BVH"
    bl_label = "Source Armature"
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
        layout.prop(scn, "McpIncludeFingers")
        layout.separator()
        layout.operator("mcp.identify_source_rig")
        layout.operator("mcp.verify_source_rig")
        layout.operator("mcp.list_source_rig")
        layout.operator("mcp.put_in_t_pose")
        
########################################################################
#
#    class MCP_PT_MhxTargetBones(bpy.types.Panel):
#

class MCP_PT_MhxTargetBones(bpy.types.Panel, utils.IsArmature):
    bl_category = "BVH"
    bl_label = "Target Armature"
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
        layout.prop(scn, "McpIncludeFingers")
        layout.prop(scn, "McpIgnoreHiddenLayers")
        layout.prop(rig, "McpReverseHip")
        layout.separator()
        layout.operator("mcp.identify_target_rig")
        layout.operator("mcp.verify_target_rig")
        layout.operator("mcp.list_target_rig")
        layout.operator("mcp.put_in_t_pose")

########################################################################
#
#   class MCP_PT_Poses(bpy.types.Panel):
#

class MCP_PT_TPose(bpy.types.Panel, utils.IsArmature):
    bl_category = "BVH"
    bl_label = "T-Pose"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        rig = context.object

        layout.prop(scn, "McpSourceTPose", text="Source T-Pose")
        layout.prop(scn, "McpTargetTPose", text="Target T-Pose")
        layout.operator("mcp.put_in_t_pose")
        #layout.separator()
        #layout.operator("mcp.define_t_pose")
        #layout.operator("mcp.undefine_t_pose")
        layout.operator("mcp.load_t_pose")
        layout.operator("mcp.save_t_pose")
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
        layout.operator("mcp.set_all_fake_user")
        layout.operator("mcp.delete_action")
        layout.operator("mcp.delete_all_actions")
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
    MCP_PT_TPose,
    MCP_PT_Actions,

    utils.ErrorOperator,
    utils.MessageOperator
]

def register():
    bpy.types.Scene.McpVerbose = BoolProperty(
        name="Verbose",
        description="Verbose mode for debugging",
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

