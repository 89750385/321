import atexit
import signal
import builtins
import sys
import os
import runpy
from lib_comfyui import (
    custom_extension_injector,
    ipc,
    parallel_utils,
)
from lib_comfyui.comfyui import routes_extension, queue_tracker
from lib_comfyui.webui import paths


original_print = builtins.print
def comfyui_print(*args, **kwargs):
    return original_print('[ComfyUI]', *args, **kwargs)


def main(comfyui_path, cli_args):
    builtins.print = comfyui_print
    ipc.current_callback_listeners = {'comfyui': parallel_utils.CallbackWatcher(ipc.call_fully_qualified, 'comfyui')}
    ipc.current_callback_proxies = {'webui': parallel_utils.CallbackProxy('webui')}
    ipc.current_process_id = 'comfyui'
    atexit.register(ipc.stop_callback_listeners)
    ipc.start_callback_listeners()

    def sigint_handler(sig, frame):
        exit()

    signal.signal(signal.SIGINT, sigint_handler)
    start_comfyui(comfyui_path, cli_args)


@ipc.restrict_to_process('comfyui')
def start_comfyui(comfyui_path, cli_args):
    sys.path.insert(0, comfyui_path)
    sys.argv[1:] = cli_args

    print('[sd-webui-comfyui]', 'Injecting custom extensions...')
    paths.share_webui_folder_paths()
    patch_comfyui()
    print('[sd-webui-comfyui]', f'Launching ComfyUI with arguments: {" ".join(sys.argv[1:])}')
    runpy.run_path(os.path.join(comfyui_path, 'main.py'), {}, '__main__')


@ipc.restrict_to_process('comfyui')
def patch_comfyui():
    custom_extension_injector.register_webui_extensions()
    routes_extension.patch_server_routes()
    queue_tracker.patch_prompt_queue()
