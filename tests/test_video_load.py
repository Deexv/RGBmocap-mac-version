"""Regression tests for the video-load path after the macOS trim.

Drag-and-drop calls MainWindow.load_video. It and the default-settings,
project-save paths used to touch FlowHMR/ExMR/MAMMA/PromptHMR/face widgets that
no longer exist and crashed with AttributeError ('flow_hamer' and friends).
"""
import os
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QMessageBox

from mocap import local_choices
from mocap.gui import MainWindow
from mocap.resource_safety import path as settings_file
from mocap.storage import atomic_json


def make_clip():
    """A tiny valid MP4 generated with ffmpeg when available, else None."""
    if not shutil.which('ffmpeg'):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        clip = Path(tmp) / 'clip.mp4'
        subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i',
                        'testsrc2=duration=1:size=160x120:rate=10',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(clip)],
                       capture_output=True, timeout=60)
        if not clip.is_file():
            return None
        target = Path(tempfile.gettempdir()) / 'rgbmocap-regression-clip.mp4'
        target.write_bytes(clip.read_bytes())
        return target


class VideoLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # Error dialogs are modal and would block an offscreen test run.
        cls.warn = QMessageBox.warning
        QMessageBox.warning = staticmethod(lambda *a, **k: None)
        cls.clip = make_clip()

    @classmethod
    def tearDownClass(cls):
        QMessageBox.warning = cls.warn

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name).resolve() / 'home'
        self.home.mkdir()
        patcher = patch.dict(os.environ, {'RGB_MOCAP_DATA': str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def window(self):
        w = MainWindow()
        self.addCleanup(w.shutdown_preview)
        self.addCleanup(w.close)
        return w

    def test_window_builds(self):
        w = self.window()
        self.assertFalse(getattr(w, '_pear_active', True))
        self.assertEqual([w.model_choice.itemData(i) for i in range(w.model_choice.count())], ['gvhmr'])

    def test_load_video_without_saved_defaults(self):
        """The reported crash: dropping a video with no saved defaults."""
        w = self.window()
        w.load_video(Path('/nonexistent-clip.mp4'))
        self.assertFalse(w.busy)

    def test_load_video_with_real_clip(self):
        if self.clip is None:
            self.skipTest('ffmpeg unavailable')
        w = self.window()
        w.load_video(self.clip)
        self.assertEqual(w.video_path, self.clip)

    def test_saved_defaults_apply_on_load(self):
        """A defaults file in the trimmed schema must apply cleanly."""
        w = self.window()
        atomic_json(settings_file(), {'default_settings': {
            'gvhmr_options': {'htd': True, 'footmr': True, 'handflow': True},
            'correction': {'mode': 'flat', 'preset': 'normal', 'foot_lock': True, 'hand_lock': False},
            'processing_options': {'resource_mode': 'low_memory'}}})
        w.load_video(Path('/nonexistent-clip.mp4'))
        self.assertEqual(w.compute_mode.currentData(), 'low_memory')

    def test_legacy_saved_defaults_with_removed_groups(self):
        """Defaults saved by the full build (flow/exmr/mamma keys) must not crash the trim."""
        w = self.window()
        atomic_json(settings_file(), {'default_settings': {
            'gvhmr_options': {'htd': True, 'footmr': False, 'handflow': True},
            'flow_options': {'camera_interval': 5, 'fast_sam': True, 'hamer': True},
            'exmr_options': {'static_camera': False, 'smoothing': 'global'},
            'prompthmr_options': {'camera': 'static'},
            'correction': {'mode': 'multi', 'preset': 'strong', 'foot_lock': True, 'hand_lock': True},
            'track_face': True,
            'processing_options': {'resource_mode': 'auto'}}})
        w.load_video(Path('/nonexistent-clip.mp4'))
        self.assertFalse(w.footmr_refine.isChecked())  # gvhmr_options still applied

    def test_save_and_reset_default_settings_data(self):
        """The menu actions must build their confirmation data without removed widgets."""
        from mocap.project_workspace_ui import DEFAULT_SETTINGS
        w = self.window()
        w._selected_tool = 'gvhmr'
        settings = w.workspace_settings()
        settings['gvhmr_options'] = dict(htd=True, footmr=True, handflow=True)
        settings['processing_options'] = {'resource_mode': w.compute_mode.currentData()}
        value = {group: {key: settings[group][key] for key in fields}
                 for group, (_, fields) in DEFAULT_SETTINGS.items()}
        self.assertEqual(set(value), {'gvhmr_options', 'correction', 'processing_options'})

    def test_workspace_settings_round_trip(self):
        w = self.window()
        w._selected_tool = 'gvhmr'
        settings = w.workspace_settings()
        self.assertIn('correction', settings)
        w.restore_workspace_settings(settings)
        self.assertEqual(w.selected_result(), settings['result'])

    def test_project_save_payload_has_no_removed_widgets(self):
        """The Save Project request must serialize without mamma/flow/exmr widgets."""
        w = self.window()
        w._selected_tool = 'gvhmr'
        payload = dict(workspace_view=w.workspace_view(),
                       workspace_settings=w.workspace_settings(),
                       correction=w.selected_correction_options())
        self.assertNotIn('mamma_inputs', payload)
        self.assertNotIn('flow_options', payload)

    def test_preview_audio_source(self):
        from mocap.preview_audio import source_for_preview
        w = self.window()
        w.video_path = Path('/some/clip.mp4')
        w.project = None
        source, start = source_for_preview(w)
        self.assertEqual(start, 0.0)

    def test_find_person_models_are_preparable(self):
        """Find person must route to a Model Manager that can actually prepare
        YOLO/OSNet, not to a page that lists nothing (macOS trim bug)."""
        from mocap.model_manager import model_consumers, workflow_catalog
        w = self.window()
        w.video_path = Path('/tmp/clip.mp4')
        w.video_readable = True
        w._selected_tool = 'gvhmr'
        catalog = workflow_catalog()
        consumers = model_consumers(catalog)
        self.assertIn('person_reid', catalog['gvhmr'])
        self.assertEqual(consumers['person_reid'], ('gvhmr',))
        # With every people model faked as installed, find_people must not
        # redirect to the Model Manager at all.
        with patch('mocap.models.missing', return_value=[]):
            opened = []
            with patch.object(type(w), 'open_model_manager', lambda self: opened.append(True)):
                w.find_people()
        self.assertEqual(opened, [])


if __name__ == '__main__':
    unittest.main()
