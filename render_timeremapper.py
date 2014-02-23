# ##### BEGIN GPL LICENSE BLOCK #####''
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Time Remapper",
    "author": "Garrett",
    "version": (0, 0),
    "blender": (2, 70, 0),
    "location": "Properties > Render > Render Panel",
    "description": "Time remaps whole scene according to an animatable speed factor",
    "warning": "beta",
    "category": "Render",
    "wiki_url": "",
    "tracker_url": ""}
    
    
import bpy
import os
import signal

##TODO: figure out how to initialize the addon. 
#TODO: initialize fcurve using Pink Vertex answer here: http://blender.stackexchange.com/questions/7123/add-keyframe-to-a-scene-property
#and also fcurve.extrapolation='LINEAR'

def get_TR_frames_from_SF(context):
    '''Gets a list of time-remapped frames to be rendered by
    looking at the Speed Factor parameter.'''

    scene = context.scene
   
    #Time-remapped frames to render
    TR_frames=[]
    
    #current time-remapped frame
    current_TR_frame = scene.frame_start
    
    #we loop through however many (time-remapped) frames it takes 
    #to get to the end frame
    while current_TR_frame <= scene.frame_end:

        #jump to current frame
        scene.frame_set(current_TR_frame)              
        
        #add current frame to our list
        TR_frames.append( current_TR_frame )
        
        #avoid infinite loop by checing that speed factor's positive            
        if scene.timeremap_speedfactor <= 0.0:
            raise RuntimeError(
                    "\n\nYou're speed factor must always be positive" 
                    " to avoid getting stuck in an infinite loop!")
        
        #move to next frame based on the current value of the speed factor
        current_TR_frame += scene.timeremap_speedfactor  
    #end while loop
    
    return TR_frames    
#end of get_TR_frames_from_SF(.)


def get_TR_frames_from_TTC(context):
    '''Gets a list of time-remapped frames to be rendered by 
    looking at the Speed Factor parameter.'''
    pass
    scene = context.scene
    
    #Time-remapped frames to render
    TR_frames=[]
    #jump to non-time-remapped start frame
    nonTR_frame = scene.frame_start
    scene.frame_set(nonTR_frame)

    #to avoid getting stuck in an infinite loop (ex: TT curve never reaches the
    #end frame), we break after 100 000 frames.
    count=0

    #we loop through however many (time-remapped) frames 
    #it takes to get to the end frame
    while scene.timeremap_TTC <= scene.frame_end:
        
        TR_frames.append( scene.timeremap_TTC )
        
        #move to next frame. 
        #Note: this wil change scene.timeremap_TTC's value
        nonTR_frame += 1    
        scene.frame_set(nonTR_frame)
        
        count+=1
        if count>=100000:
            raise RuntimeError("\n\nHaven't reached end after counting 100 000" 
                                "frames!\nMake sure the TT Curve value reaches"
                                " the end frame at some point.")
    #end of while loop
    
    return TR_frames
#end of get_TR_frames_from_TTC(.)
        
    


class OBJECT_OT_render_TR(bpy.types.Operator):
    bl_idname='render.render_timeremapper'
    bl_label="Render using Time Remapper"
    bl_description= "This renders out frames based on your time remapping"
    bl_register = True
    
    #this is only used during rendering frames
    abort_render = bpy.props.BoolProperty(default=False)
    
    

    
    
    def SIGINT_handler(self, signum, frame):
        '''This signal handler will be called when user hits CTL+C
        while rendering'''
        self.abort_render = True
    
        
    
    def execute(self, context):
        
        scene = context.scene
        
        #ensure they are using Cycles. 
        #Comment this out if you want to try it with Blender Render...
        if scene.render.engine != 'CYCLES':
            raise RuntimeError("\n\nYou must be using Cycles Render "
                               "for this script to work properly.\n")
        #ensure they haven't selected a movie format
        if scene.render.is_movie_format:
            file_format = scene.render.image_settings.file_format
            raise RuntimeError("\n\nCannot render movie file, "
                                "you must select an image format"
                                "\n(Current file format: {})"
                                .format(file_format))
                        
        
        
        print("Getting list of frames to be rendered (should take < 1s)")
        if scene.timeremap_method == 'SF':
            TR_frames = get_TR_frames_from_SF(context)
        elif scene.timeremap_method == 'TTC':
            TR_frames = get_TR_frames_from_TTC(context)
        else:
            assert False
        
        
        #total number of frames
        total_num_fr = len(TR_frames)
        
        print("\n\nRendering " + str(total_num_fr) +\
                " frames now ... to stop after rendering current frame,"
                "press CTL+C...\n\n")
        
        
        
        #store original render path
        orig_render_path = scene.render.filepath
        
        #keep a count for labelling the filenames
        count=0
        
        first_frame = scene.frame_start

        #before starting loop, set up a signal handler for CTL+C
        #since KeyboardInterrupt doesn't work while rendering
        #(see bit.ly/1cfBmlS)
        self.abort_render=False
        signal.signal(signal.SIGINT, self.SIGINT_handler)
                
        #start loop that renders the frames. 
        #(anim_frame is the actual frame in animation we're at, ex: 4.5435)
        for anim_frame in TR_frames:
            
            print('-------------------')
        
            #check for frame step and skip frame if necessary
            if count % scene.frame_step != 0:
                print("Stepping over frame " +str(first_frame+count) + 
                        ". (Frame Step is " + str(scene.frame_step) +")" )
                count+=1
                continue
          
            
            #Jump to animation frame (frame is a float)
            scene.frame_set(int(anim_frame), anim_frame%1)
            #create filename.  Note that Blender expects a four digit integer at the end.
            if scene.timeremap_trueframelabels:
                current_renderpath = orig_render_path +\
                                    '{x:.2f}_'.format(x=anim_frame) +\
                                    str(first_frame+count).zfill(4)
            else:
                current_renderpath = orig_render_path + str(first_frame+count).zfill(4)
                
               
            #check if file exists, and if so whether we should overwrite it   
            #first we get the full current path to image to be rendered by 
            #adding the extension if File Extensions is enabled.
            full_current_renderpath = bpy.path.abspath(current_renderpath) + \
                                      scene.render.file_extension * \
                                      (scene.render.use_file_extension==True)
            if os.path.exists( full_current_renderpath ):
                if scene.render.use_overwrite == False:
                    print("Skipping frame " + str(first_frame+count) +
                            " because there already exists the file: " + 
                            full_current_renderpath )
                    count+=1
                    continue
                else:
                    print("File: " + full_current_renderpath + " will be overwritten.")
                    #Wait to overwrite it until last possible moment.
            
            
            #check if we need Placeholders
            if scene.render.use_placeholder == True:
                #delete the old file if it exists
                if os.path.exists( full_current_renderpath ):
                    os.remove( full_current_renderpath )
                #create placeholder  (tag 'a' helps prevent race errors)
                open(full_current_renderpath, 'a').close()
                    
            
            scene.render.filepath = current_renderpath
            print("Rendering true frame:",anim_frame)
            bpy.ops.render.render( write_still=True )
            print("Finished frame: " + str(count+1) + "/" + str(total_num_fr) + "\n\n")
            count+=1
            #Check if CTL+C was pressed by user
            if self.abort_render == True:
                print("\nAborting Animation")
                #reset the SIGINT handler back to default
                signal.signal( signal.SIGINT, signal.default_int_handler)
                break
        
        #End loop that renders frames
         
         
            
        #reset the filepath in case user wants to play movie afterwards
        scene.render.filepath = orig_render_path
        
        print("\n\nDone")
        
        return {'FINISHED'}
        
    #end of execute(.)
#end of class OBJECT_OT_render_TR


class OBJECT_OT_playback_TR(bpy.types.Operator):
    bl_idname='render.playback_timeremapper'
    bl_label="Playback time remapped frames"
    bl_description= "Plays back frames, defining the start and end"\
                        " based on the time remapping"
    bl_register = True

    def execute(self, context):
        print("You're inside the execute playback")

        scene = context.scene        
        
        #get number of frames that we need to play back
        if scene.timeremap_method == 'SF':
            num_frames = len( get_TR_frames_from_SF(context) )
        elif scene.timeremap_method == 'TTC':
            num_frames = len( get_TR_frames_from_TTC(context) )
        else:
            assert False        
        
        old_frame_end = scene.frame_end
        
        scene.frame_end = scene.frame_start + num_frames -1
        
        bpy.ops.render.play_rendered_anim()

        #restore the old end frame
        scene.frame_end = old_frame_end
        
        return {'FINISHED'}
    
    @classmethod
    def poll(cls, context):
        return not context.scene.timeremap_trueframelabels
        


def draw(self, context):
    layout = self.layout

    scene = context.scene

    layout.label("Time Remapper:")    
    
    row = layout.row(align=True)
    row.alignment = 'LEFT'
    row.prop(scene, 'timeremap_method')
    if scene.timeremap_method == 'SF':
        row.prop(scene, 'timeremap_speedfactor')
    elif scene.timeremap_method == 'TTC':
        row.prop(scene, 'timeremap_TTC')
    
    row = layout.row(align=True)
    rowsub = row.row(align=True)
    rowsub.operator('render.render_timeremapper', 
                    text="TR Animation", 
                    icon="RENDER_ANIMATION")        
    rowsub.operator('render.playback_timeremapper', 
                    text="TR Playback", 
                    icon='PLAY')
    rowsub.prop(scene, 'timeremap_trueframelabels')
     
     
def is_keyframed(scene, prop):
    '''Check if the scene property is already keyframed
    Ideas from @CoDEmanX on Blender SE for this.'''

    anim = scene.animation_data    
    
    if anim is not None and anim.action is not None:
        for fcu in anim.action.fcurves:
            if fcu.data_path == prop:
                return True
    return False
        
    

def update_TR_method(self, context):
    '''Check if user switched to using a TT curve.  If so, and it is not 
    keyframed, then keyframe it to produce a 45 degree angle curve (which 
    corresponds to a one-to-one time mapping)
    
    Ideas from @pinkvertex on Blender SE.'''

    scene = context.scene   
    
    print('Inside update method')
    
    #if not switching to TT curve, or if it's already keyframed, return
    if scene.timeremap_method != 'TTC' or is_keyframed(scene, 'timeremap_TTC'):
        print('OK no need')
        return
    
    if not scene.animation_data:
        scene.animation_data_create()
    if not scene.animation_data.action:
        scene.animation_data.action = bpy.data.actions.new('timeremap_TTC_action')
    
 
    #find the correct f-curve in case there's multiple        
    fcurve = scene.animation_data.action.fcurves.new('timeremap_TTC')    
    
    
    #keyframe it to make a 45 degree straight line
    fcurve.keyframe_points.insert( frame=0.0, value=0.0 )
    fcurve.keyframe_points.insert( frame=1.0, value=1.0 )    
    fcurve.extrapolation='LINEAR' 
    #now because of a possible bug, I have to use this workaround
    refresh_fcurve_editor()


def refresh_fcurve_editor():
    '''execute a meaningless command on F-Curve Editor which has the effect of
    refreshing the graph.  I think it's a bug that necessitates using this.
    see: bit.ly/1hGAT0I'''
    C=bpy.context
    old_area_type = C.area.type
    C.area.type='GRAPH_EDITOR'
    bpy.ops.graph.clean( threshold = 0)
    C.area.type=old_area_type    
    

    
def register():
    bpy.utils.register_module(__name__)
    
    bpy.types.Scene.timeremap_speedfactor = bpy.props.FloatProperty(
                    name="Speed factor", 
                    options={'ANIMATABLE'},
                    default=1.0)
    bpy.types.Scene.timeremap_TTC = bpy.props.FloatProperty(
                    name="TT Curve",
                    options={'ANIMATABLE'},
                    default=0.0)
    bpy.types.Scene.timeremap_trueframelabels = bpy.props.BoolProperty(
                    name="Frame labels", 
                    description="Include true frames in filenames"
                                " (Ex: '23.42_0025.png')  "
                                "Enabling this precludes the use of Playback",
                    default=False)
    bpy.types.Scene.timeremap_method = bpy.props.EnumProperty(
                    name="",
                    description="Method for defining the time remapping",
                    items=[
                            ('SF','Speed Factor','Use a speed factor (where 0.5 means 2x slow-mo)'),
                           ('TTC', 'Time-Time Curve', 
                           'Use a curve which shows how rendered frame maps to true-time frame')
                           ],
                    default='SF', update=update_TR_method)

    #Draw the panel under the header "Render" in Render tab of Properties window    
    bpy.types.RENDER_PT_render.append(draw)

    
def unregister():    
    
    del bpy.types.Scene.timeremap_speedfactor    
    del bpy.types.Scene.timeremap_TTC
    del bpy.types.Scene.timeremap_trueframelabels
    del bpy.types.Scene.timeremap_method
    
    #remove the panel from the UI
    bpy.types.RENDER_PT_bake.remove(draw)
    
    bpy.utils.unregister_module(__name__)



if __name__ == "__main__":
    register()