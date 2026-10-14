# forkOS — Agentic Setup Prompt (Ajan ile Tek Adımda Kurulum)

Bu doküman, forkOS'u herhangi bir AI kodlama ajanına (Claude Code, Cursor Agent, OpenAI Codex, ChatGPT, Antigravity vb.) **tek bir prompt ile sıfırdan kurdurmak ve entegrasyonlarını tamamlatmak** için hazırlanmıştır.

Aşağıdaki promptu kopyalayıp kullandığınız yapay zekâ ajanına yapıştırmanız yeterlidir.

---

## 🇹🇷 Türkçe Agentic Setup Prompt (Kopyala & Yapıştır)

```text
Sen forkOS kurulumunu ve yerel entegrasyonlarını gerçekleştirecek uzman bir sistem mühendisisin.
Bulunduğun çalışma dizininde forkOS projesini, yerel Obsidian Vault entegrasyonunu, Hermes MCP bağlantısını ve terminal başlatıcılarını (forkos, forkos stop, forkos doctor) uçtan uca kurmanı istiyorum.

Aşağıdaki adımları sırasıyla uygula ve her adımın çıktısını doğrula:

1. ORTAM KONTROLÜ:
   - Sistemde Docker/OrbStack veya Podman olup olmadığını denetle.
   - Python (>= 3.11) ve Make araçlarının varlığını doğrula.

2. .ENV VE OBSIDIAN VAULT YAPILANDIRMASI:
   - Eğer .env dosyası yoksa, .env.example dosyasını .env olarak kopyala.
   - .env içindeki BIND_ADDR değerinin 127.0.0.1 olduğunu teyit et.
   - Obsidian Vault entegrasyonu için: Eğer OBSIDIAN_VAULT_HOST_PATH tanımlı değilse, projenin bir üst dizininde yerel bir Vault klasörü oluştur (örn: ../Vault), içine 'forkOS Hoşgeldiniz.md' notu bırak ve .env içine OBSIDIAN_VAULT_HOST_PATH ve OBSIDIAN_VAULT_NAME=Vault olarak kaydet.

3. HERMES MCP ENTEGRASYONU:
   - Sistemde 'hermes' CLI komutunun kurulu olup olmadığını kontrol et.
   - Eğer hermes varsa, 'hermes mcp add forkos-brain http://127.0.0.1:8787/mcp' komutuyla forkOS MCP sunucusunu Hermes'e bağla.

4. TERMİNAL LAUNCHER VE ALIAS'LARIN KURULUMU:
   - 'python3 scripts/forkos.py install' (veya 'make install-launcher') komutunu çalıştır.
   - Bu işlemin ~/.zshrc veya ~/.bashrc dosyasına 'alias forkos=...' tanımını başarıyla eklediğini doğrula.
   - Bu sayede kullanıcının terminalde 'forkos', 'forkos stop' ve 'forkos doctor' komutlarını doğrudan çalıştırabilmesini sağla.

5. CONTAINER'LARI BAŞLATMA VE VERİTABANI MİGRATİON'I:
   - 'make up-obsidian CO="docker compose"' (veya Podman kullanılıyorsa 'make up-obsidian') komutuyla veritabanını, migration geçidini, backend'i ve web arayüzünü ayağa kaldır.
   - Veritabanı (PostgreSQL 16), backend (127.0.0.1:8787/health) ve frontend (127.0.0.1:5173) servislerinin sağlıklı çalıştığını curl/HTTP ile doğrula.

6. DOĞRULAMA VE RAPOR:
   - 'python3 scripts/forkos.py doctor' (veya './scripts/forkos_doctor.sh') çalıştırarak tüm kontrollerin (Container motoru, DB, API, Web, Migration, Obsidian, Hermes MCP) 'OK' döndüğünü teyit et.
   - Kurulum bittiğinde bana web arayüzü linkini (http://127.0.0.1:5173), API dokümantasyonu linkini (http://127.0.0.1:8787/docs) ve terminalde kullanabileceğim komutları (forkos, forkos stop, forkos doctor) özetle.
```

---

## 🇬🇧 English Agentic Setup Prompt (Copy & Paste)

```text
You are an expert system engineer tasked with setting up forkOS and its local integrations from scratch.
In the current workspace, set up forkOS, its local Obsidian Vault bridge, Hermes MCP integration, and the terminal launcher aliases ('forkos', 'forkos stop', 'forkos doctor').

Execute the following steps sequentially and verify each outcome:

1. ENVIRONMENT CHECK:
   - Check if Docker / OrbStack or Podman is available.
   - Verify Python (>= 3.11) and Make are installed.

2. .ENV & OBSIDIAN VAULT CONFIGURATION:
   - If .env does not exist, copy .env.example to .env.
   - Ensure BIND_ADDR=127.0.0.1 for local-only privacy.
   - If OBSIDIAN_VAULT_HOST_PATH is empty in .env, create a local Vault directory (e.g. ../Vault), add a sample note, and set OBSIDIAN_VAULT_HOST_PATH and OBSIDIAN_VAULT_NAME=Vault in .env.

3. HERMES MCP INTEGRATION:
   - Check if the 'hermes' CLI is installed.
   - If available, register forkOS MCP with: 'hermes mcp add forkos-brain http://127.0.0.1:8787/mcp'.

4. TERMINAL LAUNCHER ALIAS INSTALLATION:
   - Run 'python3 scripts/forkos.py install' (or 'make install-launcher').
   - Verify that 'alias forkos=...' has been written to ~/.zshrc or ~/.bashrc.
   - Confirm that 'forkos', 'forkos stop', and 'forkos doctor' will work seamlessly.

5. CONTAINER STARTUP & MIGRATION:
   - Start the stack with 'make up-obsidian CO="docker compose"' (or Podman equivalent).
   - Ensure the one-shot migration service completes and that db, api, and web containers are healthy.

6. HEALTH VERIFICATION:
   - Run 'python3 scripts/forkos.py doctor' to verify all health checks pass.
   - Report the Web UI URL (http://127.0.0.1:5173), API Swagger docs (http://127.0.0.1:8787/docs), and usage instructions for the terminal commands.
```

---

## ⚡ Alternatif: Tek Komutla Otomatik Script

Eğer ajan kullanmadan doğrudan terminalden tek komutla kurmak isterseniz:

```bash
make setup
```

veya:

```bash
python3 scripts/setup_all.py
```

Bu komut yukarıdaki adımların tamamını (`.env` oluşturma, Obsidian klasörü hazırlama, Hermes MCP kaydı, terminal alias ekleme) saniyeler içinde otomatik olarak tamamlar.
