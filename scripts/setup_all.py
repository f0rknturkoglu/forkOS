#!/usr/bin/env python3
"""Unified bootstrap script for forkOS + Obsidian + Hermes.

Automates:
1. Environment configuration (.env initialization from .env.example)
2. Obsidian Vault path configuration (ensures a local Vault directory exists)
3. Hermes MCP registration (registers forkos-brain -> http://127.0.0.1:8787/mcp)
4. Terminal launcher alias installation (forkos, forkos stop, forkos doctor)
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    print("\n══════════════════════════════════════════════════════════════════")
    print("  forkOS v1.0 · Tam Otomatik Kurulum ve Entegrasyon Sihirbazı")
    print("══════════════════════════════════════════════════════════════════\n")

    # 1. .env yapılandırması
    env_path = ROOT / ".env"
    env_example = ROOT / ".env.example"
    if not env_path.exists():
        if env_example.exists():
            shutil.copy2(env_example, env_path)
            print("✓ .env dosyası .env.example üzerinden oluşturuldu.")
        else:
            print("✗ .env.example bulunamadı!")
            sys.exit(1)
    else:
        print("✓ Mevcut .env dosyası korundu.")

    # 2. Obsidian Vault yapılandırması
    env_content = env_path.read_text(encoding="utf-8")
    lines = env_content.splitlines()
    env_vars = {}
    for line in lines:
        k, sep, v = line.partition("=")
        if sep:
            env_vars[k.strip()] = v.strip().strip("'\"")

    vault_host_path = env_vars.get("OBSIDIAN_VAULT_HOST_PATH", "")
    if not vault_host_path:
        default_vault = (ROOT.parent / "Vault").resolve()
        default_vault.mkdir(parents=True, exist_ok=True)
        # Örnek karşılama notu
        welcome_note = default_vault / "forkOS Hoşgeldiniz.md"
        if not welcome_note.exists():
            welcome_note.write_text(
                "# forkOS Bilgi Deposu (Vault)\n\n"
                "Bu Obsidian Vault, forkOS ile bağlı bilgi deponuzdur.\n"
                "Notlar, günlükler ve proje dokümantasyonları burada Markdown olarak yaşar.\n",
                encoding="utf-8",
            )
        # .env içine yaz
        new_lines = []
        for line in lines:
            if line.startswith("OBSIDIAN_VAULT_HOST_PATH="):
                new_lines.append(f"OBSIDIAN_VAULT_HOST_PATH={default_vault}")
            elif line.startswith("OBSIDIAN_VAULT_NAME=") and not env_vars.get("OBSIDIAN_VAULT_NAME"):
                new_lines.append("OBSIDIAN_VAULT_NAME=Vault")
            else:
                new_lines.append(line)
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"✓ Obsidian Vault dizini oluşturuldu ve bağlandı: {default_vault}")
    else:
        vault_path = Path(vault_host_path).expanduser()
        if not vault_path.is_absolute():
            vault_path = ROOT / vault_path
        vault_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Mevcut Obsidian Vault doğrulandı: {vault_path}")

    # 3. Hermes MCP Entegrasyonu
    if shutil.which("hermes"):
        try:
            # Check if forkos-brain is already added
            list_res = subprocess.run(["hermes", "mcp", "list"], capture_output=True, text=True)
            if "forkos-brain" not in list_res.stdout:
                res = subprocess.run(
                    ["hermes", "mcp", "add", "forkos-brain", "http://127.0.0.1:8787/mcp"],
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0:
                    print("✓ Hermes MCP sunucusu 'forkos-brain' başarıyla eklendi (http://127.0.0.1:8787/mcp).")
                else:
                    print(f"⚠ Hermes MCP eklenirken uyarı: {res.stderr.strip() or res.stdout.strip()}")
            else:
                print("✓ Hermes 'forkos-brain' MCP entegrasyonu zaten kayıtlı.")
        except Exception as e:
            print(f"⚠ Hermes MCP kontrolü atlandı: {e}")
    else:
        print("ℹ Hermes CLI kurulu değil; doğrudan MCP entegrasyonu daha sonra yapılabilir.")

    # 4. Terminal Launcher Alias Kurulumu (forkos, forkos stop, forkos doctor)
    try:
        from forkos import install as install_launcher
        install_launcher()
    except Exception:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "forkos.py"), "install"], check=True)

    print("\n══════════════════════════════════════════════════════════════════")
    print("  Kurulum Tamamlandı! Sistemi Başlatmak İçin:")
    print("══════════════════════════════════════════════════════════════════")
    print("  1. Terminal alias'ını aktif kılın:")
    print("     source ~/.zshrc    (veya bash için: source ~/.bashrc)")
    print("\n  2. forkOS'u çalıştırın:")
    print("     forkos")
    print("\n  3. Kullanışlı komutlar:")
    print("     forkos doctor      → Sağlık kontrolü ve teşhis raporu")
    print("     forkos stop        → Tüm servisleri güvenle durdurma")
    print("     forkos --stable    → Geliştirme (Vite) yerine kararlı modda çalıştırma")
    print("\n  Web Arayüzü: http://127.0.0.1:5173")
    print("  API Dokümantasyonu: http://127.0.0.1:8787/docs\n")


if __name__ == "__main__":
    main()
