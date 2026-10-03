#!/usr/bin/env python3
"""Local, dependency-free terminal entry point for forkOS."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import threading
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
COLOR = sys.stdout.isatty() and 'NO_COLOR' not in os.environ


def run(args, timeout=30):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=True).stdout.strip()


def http(url):
    with urllib.request.urlopen(url, timeout=3) as response:
        return response.status == 200


def wait(check, seconds=90):
    end = time.monotonic() + seconds
    while True:
        try:
            if check():
                return
        except (OSError, subprocess.SubprocessError):
            pass
        if time.monotonic() >= end:
            raise RuntimeError(f'{seconds} saniyede hazır olmadı')
        time.sleep(2)


def step(label, action):
    print(f'  ◌ {label}…', flush=True)
    start = time.monotonic()
    finished = threading.Event()
    def progress():
        while not finished.wait(10):
            print(f'    ⋯ {label} devam ediyor ({time.monotonic()-start:.0f} sn)', flush=True)
    ticker = threading.Thread(target=progress, daemon=True)
    ticker.start()
    try:
        detail = action() or 'hazır'
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        # Command outputs may contain credentials. Never echo captured output.
        reason = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        print(f'  ✗ {label}: {reason}', flush=True)
        raise SystemExit(1)
    finally:
        finished.set()
        ticker.join()
    green = '\033[32m' if COLOR else ''
    reset = '\033[0m' if COLOR else ''
    print(f'  {green}✓{reset} {label} — {detail} ({time.monotonic()-start:.0f} sn)', flush=True)


def settings():
    values = {}
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            key, separator, value = line.partition('=')
            if separator and key in ('OBSIDIAN_VAULT_HOST_PATH', 'OBSIDIAN_VAULT_NAME'):
                values[key] = value.strip().strip('\"\'')
    return values


def install():
    path = Path.home() / '.zshrc'
    original = path.read_text() if path.exists() else ''
    start, end = '# >>> forkOS launcher >>>', '# <<< forkOS launcher <<<'
    block = f'{start}\nalias forkos={shlex.quote(shlex.join([sys.executable, str(Path(__file__).resolve())]))}\n{end}'
    if start in original and end in original:
        before, tail = original.split(start, 1)
        _, after = tail.split(end, 1)
        content = before + block + after
    else:
        content = original.rstrip() + '\n\n' + block + '\n'
    path.write_text(content)
    print('✓ forkos aliası kuruldu. Bu terminalde: source ~/.zshrc')


def main():
    parser = argparse.ArgumentParser(description='forkOS başlangıç checklist’i')
    parser.add_argument('command', nargs='?', default='start', choices=['start', 'doctor', 'install'])
    parser.add_argument('--stable', action='store_true', help='Vite yerine günlük runtime')
    parser.add_argument('--no-open', action='store_true', help='Web sekmesini açma')
    args = parser.parse_args()
    if args.command == 'install':
        install()
        return
    if args.command == 'doctor':
        raise SystemExit(subprocess.call([str(ROOT / 'scripts/forkos_doctor.sh'), 'docker compose'], cwd=ROOT))
    print('\nforkOS · Başlangıç checklist’i\n')
    cfg = settings()
    compose = ['docker', '--context', 'orbstack', 'compose', '-f', 'compose.yaml']
    if cfg.get('OBSIDIAN_VAULT_HOST_PATH'):
        vault = Path(cfg['OBSIDIAN_VAULT_HOST_PATH']).expanduser()
        if not vault.is_absolute():
            vault = ROOT / vault
        step('Obsidian Vault', lambda: 'bulundu' if vault.is_dir() else (_ for _ in ()).throw(RuntimeError('Vault dizini yok; .env ayarını kontrol et')))
        compose += ['-f', 'compose.obsidian.yaml']
    if not args.stable:
        compose += ['-f', 'compose.dev.yaml']

    def engine():
        if not shutil.which('docker'):
            raise RuntimeError('Docker CLI bulunamadı; OrbStack kurulmalı')
        run(['open', '-a', 'OrbStack'])
        wait(lambda: bool(run(['docker', '--context', 'orbstack', 'info', '--format', '{{.ServerVersion}}'])))
        return 'OrbStack'
    step('Container motoru', engine)
    step('Container’lar ve migration', lambda: (run(compose + ['up', '-d', 'db', 'migrate', 'api', 'web'], timeout=600), 'başlatıldı')[1])
    step('PostgreSQL', lambda: wait(lambda: bool(run(compose + ['exec', '-T', 'db', 'sh', '-c', 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"']))))
    step('Backend', lambda: wait(lambda: http('http://127.0.0.1:8787/health')))
    step('Web', lambda: wait(lambda: http('http://127.0.0.1:5173/')))
    def containers_healthy():
        for service in ('db', 'api', 'web'):
            container = run(compose + ['ps', '-q', service])
            if not container:
                return False
            health = run(['docker', '--context', 'orbstack', 'inspect', '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}', container])
            if health not in ('healthy', 'running'):
                return False
        return True
    step('Container sağlık kontrolleri', lambda: wait(containers_healthy, seconds=120))
    step('Obsidian uygulaması', lambda: (run(['open', '-a', 'Obsidian']), 'açıldı')[1])
    if cfg.get('OBSIDIAN_VAULT_NAME'):
        from urllib.parse import quote
        run(['open', 'obsidian://open?vault=' + quote(cfg['OBSIDIAN_VAULT_NAME'], safe='')])
    desktop = Path.home() / '.hermes/hermes-agent/apps/desktop/release/mac-arm64/Hermes.app'
    step('Hermes Desktop', lambda: (run(['open', str(desktop)] if desktop.exists() else ['open', '-a', 'Hermes']), 'açıldı')[1])
    provider = run(['hermes', 'config', 'get', 'model.provider'])
    model = run(['hermes', 'config', 'get', 'model.default'])
    if provider == 'llamacpp':
        def local_model():
            if not (Path.home() / '.hermes/models' / f'{model}.gguf').is_file():
                raise RuntimeError('Yapılandırılmış GGUF dosyası bulunamadı')
            wait(lambda: http('http://127.0.0.1:18434/health'), seconds=120)
            state = json.loads((Path.home() / '.hermes/runtimes/llamacpp/server.json').read_text())
            request = urllib.request.Request(
                'http://127.0.0.1:18434/v1/chat/completions',
                data=json.dumps({'model': model, 'messages': [{'role': 'user', 'content': 'Hi'}], 'max_tokens': 1}).encode(),
                headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + state['api_key']},
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.load(response)
            if not result.get('choices'):
                raise RuntimeError('Model üretim kontrolü başarısız')
            return f'llama.cpp · {model}; üretim doğrulandı; Ollama kullanılmıyor'
        step('Yerel model sunucusu', local_model)
    elif provider == 'ollama':
        step('Ollama', lambda: (run(['open', '-a', 'Ollama']), wait(lambda: http('http://127.0.0.1:11434/api/tags')), model)[2])
    else:
        raise RuntimeError('Hermes yerel sağlayıcıya ayarlı değil')
    step('Hermes → forkOS MCP', lambda: (run(['hermes', 'mcp', 'test', 'forkos-brain'], timeout=90), 'bağlantı doğrulandı')[1])
    def doctor():
        try:
            output = run([str(ROOT / 'scripts/forkos_doctor.sh'), 'docker --context orbstack compose'], timeout=240)
        except subprocess.CalledProcessError as exc:
            print(exc.stdout)
            raise RuntimeError('Doctor başarısız; yukarıdaki FAIL satırını kontrol et') from exc
        print('\n'.join('    ' + line for line in output.splitlines() if line.startswith(('OK', 'WARN', 'Sonuç:'))))
        return 'kontroller tamamlandı'
    step('Uçtan uca doctor', doctor)
    if not args.no_open:
        run(['open', 'http://127.0.0.1:5173/'])
    print('\n✓ forkOS hazır · http://127.0.0.1:5173/\n  Worker varsayılan olarak kapalı. Ayrıntılar: forkos doctor\n')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nBaşlangıç iptal edildi; başlamış servisler korunuyor.')
        sys.exit(130)
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print(f'✗ Başlangıç tamamlanamadı: {type(exc).__name__}. forkos doctor ile kontrol et.')
        sys.exit(1)
