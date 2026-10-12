#!/usr/bin/env python3
"""Owned, tools-free named-profile lifecycle. Never clones or logs personal credentials."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROFILE = Path.home() / '.hermes/profiles/forkos-goal-studio'
MARKER = PROFILE / '.forkos-goal-studio-owned'


def clean_environment():
    return {**{k: os.environ[k] for k in ('HOME', 'PATH', 'TMPDIR', 'LANG') if k in os.environ}, 'HERMES_DISABLE_LAZY_INSTALLS': '1'}


def init():
    if PROFILE.exists():
        raise RuntimeError('Profil zaten var; config veya credential üzerine yazılmadı')
    subprocess.run(['hermes', 'profile', 'create', 'forkos-goal-studio', '--no-skills', '--no-alias'], check=True, env=clean_environment())
    shutil.copyfile(ROOT / 'config/hermes-goal-studio/config.yaml', PROFILE / 'config.yaml')
    api_key, model_key = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    files = {
        '.env': f'API_SERVER_KEY={api_key}\nOPENAI_API_KEY={model_key}\nOPENAI_BASE_URL=http://127.0.0.1:18435/v1\n',
        'model.key': model_key + '\n',
        'forkos.env': f'HERMES_GOAL_API_KEY={api_key}\nHERMES_GOAL_MODEL_API_KEY={model_key}\n',
        '.forkos-goal-studio-owned': '1\n',
    }
    for name, content in files.items():
        path = PROFILE / name
        path.write_text(content)
        path.chmod(0o600)
    for name in ('hooks', 'plugins', 'cron'):
        (PROFILE / name).mkdir(exist_ok=True)
    print('Ayrı profil hazır. Model dosyasını sağla; OAuth login otomatik yapılmaz.')


def require_owned():
    if not MARKER.is_file() or MARKER.is_symlink() or MARKER.read_text().strip() != '1':
        raise RuntimeError('forkOS tarafından kurulmuş ayrı profil gerekli; kişisel profil değiştirilemez')


def birth(pid):
    return subprocess.check_output(['ps', '-o', 'lstart=', '-p', str(pid)], text=True).strip()


def alive(name):
    path = PROFILE / ('forkos-' + name + '.process.json')
    if not path.exists():
        return False
    item = json.loads(path.read_text())
    try:
        return bool(item['start']) and birth(item['pid']) == item['start']
    except subprocess.CalledProcessError:
        return False


def spawn(name, command):
    if alive(name):
        return
    with (PROFILE / ('forkos-' + name + '.log')).open('ab') as log:
        proc = subprocess.Popen(command, cwd=PROFILE, env=clean_environment(), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (PROFILE / ('forkos-' + name + '.process.json')).write_text(json.dumps({'pid': proc.pid, 'start': birth(proc.pid)}))


def ready():
    values = dict(line.split('=', 1) for line in (PROFILE / 'forkos.env').read_text().splitlines())
    def get(route):
        request = urllib.request.Request('http://127.0.0.1:8643' + route,
            headers={'Authorization': 'Bearer ' + values['HERMES_GOAL_API_KEY']})
        with urllib.request.urlopen(request, timeout=2) as response:
            return json.load(response)
    health = get('/health/detailed')
    caps = get('/v1/capabilities')
    tools = get('/v1/toolsets')
    rows = tools if isinstance(tools, list) else tools.get('data', [])
    return (health.get('version') == '0.21.6' and health.get('status') == 'ok'
        and caps.get('model') == 'forkos-goal-studio' and caps.get('auth', {}).get('required') is True
        and caps.get('features', {}).get('runs_idempotency', {}).get('durable') is True
        and not any(row.get('enabled') is not False for row in rows))


def start():
    require_owned()
    text = (PROFILE / 'config.yaml').read_text()
    if '\n  provider: custom\n' in text:
        weights = Path.home() / '.hermes/models/Qwen3.5-9B-Q4_K_M.gguf'
        binary = Path.home() / '.hermes/tools/llamacpp-metal-11370-darwin-arm64/llama-server'
        if not weights.is_file() or not binary.is_file():
            raise RuntimeError('Doğrulanmış llama-server ve Qwen3.5-9B-Q4_K_M.gguf gerekli; otomatik indirme yok')
        spawn('model', [str(binary), '--model', str(weights), '--alias', 'Qwen3.5-9B-Q4_K_M', '--host', '127.0.0.1', '--port', '18435', '--api-key-file', str(PROFILE / 'model.key'), '--ctx-size', '65536', '--parallel', '1', '--reasoning', 'off', '--no-ui'])
    spawn('gateway', ['hermes', '-p', 'forkos-goal-studio', 'gateway', 'run'])
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if alive('gateway') and ready():
                print('Goal Studio daemon · 127.0.0.1:8643; çıkarım backend iznine bağlı')
                return
        except OSError:
            pass
        time.sleep(0.5)
    raise RuntimeError('Goal Studio daemon hazır değil; ayrı profil loglarını kontrol et')


def stop():
    require_owned()
    for name in ('gateway', 'model'):
        path = PROFILE / ('forkos-' + name + '.process.json')
        if alive(name):
            item = json.loads(path.read_text())
            os.kill(item['pid'], signal.SIGTERM)
            deadline = time.monotonic() + 30
            while alive(name) and time.monotonic() < deadline:
                time.sleep(0.2)
            if alive(name):
                raise RuntimeError(name + ' güvenle kapanmadı; zorla sonlandırılmadı')
        path.unlink(missing_ok=True)
    print('Goal Studio kapalı; profil, sohbetler ve model dosyası korundu')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('init', 'start', 'stop', 'status'))
    args = parser.parse_args()
    if args.command == 'status':
        require_owned()
        print(json.dumps({name: alive(name) for name in ('gateway', 'model')}))
    else:
        globals()[args.command]()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc
