"""Switch cached model results inside one project without running inference."""
import json
from pathlib import Path
import numpy as np
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHeaderView,
    QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout)
from . import project_workspace as workspace
from .local_choices import offered
from .theme import set_appearance_style, ui_px
from .project_storage import manifest
from .storage import atomic_json

DEFAULTS = 'default_settings'
# Stored keys map to the editor controls. Checkboxes supply their own labels.
DEFAULT_SETTINGS = {
    'gvhmr_options': ('GVHMR', {
        'htd': ('htd_refine', None),
        'footmr': ('footmr_refine', None),
        'handflow': ('handflow_refine', None),
    }),
    'correction': ('Motion Correction', {
        'mode': ('correction_mode', 'Correction Mode'),
        'preset': ('correction_preset', 'Lock Preset'),
        'foot_lock': ('foot_lock', None),
        'hand_lock': ('hand_lock', None),
    }),
    'processing_options': ('Processing Resources', {
        'resource_mode': ('compute_mode', 'Resource Mode'),
    }),
}
PROJECT_DEFAULT_GROUPS = ('correction',)
DEFAULT_RESOURCE_MODE = 'auto'
GVHMR_DEFAULTS = dict(htd=True, footmr=True, handflow=True)


class DefaultSettingsDialog(QDialog):
    def __init__(self, parent, groups, *, reset):
        super().__init__(parent)
        self.setWindowTitle('Reset Default Settings' if reset else 'Save Settings as Default')
        prompt = ('Restore the built-in starting settings?' if reset else
                  'Save these options as your starting settings?')
        scope = ('These values apply the next time you open a video or launch the app. '
                 'The current video keeps its settings.')
        layout = QVBoxLayout(self)
        for text in (prompt, scope):
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)

        values = QTreeWidget()
        values.setHeaderLabels(('Setting', 'Built-in Value' if reset else 'Value to Save'))
        values.setAccessibleName('Starting settings and values')
        values.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        values.setRootIsDecorated(False)
        values.setItemsExpandable(False)
        set_appearance_style(values, 'QTreeWidget::item { padding: 0 8px; }')
        values.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        values.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for title, rows in groups:
            group = QTreeWidgetItem(values, [title])
            font = group.font(0)
            font.setBold(True)
            group.setFont(0, font)
            for label, value in rows:
                QTreeWidgetItem(group, [label, value])
        values.expandAll()
        layout.addWidget(values, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel.setDefault(True)
        cancel.setFocus()
        area = parent.screen().availableGeometry()
        self.resize(min(ui_px(600), area.width() - 32), min(ui_px(560), area.height() - 64))


class ModelWorkspace:
    def workspace_settings(self):
        return dict(result=self.active_result,correction=self.selected_correction_options())

    def restore_workspace_settings(self,settings):
        from .motion_tools import result_options,has_handflow,result_kind
        gvhmr=self.model_choice.currentData()=='gvhmr'
        kind=settings.get('result',result_kind(gvhmr,gvhmr,True,gvhmr))
        for widget,value in ((self.htd_refine,result_options(kind)[0]),(self.footmr_refine,result_options(kind)[1]),
                             (self.handflow_refine,has_handflow(kind)),(self.motion_correction,kind.startswith('corrected_'))):
            widget.blockSignals(True);widget.setChecked(value);widget.blockSignals(False)
        self.restore_correction_options(settings.get('correction',{}))
        self.active_result=self.selected_result()

    def default_option_text(self, control, key, value):
        if isinstance(control, QComboBox):
            index = offered(control, value)
            return control.itemText(index) if index >= 0 else None
        if type(value) is bool:
            return 'On' if value else 'Off'
        return None

    def confirm_default_settings(self, settings, *, reset):
        groups = []
        for group, (title, fields) in DEFAULT_SETTINGS.items():
            rows = []
            for key, (name, label) in fields.items():
                control = getattr(self, name)
                value = self.default_option_text(control, key, settings[group][key])
                rows.append((label if label is not None else control.text(), value or 'Unavailable'))
            groups.append((title, rows))
        return DefaultSettingsDialog(self, groups, reset=reset).exec() == QDialog.DialogCode.Accepted

    def save_default_settings(self):
        from .resource_safety import update

        settings = self.workspace_settings()
        if self._selected_tool == 'gvhmr':
            htd, footmr, handflow = (control.isChecked() for control in
                                     (self.htd_refine, self.footmr_refine, self.handflow_refine))
        else:
            htd, footmr, _, handflow = self._tool_refinement.get('gvhmr', (True, True, True, True))
        settings['gvhmr_options'] = dict(htd=htd, footmr=footmr, handflow=handflow)
        settings['processing_options'] = {'resource_mode': self.compute_mode.currentData()}
        value = {group: {key: settings[group][key] for key in fields}
                 for group, (_, fields) in DEFAULT_SETTINGS.items()}
        if not self.confirm_default_settings(value, reset=False):
            return
        try:
            update({DEFAULTS: value})
        except (OSError, ValueError) as error:
            self.status.setText('Could not save default settings. See Console.')
            self.log.append('Cannot save default settings: ' + str(error))
            return
        self.status.setText('Default settings saved for new videos.')
        self.log.append('Default settings saved. New videos, the next start and models a project has no settings for use them.')

    def reset_default_settings(self):
        from .correction_settings import correction_options
        from .resource_safety import update

        built_in = dict(gvhmr_options=GVHMR_DEFAULTS,
                        correction=correction_options(),
                        processing_options={'resource_mode': DEFAULT_RESOURCE_MODE})
        if not self.confirm_default_settings(built_in, reset=True):
            return
        try:
            update({DEFAULTS: None})
        except (OSError, ValueError) as error:
            self.status.setText('Could not reset default settings. See Console.')
            self.log.append('Cannot reset default settings: ' + str(error))
            return
        self._reset_starting_settings = True
        self.status.setText('Default settings reset for new videos.')
        self.log.append('Default settings reset. New videos and the next start use the built-in settings.')

    def default_groups(self):
        """Saved defaults by group, only values that pass their check; None when nothing is saved."""
        from .local_choices import saved
        start = saved(DEFAULTS)
        if not isinstance(start, dict):
            return None
        groups = {}
        for group, (_, fields) in DEFAULT_SETTINGS.items():
            values = start.get(group)
            groups[group] = {}
            if isinstance(values, dict):
                for key, (name, _) in fields.items():
                    if key in values and self.default_option_text(getattr(self, name), key, values[key]) is not None:
                        groups[group][key] = values[key]
        return groups

    def with_default_groups(self, settings, model):
        defaults = self.default_groups()
        if defaults is None:
            return settings
        # Saved project groups and preview selections take precedence.
        settings = {**settings, **{group: defaults[group] for group in PROJECT_DEFAULT_GROUPS
                                   if not isinstance(settings.get(group), dict)}}
        if model == 'gvhmr' and 'result' not in settings and defaults['gvhmr_options']:
            from .motion_tools import result_kind
            options = {**GVHMR_DEFAULTS, **defaults['gvhmr_options']}
            settings['result'] = result_kind(options['htd'], options['footmr'], True, options['handflow'])
        return settings

    def apply_default_settings(self):
        # New work. A missing or unusable value keeps restore_workspace_settings' built-in value for that setting.
        defaults=self.default_groups()
        reset = self._reset_starting_settings
        self._reset_starting_settings = False
        if defaults is None:
            if reset:
                # These settings otherwise carry over between clips in the same session.
                self.compute_mode.setCurrentIndex(self.compute_mode.findData(DEFAULT_RESOURCE_MODE))
                self.camera_tools.restore_background({})
                self._tool_refinement['gvhmr'] = (GVHMR_DEFAULTS['htd'], GVHMR_DEFAULTS['footmr'],
                                                  True, GVHMR_DEFAULTS['handflow'])
            return
        from .motion_tools import result_kind

        mode = defaults['processing_options'].get('resource_mode', DEFAULT_RESOURCE_MODE)
        self.compute_mode.setCurrentIndex(self.compute_mode.findData(mode))
        self.camera_tools.restore_background({})
        options = {**GVHMR_DEFAULTS, **defaults['gvhmr_options']}
        self._tool_refinement['gvhmr'] = (options['htd'], options['footmr'], True, options['handflow'])
        settings = self.workspace_settings()
        if self._selected_tool == 'gvhmr':
            settings['result'] = result_kind(options['htd'], options['footmr'],
                                             self.motion_correction.isChecked(), options['handflow'])
        for group in PROJECT_DEFAULT_GROUPS:
            fields = DEFAULT_SETTINGS[group][1]
            settings[group] = {**{key: value for key, value in settings[group].items() if key not in fields},
                               **defaults[group]}
        try:self.restore_workspace_settings(settings)
        except (OSError,ValueError,KeyError,TypeError) as error:self.log.append('Default settings not applied: '+str(error))

    def workspace_view(self):
        fps=self.info['fps'] if self.info else 30.
        return dict(source_time=self.source_offset+self.slider.value()/fps,
            trim_time=[self.source_offset+self.slider.clip_in/fps,self.source_offset+self.slider.clip_out/fps],
            camera={**{key:np.asarray(getattr(self.motion_view,key)).tolist()
                    for key in ('yaw','pitch','distance','pan','scene_center')},'target':self.motion_view.target().tolist()})

    def remember_workspace_model(self):
        root=self.workspace_root
        if root is None:return
        if self.project is not None:
            state=manifest(self.project)
            state.setdefault('pipeline',{})['result']=self.active_result
            settings=self.workspace_settings()
            for key in PROJECT_DEFAULT_GROUPS:
                if key in settings:state[key]=settings[key]
            atomic_json(self.project/'project.json',state)
            saved=workspace.set_active(root,state['pipeline']['model'],self.project,self.workspace_view())
            model=state['pipeline']['model']
        else:
            model=self._selected_tool
            saved=workspace.set_active(root,model,view=self.workspace_view())
        saved['models'][model]['settings']=self.workspace_settings()
        atomic_json(root/'project.json',saved)

    def restore_workspace_view(self,view):
        self.camera_tools.restore_background(view.get('camera_background',{}))
        if self.info:
            fps=self.info['fps']
            times=view.get('trim_time')
            if times:
                first=max(0,round((times[0]-self.source_offset)*fps))
                end=min(self.slider.maximum()+1,round((times[1]-self.source_offset)*fps))
                if first<end:self.slider.set_clip(first,end)
            frame=round((view.get('source_time',self.source_offset)-self.source_offset)*fps)
            self.slider.setValue(max(0,min(self.slider.maximum(),frame)))
            self.seek(self.slider.value())
        if view.get('camera'):
            self._workspace_camera=view['camera']
            self.restore_workspace_camera()

    def restore_workspace_camera(self,consume=False):
        camera=getattr(self,'_workspace_camera',None)
        if not camera:return
        for key,value in camera.items():
            if key=='target':continue
            setattr(self.motion_view,key,np.asarray(value,float) if key in ('pan','scene_center') else float(value))
        if 'target' in camera:self.motion_view.pan+=np.asarray(camera['target'])-self.motion_view.target()
        self.motion_view.auto_fit=False
        self.motion_view.update()
        if consume and (self.people_root is None or self.scene_data is not None):self._workspace_camera=None

    def open_workspace(self,root):
        try:
            root=Path(root).resolve();state=workspace.read(root)
            workspace.model_project(root,state['active_model'],state)
            if self.workspace_root is not None and self.workspace_root!=root and not self.busy:
                self.remember_workspace_model()
            self.workspace_root=root
            self._workspace_camera=None
            if not self.switch_workspace_model(state['active_model'],opening=True):
                return False
            return True
        except (OSError,ValueError,KeyError) as error:
            self.status.setText('Cannot open project: '+str(error));return False

    def switch_workspace_model(self,model,opening=False):
        root=self.workspace_root
        try:
            state=workspace.read(root)
            if not opening:
                view=self.workspace_view()
                self.remember_workspace_model()
                state=workspace.read(root)
            else:view=state.get('models',{}).get(model,{}).get('view',state.get('view',{}))
            target=workspace.model_project(root,model,state)
            self.stop_playback()
            self._workspace_loading=True
            try:
                if (target/'project.json').is_file():
                    self.load_project(target)
                else:
                    self.clear_preview();self.reset_people();self.project=None
                    self.video_view.set_observations({})
                    self.model_choice.blockSignals(True)
                    self.model_choice.setCurrentIndex(self.model_choice.findData(model))
                    self.model_choice.blockSignals(False)
                    self.select_model()
                    settings = state.get('models', {}).get(model, {}).get('settings', {})
                    self.restore_workspace_settings(self.with_default_groups(settings, model))
                    self.status.setText(
                        f'{self.model_choice.currentText()} has no saved motion in this project. Use Reconstruct 3D.')
            finally:self._workspace_loading=False
            workspace.set_active(root,model,target if (target/'project.json').is_file() else None,view)
            self._workspace_pending_view=view
            self.restore_workspace_view(view)
            self.setWindowTitle('RGB MoCap | '+root.name)
            self.update_readiness()
            return True
        except (OSError,ValueError,KeyError) as error:
            self.model_choice.blockSignals(True)
            self.model_choice.setCurrentIndex(self.model_choice.findData(self._selected_tool))
            self.model_choice.blockSignals(False)
            self.status.setText('Cannot switch model: '+str(error));return False

    def workspace_project_loaded(self,project,state):
        root=workspace.root_for(project,state)
        self.workspace_root=root
        self._workspace_video_reference=root is not None
        if root is not None:
            workspace.set_active(root,state['pipeline']['model'],project)
