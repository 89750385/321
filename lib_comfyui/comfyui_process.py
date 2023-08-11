import atexit
import inspect
import os
import subprocess
import sys
from pathlib import Path

from lib_comfyui import ipc, torch_utils, argv_conversion, global_state
from lib_comfyui.webui import settings
from lib_comfyui.comfyui import pre_main, print_sys_path


comfyui_process = None


@ipc.restrict_to_process('webui')
def start():
    from modules import shared

    if not getattr(shared.opts, 'comfyui_enabled', True):
        return

    install_location = settings.get_install_location()
    if not install_location.exists():
        print('[sd-webui-comfyui]', f'Could not find ComfyUI under directory "{install_location}". The server will NOT be started.', file=sys.stderr)
        return

    ipc.current_callback_listeners = {'webui': ipc.callback.CallbackWatcher(ipc.call_fully_qualified, 'webui', global_state.ipc_strategy_class, clear_on_init=True)}
    ipc.current_callback_proxies = {'comfyui': ipc.callback.CallbackProxy('comfyui', global_state.ipc_strategy_class, clear_on_init=True)}
    ipc.start_callback_listeners()
    atexit.register(stop)
    start_comfyui_process(install_location)


@ipc.restrict_to_process('webui')
def start_comfyui_process(comfyui_install_location):
    global comfyui_process

    executable = get_comfyui_executable(comfyui_install_location)
    comfyui_env = get_comfyui_env(executable, comfyui_install_location)
    install_comfyui_requirements(executable, comfyui_install_location, comfyui_env)
    args = [executable, inspect.getfile(pre_main)] + argv_conversion.get_comfyui_args()
    comfyui_process = subprocess.Popen(
        args=args,
        executable=executable,
        cwd=str(comfyui_install_location),
        env=comfyui_env,
    )


def get_comfyui_executable(comfyui_install_location):
    executable = sys.executable
    venv = comfyui_install_location / 'venv'
    if venv.exists():
        if os.name == 'nt':
            executable = venv / 'scripts' / 'python.exe'
        else:
            executable = venv / 'bin' / 'python'

        print('[sd-webui-comfyui]', f'Detected custom ComfyUI venv:', venv)

    return str(executable)


def get_comfyui_env(executable, comfyui_install_location):
    comfyui_env = os.environ.copy()
    comfyui_sys_path = get_base_sys_path(executable, comfyui_install_location)
    comfyui_sys_path[:0] = (str(comfyui_install_location), settings.get_extension_base_dir())
    comfyui_env['PYTHONPATH'] = os.pathsep.join(comfyui_sys_path)
    comfyui_env['SD_WEBUI_COMFYUI_IPC_STRATEGY_CLASS_NAME'] = global_state.ipc_strategy_class.__name__
    return comfyui_env


def get_base_sys_path(executable, comfyui_install_location):
    env = os.environ.copy()
    del env['PYTHONPATH']
    return subprocess.run(
        args=[executable, inspect.getfile(print_sys_path)],
        executable=executable,
        cwd=str(comfyui_install_location),
        env=env,
        text=True,
        capture_output=True,
    ).stdout.split(os.pathsep)[1:]  # remove PYTHONHOME because it is automatically added


def install_comfyui_requirements(executable, comfyui_install_location, comfyui_env):
    if executable == sys.executable:
        return

    print('[sd-webui-comfyui]', f'Installing mandatory pip requirements in ComfyUI venv...')
    subprocess.check_call(
        args=[
            executable,
            *(['-s'] if "python_embeded" in executable or "python_embedded" in executable else []),
            '-m',
            'pip',
            'install',
            '-r',
            str(Path(settings.get_extension_base_dir(), 'requirements.txt')),
        ],
        executable=executable,
        cwd=str(comfyui_install_location),
        env=comfyui_env,
    )


@ipc.restrict_to_process('webui')
def stop():
    atexit.unregister(stop)
    stop_comfyui_process()
    ipc.stop_callback_listeners()


@ipc.restrict_to_process('webui')
def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    print('[sd-webui-comfyui]', 'Attempting to gracefully terminate the ComfyUI server...')
    comfyui_process.terminate()
    try:
        comfyui_process.wait(global_state.comfyui_graceful_termination_timeout)
        print('[sd-webui-comfyui]', 'The ComfyUI server was gracefully terminated')
    except subprocess.TimeoutExpired:
        print('[sd-webui-comfyui]', 'Graceful termination timed out. Killing the ComfyUI server...')
        comfyui_process.kill()
        print('[sd-webui-comfyui]', 'The ComfyUI server was killed')
    comfyui_process = None
