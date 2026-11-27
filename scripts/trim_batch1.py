#!/usr/bin/env python3
"""Batch surgical fixes: finish trimming removed backends for the Mac port."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / 'mocap'
changed = []

def edit(name, pairs, regex=None):
    p = M / name
    t = p.read_text(encoding='utf-8')
    orig = t
    for old, new in pairs:
        if old not in t:
            print(f'MISS {name}: {old[:70]!r}')
        t = t.replace(old, new)
    if regex:
        for pat, rep in regex:
            t = re.sub(pat, rep, t, flags=re.M)
    if t != orig:
        p.write_text(t, encoding='utf-8')
        changed.append(name)
        print(f'OK   {name}')

# ---------------- models.py: remove optional model catalog imports ----------------
t = (M / 'models.py').read_text(encoding='utf-8')
for pat in [r'^from \.mamma_models import.*\n', r'^from \.prompthmr_models import.*\n',
            r'^from \.pear_models import.*\n', r'^from \.gemx_models import.*\n',
            r'^MODELS_LIST\.extend\(Model\(\*\*entry\) for entry in (MAMMA|PEAR|PHMR|GEMX)_ASSETS\)\n']:
    t = re.sub(pat, '', t, flags=re.M)
# GEMX/MAMMA/PHMR key tuples in STAGE_REQUIREMENTS -> empty tuples
t = re.sub(r'^GEMX_KEYS\s*=.*$', 'GEMX_KEYS = ()', t, flags=re.M)
t = re.sub(r'^MAMMA_KEYS\s*=.*$', 'MAMMA_KEYS = ()', t, flags=re.M)
t = re.sub(r'^PHMR_KEYS\s*=.*$', 'PHMR_KEYS = ()', t, flags=re.M)
t = re.sub(r'^PHMR_CAMERA_KEYS\s*=.*$', 'PHMR_CAMERA_KEYS = ()', t, flags=re.M)
# runtime receipt checks for removed families -> always valid
t = t.replace("model.key.startswith(('flow','hand','exmr','mamma','phmr','pear','gemx','sam31','rife')) or model.key in ('smplh','mano_right')",
              "model.key.startswith(('hand','rife')) or model.key in ()")
(M / 'models.py').write_text(t, encoding='utf-8')
print('OK   models.py')

# ---------------- motion_tools.py: GVHMR-only ----------------
t = (M / 'motion_tools.py').read_text(encoding='utf-8')
t = t.replace('MOTION_TOOLS = {"pear": MotionTool("pear", "PEAR · Live (Experimental)", (), live=True),"gvhmr": MotionTool("gvhmr", "GVHMR", ("track", "gvhmr"), ("pva", "refine")),\n                "flowhmr": MotionTool("flowhmr", "FlowHMR", ("track", "flow_camera", "flow_features", "flowhmr")),\n                "exmr": MotionTool("exmr", "ExMR", ("track", "exmr_preprocess", "exmr_features", "exmr")),\n                "mamma": MotionTool("mamma", "MAMMA", ("mamma_prepare","mamma_masks","mamma_landmarks","mamma_camera","mamma_fit","mamma_publish")),\n                "prompthmr": MotionTool("prompthmr", "PromptHMR", ("prompthmr_prepare","prompthmr_track","prompthmr_pose","prompthmr_world","prompthmr_publish")),\n                "gemx": MotionTool("gemx", "GEM-X", ("gemx_reconstruct",))}',
              'MOTION_TOOLS = {"gvhmr": MotionTool("gvhmr", "GVHMR", ("track", "gvhmr"), ("pva", "refine"))}')
(M / 'motion_tools.py').write_text(t, encoding='utf-8')
print('OK   motion_tools.py (catalog)')

# fix remaining helper imports in motion_tools
edit('motion_tools.py', [
    ("        from .gemx_result import current\n", "        current = None\n"),
    ("        from .gemx_correct import KIND, selected\n", "        KIND, selected = None, None\n"),
    ("    from .flow_placement import current as placement_current\n", "    placement_current = None\n"),
    ("    from .gemx_result import RECEIPT, is_project\n", "    RECEIPT, is_project = None, (lambda project: False)\n"),
    ("        from .gemx_correct import RECORD\n", "        RECORD = None\n"),
])

# ---------------- local_choices.py ----------------
edit('local_choices.py', [
    ("DEFAULT_MODEL = 'exmr'", "DEFAULT_MODEL = 'gvhmr'"),
    ("OPTIONAL_RUNTIMES = ('mamma', 'prompthmr', 'gemx')", "OPTIONAL_RUNTIMES = ()"),
])

# ---------------- worker.py: GVHMR-only stages ----------------
edit('worker.py', [
    ('parser.add_argument("stage", choices=["diagnose", "prepare", "download", "import_model", "mesh", "rig", "save_fbx", "track", "pva", "features", "gvhmr", "refine", "footmr", "handflow", "correct", "export", "people", "person", \'flow_camera\',\'flow_features\',\'flowhmr\',\'flow_export\',\'exmr_preprocess\',\'exmr_features\',\'exmr\'])',
     'parser.add_argument("stage", choices=["diagnose", "prepare", "download", "import_model", "mesh", "rig", "save_fbx", "track", "pva", "features", "gvhmr", "refine", "footmr", "handflow", "correct", "export", "people", "person"])'),
    ("            if args.motion_tool=='flowhmr':\n", "            if False:\n"),
    ("            if args.motion_tool=='exmr':\n                from .exmr_options import options\n                manifest['exmr_options']=options(json.loads(os.environ.get('RGB_MOCAP_EXMR_OPTIONS','{}')))\n", ""),
    ("        if require_supported_project(project).key=='exmr' and args.stage not in ('exmr_preprocess','exmr_features','exmr','people','person','track','rig','mesh','export','correct'):\n            raise ValueError('This stage is not compatible with ExMR. Its original prediction has been preserved.')\n        if require_supported_project(project).key=='exmr' and args.stage.startswith('exmr'):\n            from .exmr_backend import run_stage\n            run_stage(project,args.stage,args.result,emit,force=args.force)\n            return 0\n        if require_supported_project(project).key=='flowhmr' and args.stage not in ('people','person','track'):\n            from .flow_backend import run_stage\n            run_stage(project,args.stage,args.result,emit,force=args.force)\n            return 0\n        if require_supported_project(project).key in ('mamma','prompthmr'):\n            if args.stage=='export':\n                from .export import export_project\n                output=export_project(project,args.result)\n            elif args.stage=='correct':\n                from .correction import run as correct_mamma\n                correct_mamma(project,emit,args.result);output=project/RESULTS[args.result][0]\n            elif args.stage in ('mesh','rig'):\n                from .export import export_project\n                output=export_project(project,args.result)\n            else:raise ValueError('Use this model\\'s dedicated reconstruction pipeline; generic inference stages cannot process this project.')\n            emit('complete',stage=args.stage,output=str(output),cached=False,elapsed=time.monotonic()-started)\n            return 0\n", ""),
    ("                finger_motion='ExMR native finger inference' if require_supported_project(project).key=='exmr' else 'HandFlow finger inference; body and wrists preserved' if has_handflow(kind) else 'Source relaxed pose animated relative to open bind; finger inference is not enabled'",
     "                finger_motion='HandFlow finger inference; body and wrists preserved' if has_handflow(kind) else 'Source relaxed pose animated relative to open bind; finger inference is not enabled'"),
])

# ---------------- worker_progress.py: GVHMR-only dispatch ----------------
edit('worker_progress.py', [
    ("    if stage in {'people','person','track','pva','features','gvhmr','refine','footmr','handflow','rig','mesh','export','correct'} and '--project' in sys.argv:\n        from .gemx_result import is_project\n        if is_project(sys.argv[sys.argv.index('--project')+1]):\n            emit('failed',stage=stage,message='This operation requires a SMPL result. GEM-X uses native SOMA.')\n            return 1\n", ""),
    ("    if stage in ('save_blend','save_blend_scene'):", "    if stage in ('save_blend',):"),
    ("    if stage=='flow_mamma_gravity':\n        from .mamma_gravity_worker import main as gravity_main\n        return gravity_main()\n", ""),
    ("    if stage=='pear_camera_preview':\n        from .pear.camera_preview import main as camera_main\n        return camera_main()\n", ""),
    ("    if stage=='flow_pear_align':\n        from .pear.align_worker import main as align_main\n        return align_main()\n", ""),
    ("    if stage=='pear_live':\n        from .pear.worker import main as live_main\n        return live_main()\n", ""),
    ("    if stage in ('prompthmr_prepare','prompthmr_publish'):\n        from .compute_policy import configure_worker_cpu\n        configure_worker_cpu(stage)\n        from .prompthmr_pipeline import main as phmr_main\n        return phmr_main(sys.argv[1:])\n", ""),
    ("    if stage in ('flow_batch','exmr_batch','gvhmr_batch'):", "    if stage in ('gvhmr_batch',):"),
    ("    if stage in ('mamma_prepare','mamma_publish'):\n        from .compute_policy import configure_worker_cpu\n        configure_worker_cpu(stage)\n        from .mamma_pipeline import main as mamma_main\n        return mamma_main(sys.argv[1:])\n", ""),
    ("    if stage == 'gemx_contact_solve':\n        from .gemx_contact_solver import main as solve\n        return solve(sys.argv[2:], emit)\n", ""),
    ("    if stage.startswith('exmr') or stage=='download':", "    if stage=='download':"),
])

# ---------------- paths.py ----------------
edit('paths.py', [
    ("    if stage == 'face_track':\n        from .face_runtime import command as face_command\n        return face_command(args)\n    if stage == 'sam31_people':\n        from .sam31_runtime import command as sam31_command\n        return sam31_command(args)\n    if stage in ('gemx_reconstruct', 'gemx_correct'):\n        from .gemx_runtime import command as gemx_command\n        return gemx_command(stage, args)\n    if stage.startswith('prompthmr_') and stage not in ('prompthmr_prepare','prompthmr_publish'):\n        from .prompthmr_runtime import command as phmr_command\n        return phmr_command(stage,args)\n    if stage.startswith('mamma_') and stage not in ('mamma_prepare','mamma_publish'):\n        from .mamma_runtime import command as mamma_command\n        return mamma_command(stage,args)\n", ""),
])

# ---------------- model_manager.py ----------------
edit('model_manager.py', [
    ("    from .flow_hamer import MODEL_KEYS\n    from .sam31_runtime import SUPPORTED\n\n", "    MODEL_KEYS = ()\n    SUPPORTED = ()\n\n"),
    ("    from .exmr_backend import LINKS as exmr_links\n    from .flow_backend import ASSET_LINKS\n    from .prompthmr_models import CAMERA_LINKS, LINKS as prompt_links\n\n", "    exmr_links = {}\n    ASSET_LINKS = {}\n    CAMERA_LINKS, prompt_links = {}, {}\n\n"),
    ("    from .pear_models import geometry_folder, spec\n", "    def geometry_folder(*_a, **_k):\n        return None\n    spec = lambda *_a, **_k: {'files': []}\n"),
    ("        from .pear_models import spec\n", "        spec = lambda *_a, **_k: {'files': []}\n"),
])

# models.py helper imports
edit('models.py', [
    ("        from .pear_models import geometry_ready\n", "        geometry_ready = lambda: False\n"),
    ("        from .gemx_models import download_model\n", "        raise ValueError('Optional model downloads are not available in this build.')\n        download_model = None\n"),
    ("        from .pear_models import import_bundle\n", "        raise ValueError('PEAR asset import is not available in this build.')\n        import_bundle = None\n"),
])

# ---------------- export chain: gemx/ue5 branches ----------------
edit('export.py', [
    ('    mamma=json.loads((project/"project.json").read_text(encoding="utf-8")).get("pipeline",{}).get("model")=="mamma"\n    if not mamma:\n        root = activate("GVHMR")\n        link_models(root)\n    import torch\n    if not mamma:\n        from hmr4d.utils.smplx_utils import make_smplx\n',
     '    root = activate("GVHMR")\n    link_models(root)\n    import torch\n    from hmr4d.utils.smplx_utils import make_smplx\n'),
    ('    from .mamma_body import body_path,model_for\n    registered_body=body_path(project)\n    model_stamp=file_stat(registered_body)\n    body = model_for(project) if mamma else make_smplx("supermotion").eval()',
     '    from .mamma_body import body_path\n    registered_body=body_path(project)\n    model_stamp=file_stat(registered_body)\n    body = make_smplx("supermotion").eval()'),
    ('    exmr=state.get(\'pipeline\',{}).get(\'model\')==\'exmr\'\n    if exmr:label=\'ExMR original\'\n    if mamma:label=\'MAMMA original\'\n    if state.get(\'pipeline\',{}).get(\'model\')==\'prompthmr\':label=\'PromptHMR original\'',
     '    label=\'GVHMR original\''),
    ('        "skeleton":"Humanoid52", "finger_motion":"MAMMA fitted body and finger motion" if mamma else "ExMR native finger inference" if exmr else "HandFlow finger inference; body and wrists preserved" if has_handflow(result) else "Source relaxed pose animated relative to open bind; finger inference is not enabled"',
     '        "skeleton":"Humanoid52", "finger_motion":"HandFlow finger inference; body and wrists preserved" if has_handflow(result) else "Source relaxed pose animated relative to open bind; finger inference is not enabled"'),
])
# also fix the leftover `if not mamma:` blocks in export.py (activate/link guarded)
t = (M / 'export.py').read_text(encoding='utf-8')
t = t.replace('    if not mamma:\n        from hmr4d.utils.smplx_utils import make_smplx\n', '    from hmr4d.utils.smplx_utils import make_smplx\n')
(M / 'export.py').write_text(t, encoding='utf-8')

edit('blend_export.py', [
    ("    from .gemx_result import is_project\n\n", "    is_project = lambda project: False\n\n"),
    ("                raise ValueError('Export one native SOMA result at a time.')\n            from .gemx_blend import run as native_export\n            return native_export(rows[0], request, emit)\n",
     ""),
])
t = (M / 'blend_export.py').read_text(encoding='utf-8')
t = re.sub(r'    if rows and is_project\(rows\[0\]\[\'project\'\]\):\n', '    if False:\n', t)
(M / 'blend_export.py').write_text(t, encoding='utf-8')

edit('export_copy.py', [
    ("from .gemx_result import is_project", "is_project = lambda project: False"),
    ("            if is_project(project):\n                from .gemx_skeleton_export import write as write_soma\n\n                def progress(done,total):\n                    emit('progress',stage='copy_bvh',current=i*total+done,total=len(rows)*total,message='Export SOMA BVH')\n",
     ""),
])
edit('fbx_export.py', [
    ("    from .gemx_result import is_project", "    is_project = lambda project: False"),
    ("            if is_project(project):\n                from .gemx_skeleton_export import write as write_soma\n\n                def progress(done,total):\n                    emit('progress',stage='save_fbx',current=i*total+done,total=len(rows)*total,message='Export SOMA FBX')\n",
     ""),
])
edit('character_ui.py', [
    ("        from .gemx_result import RECEIPT, is_project\n", "        RECEIPT, is_project = None, (lambda project: False)\n"),
    ("                from .gemx_result import is_project\n                if not is_project(job['takes'][0]['project']):\n                    args+=['--project',job['takes'][0]['project']]\n", "                args+=['--project',job['takes'][0]['project']]\n"),
])
edit('take_selection.py', [
    ("    from .gemx_result import is_project\n", "    is_project = lambda project: False\n"),
    ("        from .flow_placement import needs_update\n", "        needs_update = lambda project: False\n"),
])
edit('preview_data.py', [
    ("                from .gemx_result import is_project, open_preview\n", "                is_project = lambda project: False\n                open_preview = None\n"),
])
edit('result_artifacts.py', [
    ("    from .gemx_result import is_project\n", "    is_project = lambda project: False\n"),
])
edit('project_save.py', [
    ("        from .mamma_inputs import resolved_entries\n", "        resolved_entries = lambda *a, **k: []\n"),
])
edit('project_workspace_ui.py', [
    ("from .exmr_options import DEFAULTS as EXMR_DEFAULTS", "EXMR_DEFAULTS = {'static_camera': True, 'smoothing': 'none', 'refine_camera_rotation': False}"),
    ("        from .prompthmr_pipeline import options as prompthmr_options\n", "        prompthmr_options = lambda *a, **k: {}\n"),
])
edit('scene_camera.py', [
    ("        from .prompthmr_scene import prepare_cameras as prepare_phmr\n", "        prepare_phmr = None\n"),
    ("        from .mamma_scene import prepare_cameras as prepare_mamma\n", "        prepare_mamma = None\n"),
    ("        from .flow_scene import prepare_cameras as prepare_flow\n", "        prepare_flow = None\n"),
])
edit('scene_data.py', [
    ("            from .flow_scene import load_scene\n", "            load_scene = None\n"),
])
edit('scene_floor.py', [
    ("        from .flow_floor import resolve\n", "        resolve = None\n"),
])
edit('viewport.py', [
    ("            from .pear.live_view import LiveRenderer\n", "            LiveRenderer = None\n"),
])
edit('source_export_dialog.py', [
    ("from .face_export_ui import FaceExportControls\n", "class FaceExportControls:\n    def __init__(self, *_a, **_k): pass\n    def controls(self): return {}\n    def options(self): return {}\n"),
])
edit('character_export_dialog.py', [
    ("from .face_export_ui import FaceExportControls\n", "class FaceExportControls:\n    def __init__(self, *_a, **_k): pass\n    def controls(self): return {}\n    def options(self): return {}\n"),
])
edit('source_export_worker.py', [
    ("    from .face_export import plan, publish\n", "    plan = lambda *a, **k: []\n    publish = lambda *a, **k: None\n"),
    ("    sidecars=plan(args.output,stage)\n", ""),
    ("    publish(sidecars,emit)\n", ""),
])
edit('stream_ui.py', [
    ("from .unreal_stream import UnrealStream, subject_name\n", "from .bone_stream import Y_TO_Z\nUnrealStream = None\ndef subject_name(name):\n    return name\n"),
    ("        from .unreal_stream import rig_schema\n", "        from .bone_stream import rig_schema\n"),
    ("        from .face_data import manifest\n", "        manifest = None\n"),
])
print()
print('Changed:', *changed, sep='\n  ')
