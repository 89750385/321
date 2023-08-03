import json
import os
import sys
import textwrap
import gradio as gr
import install_comfyui
from lib_comfyui import webui_settings, external_code, ipc


def create_tab():
    install_location = webui_settings.get_install_location()
    with gr.Blocks() as tab:
        gr.HTML(f"""
            <div id="comfyui_workflow_type_id_list">
                {json.dumps(external_code.get_workflow_type_ids())}
            </div>
        """, visible=False)
        if os.path.exists(install_location):
            gr.HTML(get_comfyui_app_html())
        else:
            with gr.Row():
                gr.Markdown(comfyui_install_instructions_markdown)

            with gr.Column():
                with gr.Row():
                    install_path = gr.Textbox(placeholder=f'Leave empty to install at {install_comfyui.default_install_location}', label='Installation path')

                with gr.Row():
                    install_button = gr.Button('Install ComfyUI', variant='primary')

                with gr.Row():
                    installed_feedback = gr.Markdown()

            install_button.click(automatic_install_comfyui, inputs=[install_path], outputs=[installed_feedback], show_progress=True)

    return [(tab, 'ComfyUI', 'comfyui_webui_root')]


@ipc.restrict_to_process('webui')
def automatic_install_comfyui(install_location):
    from modules import shared
    install_location = install_location.strip()
    if not install_location:
        install_location = install_comfyui.default_install_location

    if not can_install_at(install_location):
        message = 'Error! The provided path already exists. Please provide a path to an empty or non-existing directory.'
        print(message, file=sys.stderr)
        return gr.Markdown.update(message)

    install_comfyui.main(install_location)
    shared.opts.comfyui_install_location = install_location

    return gr.Markdown.update('Installed! Now please reload the UI.')


def can_install_at(path):
    is_empty_dir = os.path.isdir(path) and not os.listdir(path)
    return not os.path.exists(path) or is_empty_dir


comfyui_install_instructions_markdown = '''
## ComfyUI extension
It looks like your ComfyUI installation isn't set up yet!  
If you already have ComfyUI installed on your computer, go to `Settings > ComfyUI`, and set the proper install location.  
  
Alternatively, if you don't have ComfyUI installed, you can install it with this button:
'''


def get_comfyui_app_html():
    return textwrap.dedent(f'''
        <div id="comfyui_webui_container">
            <iframe
                src="{webui_settings.get_comfyui_client_url()}"
                workflow_type_id="sandbox_tab"
                class="comfyui-embedded-widget"
                style="width:100%; height:100%;">
            </iframe>
        </div>
    ''')
