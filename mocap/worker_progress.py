"""Presentation-only worker entry; inference/cache identities stay unchanged."""
import json,runpy,sys
from contextlib import contextmanager,nullcontext

for stream in (sys.stdout,sys.stderr):
    if hasattr(stream,'reconfigure'):
        stream.reconfigure(encoding='utf-8',errors='backslashreplace')


def emit(kind,**value):
    print('@@MOCAP@@'+json.dumps(dict(type=kind,**value)),flush=True)


@contextmanager
def download_progress(callback):
    """Preserve the downloader signature, including recursive metadata calls."""
    from . import models
    original=models.download
    def wrapped(key,progress=None):
        return original(key,progress=callback if progress is None else progress)
    try:
        models.download=wrapped
        yield
    finally:models.download=original


def main():
    stage=sys.argv[1] if len(sys.argv)>1 else ''
    if sys.platform=='darwin':
        from . import mps_compat
        mps_compat.install()
    if stage in ('save_blend',):
        from .blend_export_worker import main as save_main
        return save_main(emit)
    if stage=='stream_reference':
        from .stream_reference import main as reference_main
        return reference_main(emit)
    if stage=='camera_background':
        from .camera_background_worker import main as camera_main
        return camera_main()
    if stage=='camera_reference':
        from .camera_reference import main as camera_main
        return camera_main()
    if stage in ('copy_bvh','save_fbx'):
        from .source_export_worker import main as save_main
        return save_main(emit)
    if stage in ('gvhmr_batch',):
        from .batch_worker import main as batch_main
        from .progress_events import tqdm_events
        with tqdm_events(emit):return batch_main(sys.argv[1:],emit)
    if stage=='character':
        from .retarget.worker import main as character_main
        return character_main(sys.argv[2:])
    if stage=='save_project':
        from .project_save import main as save_main
        sys.argv.pop(1)
        return save_main(emit)
    if stage=='download':
        from .progress_events import tqdm_events
        with tqdm_events(emit), (download_progress(emit) if stage=='download' else nullcontext()):
            runpy.run_module('mocap.worker',run_name='__main__')
    else:runpy.run_module('mocap.worker',run_name='__main__')


if __name__=='__main__':raise SystemExit(main())
