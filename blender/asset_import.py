bl_info = {
    "name": "SfA: Asset Linking",
    "author": "dr. Sybren <sybren@blender.org>",
    "version": (1, 0),
    "blender": (2, 83, 0),
    "category": "Import",
    "location": "File > Import",
    "description": "Link assets from a JSON file into the scene.",
    "warning": "",
    "doc_url": "https://cloud.blender.org/p/scripting-for-artists",
    "tracker_url": "",
}
import bpy
import csv
import sys
import openpyxl  # Import the openpyxl library



def link_to_scene(
    filepath: str,
    prefix: str,
    link_to: bpy.types.Collection,
    location_y: float,
):
    # Link into the blend file
    with bpy.data.libraries.load(filepath, link=True) as (data_from, data_to):
        for name in data_from.collections:
            if not name.startswith(prefix):
                continue
            data_to.collections.append(name)

    # Instance into the scene
    location_x = 0
    step_x = 2.0
    for coll in data_to.collections:
        if coll.name in link_to.objects:
            continue
        empty = bpy.data.objects.new(coll.name, None)
        empty.instance_type = 'COLLECTION'
        empty.instance_collection = coll
        link_to.objects.link(empty)

        empty.location.x = location_x
        empty.location.y = location_y
        location_x += step_x


def ensure_collection(scene, collection_name) -> bpy.types.Collection:
    try:
        link_to = scene.collection.children[collection_name]
    except KeyError:
        link_to = bpy.data.collections.new(collection_name)
        scene.collection.children.link(link_to)
    return link_to


class IMPORT_SCENE_OT_from_json(bpy.types.Operator):
    bl_idname = 'import_scene.from_json'
    bl_label = "Link assets from JSON file"

    def execute(self, context):
        json_fname = bpy.path.abspath('//assets.json')
        with open(json_fname) as infile:
            link_info = json.load(infile)

        location_y = 0
        step_y = 2.0
        json_colls = link_info['collections']
        for coll_name, coll_info in json_colls.items():
            link_to = ensure_collection(context, coll_name)

            for file_and_prefix in coll_info['link']:
                filepath = file_and_prefix['file']
                prefix = file_and_prefix['prefix']
                link_to_scene(filepath, prefix, link_to, location_y)

                location_y += step_y

        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(IMPORT_SCENE_OT_from_json.bl_idname)


blender_classes = [
    IMPORT_SCENE_OT_from_json,
]

def register():
    for blender_class in blender_classes:
        bpy.utils.register_class(blender_class)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    for blender_class in blender_classes:
        bpy.utils.unregister_class(blender_class)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)