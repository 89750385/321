import json
import operator
from typing import Tuple

import gradio as gr
from lib_comfyui import external_code, global_state
from lib_comfyui.webui import gradio_utils, settings
from lib_comfyui.comfyui import iframe_requests


class AccordionInterface:
    def __init__(self, get_elem_id, tab):
        from modules import ui

        self.tab = tab

        self.workflow_types = external_code.get_workflow_types(self.tab)
        self.first_workflow_type = self.workflow_types[0]
        self.workflow_type_ids = {
            workflow_type.display_name: workflow_type.get_ids(self.tab)[0]
            for workflow_type in self.workflow_types
        }

        self.accordion = gr.Accordion(
            label='ComfyUI',
            open=False,
            elem_id=get_elem_id('accordion'),
        )

        self.iframes = gr.HTML(value=self.get_iframes_html(self.workflow_type_ids[self.first_workflow_type.display_name]))
        self.enable = gr.Checkbox(
            label='Enable',
            elem_id=get_elem_id('enabled'),
            value=False,
        )
        self.current_workflow_display_name = gr.Dropdown(
            label='Edit workflow type',
            choices=[workflow_type.display_name for workflow_type in self.workflow_types],
            value=self.first_workflow_type.display_name,
            elem_id=get_elem_id('displayed_workflow_type'),
        )
        self.queue_front = gr.Checkbox(
            label='Queue front',
            elem_id=get_elem_id('queue_front'),
            value=True,
        )
        self.refresh_button = gr.Button(
            value=f'{ui.refresh_symbol} Reload ComfyUI interfaces (client side)',
            elem_id=get_elem_id('refresh_button'),
        )

        self.enabled_display_names = gradio_utils.ExtensionDynamicProperty(
            key=f'enabled_display_names_{self.tab}',
            value=[],
        )
        self.enabled_workflow_type_ids = gradio_utils.ExtensionDynamicProperty(
            key=f'enabled_workflow_type_ids_{self.tab}',
            value={},
        )
        self.clear_enabled_workflow_types_button = gr.Button(
            elem_id=get_elem_id('clear_enabled_workflow_types'),
            visible=False,
        )

        self._rendered = False

    def get_iframes_html(self, first_workflow_type_id: str) -> str:
        comfyui_client_url = settings.get_comfyui_client_url()

        iframes = []
        for workflow_type_id in external_code.get_workflow_type_ids(self.tab):
            html_classes = ['comfyui-embedded-widget']
            if workflow_type_id == first_workflow_type_id:
                html_classes.append('comfyui-embedded-widget-display')

            iframes.append(f"""
                <iframe
                    src="{comfyui_client_url}"
                    workflow_type_id="{workflow_type_id}"
                    class="{' '.join(html_classes)}"
                    style="width:100%; height:500px;">
                </iframe>
            """)

        return f"""
            <div class="comfyui_iframes">
                {''.join(iframes)}
            </div>
        """

    def arrange_components(self):
        if self._rendered:
            return

        with self.accordion.render():
            with gr.Row():
                self.iframes.render()

            with gr.Row():
                with gr.Column():
                    self.enable.render()
                    self.current_workflow_display_name.render()

                with gr.Column():
                    self.queue_front.render()
                    self.refresh_button.render()

        self.enabled_display_names.render()
        self.enabled_workflow_type_ids.render()
        self.clear_enabled_workflow_types_button.render()

    def connect_events(self):
        if self._rendered:
            return

        self.refresh_button.click(
            fn=None,
            _js='reloadComfyuiIFrames'
        )

        self.activate_clear_enabled_workflow_types_button()
        self.activate_displayed_workflow_type()
        self.activate_enabled_workflow_types()
        self._rendered = True

    def get_script_ui_components(self) -> Tuple[gr.components.Component, ...]:
        return self.queue_front, self.enabled_workflow_type_ids

    def setup_infotext_fields(self, script):
        workflows_infotext_field = gr.Textbox(visible=False)
        workflows_infotext_field.change(
            fn=self.on_infotext_change,
            inputs=[workflows_infotext_field, self.current_workflow_display_name],
            outputs=[workflows_infotext_field, self.enabled_display_names, self.enable],
        )
        script.infotext_fields = [(workflows_infotext_field, 'ComfyUI Workflows')]

    def activate_clear_enabled_workflow_types_button(self):
        self.clear_enabled_workflow_types_button.click(
            fn=lambda: [],
            outputs=[self.enabled_display_names],
        )

    def activate_displayed_workflow_type(self):
        current_workflow_type_id = gr.HTML(
            value=self.workflow_type_ids[self.first_workflow_type.display_name],
            visible=False,
        )
        self.current_workflow_display_name.change(
            fn=self.workflow_type_ids.get,
            inputs=[self.current_workflow_display_name],
            outputs=[current_workflow_type_id],
        )
        current_workflow_type_id.change(
            fn=None,
            _js='changeDisplayedWorkflowType',
            inputs=[current_workflow_type_id],
        )

    def activate_enabled_workflow_types(self):
        self.enabled_display_names.change(
            fn=self.on_enabled_display_names_change,
            inputs=[self.enabled_display_names],
            outputs=[self.enabled_workflow_type_ids],
        )

        self.activate_enabled_checkbox()
        self.activate_dropdown_colors()

    def activate_dropdown_colors(self):
        style_body = '''{
            color: greenyellow !important;
            font-weight: bold;
        }'''

        dropdown_input_style = gr.HTML()
        for comp in (self.enabled_display_names, self.current_workflow_display_name):
            comp.change(
                fn=lambda enabled_display_names, current_workflow_display_name: f'''<style>
                    div#{self.current_workflow_display_name.elem_id} input {style_body}
                </style>''' if current_workflow_display_name in enabled_display_names else '',
                inputs=[self.enabled_display_names, self.current_workflow_display_name],
                outputs=[dropdown_input_style],
            )

        dropdown_list_style = gr.HTML()
        self.enabled_display_names.change(
            fn=lambda enabled_display_names, current_workflow_display_name: f'''<style>
                {','.join(
                    f'div#{self.current_workflow_display_name.elem_id} ul.options > li.item[data-value="{display_name}"]'
                    for display_name in enabled_display_names
                )} {style_body}
            </style>''',
            inputs=[self.enabled_display_names, self.current_workflow_display_name],
            outputs=[dropdown_list_style],
        )

    def activate_enabled_checkbox(self):
        self.current_workflow_display_name.change(
            fn=operator.contains,
            inputs=[self.enabled_display_names, self.current_workflow_display_name],
            outputs=[self.enable],
        )

        self.enable.select(
            fn=lambda enabled_display_names, current_workflow_display_name, enable: list(
                (operator.or_ if enable else operator.sub)(
                    set(enabled_display_names),
                    {current_workflow_display_name},
                )
            ),
            inputs=[self.enabled_display_names, self.current_workflow_display_name, self.enable],
            outputs=[self.enabled_display_names]
        )

    def on_enabled_display_names_change(self, enabled_display_names):
        enabled_workflow_type_ids = {
            self.workflow_type_ids[workflow_type.display_name]: workflow_type.display_name in enabled_display_names
            for workflow_type in self.workflow_types
        }
        return enabled_workflow_type_ids

    def on_infotext_change(self, serialized_graphs, current_workflow_display_name):
        if not serialized_graphs:
            return (gr.skip(),) * 3

        if not hasattr(global_state, 'enabled_workflow_type_ids'):
            global_state.enabled_workflow_type_ids = {}

        serialized_graphs = json.loads(serialized_graphs)
        workflow_graphs = {
            workflow_type.get_ids(self.tab)[0]: (
                serialized_graphs.get(workflow_type.base_id, json.loads(workflow_type.default_workflow)),
                workflow_type,
            )
            for workflow_type in self.workflow_types
        }

        new_enabled_display_names = []
        for workflow_type_id, (graph, workflow_type) in workflow_graphs.items():
            is_custom_workflow = workflow_type.base_id in serialized_graphs
            global_state.enabled_workflow_type_ids[workflow_type_id] = is_custom_workflow
            if is_custom_workflow:
                new_enabled_display_names.append(workflow_type.display_name)
            iframe_requests.set_workflow_graph(graph, workflow_type_id)

        return (
            gr.Textbox.update(value=''),
            gr.update(value=new_enabled_display_names),
            gr.update(value=current_workflow_display_name in new_enabled_display_names),
        )
