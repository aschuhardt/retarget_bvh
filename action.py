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
from bpy.props import EnumProperty, StringProperty

from . import utils
from .utils import *

#
#   Global variables
#

_actions = []

class ActionList:
    useFilter : BoolProperty(
        name="Filter",
        description="Filter action names",
        default=False)

    def draw(self, context):
        self.layout.prop(self, "useFilter")
        self.layout.separator()
        self.layout.prop_menu_enum(context.scene, "McpActions")


    def invoke(self, context, event):
        self.listAllActions(context)
        return BvhPropsOperator.invoke(self, context, event)
        

    def getAction(self, context):        
        self.listAllActions(context)
        aname = context.scene.McpActions
        try:
            return bpy.data.actions[aname]
        except KeyError:
            pass
        raise MocapError("Did not find action %s" % aname)

    
    def listAllActions(self, context):
        global _actions
    
        scn = context.scene
        try:
            doFilter = self.useFilter
            filter = context.object.name
            if len(filter) > 4:
                filter = filter[0:4]
                flen = 4
            else:
                flen = len(filter)
        except:
            doFilter = False

        _actions = []
        for act in bpy.data.actions:
            name = act.name
            if (not doFilter) or (name[0:flen] == filter):
                _actions.append((name, name, name))
        bpy.types.Scene.McpActions = EnumProperty(
            items = _actions,
            name = "Actions")
        print("Actions declared")
        return _actions

#
#   class MCP_OT_UpdateActionList(BvhOperator):
#

class MCP_OT_UpdateActionList(BvhPropsOperator, IsArmature, ActionList):
    bl_idname = "mcp.update_action_list"
    bl_label = "Update Action List"
    bl_description = "Update the action list"
    bl_options = {'UNDO'}

    def run(self, context):
        self.listAllActions(context)

#
#   class MCP_OT_DeleteAction(BvhOperator):
#

class MCP_OT_DeleteAction(BvhPropsOperator, IsArmature, ActionList):
    bl_idname = "mcp.delete_action"
    bl_label = "Delete Action"
    bl_description = "Delete the action selected in the action list"
    bl_options = {'UNDO'}

    reallyDelete : BoolProperty(
        name="Really Delete Action",
        description="Delete button deletes action permanently",
        default=False)

    def draw(self, context):
        ActionList.draw(self, context)
        self.layout.prop(self, "reallyDelete")


    def run(self, context):
        global _actions
        act = self.getAction(context)        
        print('Delete action', act)
        act.use_fake_user = False
        if act.users == 0:
            print("Deleting", act)
            n = self.findActionNumber(act.name)
            _actions.pop(n)
            bpy.data.actions.remove(act)
            print('Action', act, 'deleted')
            self.listAllActions(context)
            #del act
        else:
            raise MocapError("Cannot delete. Action %s has %d users." % (act.name, act.users))


    def findActionNumber(self, name):
        global _actions
        for n,enum in enumerate(_actions):
            (name1, name2, name3) = enum
            if name == name1:
                return n
        raise MocapError("Unrecognized action %s" % name)

#
#   class MCP_OT_DeleteHash(BvhOperator):
#

def deleteAction(act):
    act.use_fake_user = False
    if act.users == 0:
        bpy.data.actions.remove(act)
    else:
        print("%s has %d users" % (act, act.users))


class MCP_OT_DeleteHash(BvhOperator):
    bl_idname = "mcp.delete_hash"
    bl_label = "Delete Temporary Actions"
    bl_description = (
        "Delete all actions whose name start with '#'. " +
        "Such actions are created temporarily by BVH Retargeter. " +
        "They should be deleted automatically but may be left over."
    )
    bl_options = {'UNDO'}

    def run(self, context):
        for act in bpy.data.actions:
            if act.name[0] == '#':
                deleteAction(act)

#
#   class MCP_OT_SetCurrentAction(BvhOperator):
#

class MCP_OT_SetCurrentAction(BvhOperator, IsArmature, ActionList):
    bl_idname = "mcp.set_current_action"
    bl_label = "Set Current Action"
    bl_description = "Set the action selected in the action list as the current action"
    bl_options = {'UNDO'}

    def run(self, context):
        act = self.getAction(context)        
        context.object.animation_data.action = act
        print("Action set to %s" % act)

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MCP_OT_UpdateActionList,
    MCP_OT_DeleteAction,
    MCP_OT_DeleteHash,
    MCP_OT_SetCurrentAction,
]

def initialize():
    for cls in classes:
        bpy.utils.register_class(cls)


def uninitialize():
    for cls in classes:
        bpy.utils.unregister_class(cls)
