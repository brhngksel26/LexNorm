# LexNorm

Türkiye Ticaret Sicil Gazetesi (TTSG) ilanlarından yapılandırılmış bilgi çıkarımı yapan servis. Tarama (scan) edilen PDF’ler OCR ile metne dönüştürülür, LLM ile yapılandırılmış JSON çıktı üretilir; isteğe bağlı olarak yalnızca hedef şirket filtrelenir.

## Amaç

- TTSG ilanlarında yer alan şirket bilgilerini (ticaret unvanı, MERSİS, sicil, adres, sermaye, yönetim kurulu, denetçi, esas sözleşme maddeleri vb.) yapılandırılmış şekilde çıkarmak
- Aynı sayfada birden fazla şirket ilanı olabilir; hedef şirket adı veya MERSİS ile filtreleme yapılabilir
- Çıktıda her alan için kaynak metin (`source_text`) tutularak izlenebilirlik sağlanır

## Kullanılan Yöntem

- **OCR:** PaddleOCR (Türkçe), sayfa görüntüleri 300 DPI ile üretilir ([src/pipelines/base_pipeline.py](src/pipelines/base_pipeline.py), [src/pipelines/ocr_executors.py](src/pipelines/ocr_executors.py))
- **LLM:** Ollama ile yerel model; ilan türüne göre farklı prompt kullanılır ([src/pipelines/config.py](src/pipelines/config.py), [src/pipelines/prompt_enum.py](src/pipelines/prompt_enum.py))
- **İlan türü eşlemesi:** `announcement_type` query parametresi ile prompt seçilir: `kuruluş`, `sermaye_artırımı`, `yönetim_kurulu_değişikliği`, `denetçi_değişikliği`, `esas_sözleşme_değişikliği`, `iç_yönerge_yk_ataması`

## Kullanılan Teknolojiler

Bu projede aşağıdaki açık kaynak bileşenler kullanılmaktadır:

- **[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)** — PDF ve görüntülerden metin çıkarmak için OCR motoru. Çok dilli destek ve yapılandırılmış belge çıktısı sunar; TTSG sayfalarındaki Türkçe metinlerin tanınmasında kullanılır.
- **[Qwen2.5](https://ollama.com/library/qwen2.5)** (Ollama üzerinden) — İlan metninden yapılandırılmış bilgi (şirket bilgileri, yönetim kurulu, esas sözleşme maddeleri vb.) çıkarmak için LLM. Ollama ile yerel çalıştırılır; model adı ve sıcaklık `.env` içindeki `MODEL_NAME` ve `MODEL_TEMPERATURE` ile ayarlanır.

## Veri Çıkarım Yaklaşımı

1. **Çoklu PDF:** Her PDF için ilan türü (`announcement_type`) ayrı belirtilir; paralel extraction sonrası yalnızca hedef şirket (isim veya MERSİS ile) eşleşen belgeler birleştirilir.
2. **Konsolidasyon:** Belgeler tarih sırasına göre işlenir; güncel şirket bilgileri, yönetim kurulu ve konsolide esas sözleşme “en güncel değer” mantığıyla üretilir ([src/consolidation/](src/consolidation/)).
3. **Hedef şirket filtresi:** `target_company_name` veya `target_mersis` verilirse OCR metninde hedef blok çıkarılır (token optimizasyonu) ve çıktıda yalnızca eşleşen şirket(ler) döner ([src/pipelines/target_company_filter.py](src/pipelines/target_company_filter.py)).
4. LLM yanıtı JSON olarak parse edilir; kök yapı `companies` array’idir (aynı belgede birden fazla şirket ilanı olabilir).

## LLM Kullanımı

- **Model / sıcaklık:** `OLLAMA_URL`, `MODEL_NAME`, `MODEL_TEMPERATURE` ortam değişkenleri ile ayarlanır (`.env`).
- **Token optimizasyonu:** Hedef şirket verildiğinde OCR tam metninden yalnızca hedef şirkete ait ilan bloğu çıkarılıp LLM’e gönderilir; böylece token kullanımı azaltılır.
- **İlan türüne göre prompt:** Kuruluş, sermaye artırımı, YK değişikliği, denetçi değişikliği, esas sözleşme değişikliği, iç yönerge YK ataması vb. için ayrı prompt’lar kullanılır ([src/pipelines/prompt_enum.py](src/pipelines/prompt_enum.py)).

## Halüsinasyon Kontrolü

- **Doğrulama:** `verify_company_against_ocr` ile şirket adı ve MERSİS değerleri tam OCR metni üzerinde kontrol edilir; eşleşmeyen alanlar null’lanır ([src/pipelines/hallucination_check.py](src/pipelines/hallucination_check.py)).
- **Kurallar:** Tüm prompt’larda “sadece metinde açıkça yazan bilgiyi çıkar; her alan için `source_text` ver” talimatı vardır; `source_text` yoksa ilgili `value` null kabul edilir.

## Çalıştırma Talimatı

### Gereksinimler

- Python 3.13+, [uv](https://github.com/astral-sh/uv) veya pip
- PostgreSQL, Redis (rate limiting için)
- [Ollama](https://ollama.ai) kurulu ve çalışır durumda; kullanılacak model indirilmiş olmalı

### Adımlar

1. Repoyu klonlayın ve dizine girin.
2. `.env.example` dosyasını `.env` olarak kopyalayın ve gerekli değişkenleri doldurun (DB, Redis, JWT, Ollama URL/model vb.). Production ortamında JWT_ACCESS_SECRET_KEY ve JWT_REFRESH_SECRET_KEY için en az 32 byte (örn. `openssl rand -hex 32`) kullanın.
3. Sanal ortam ve bağımlılıklar:
   ```bash
   uv sync
   # veya: pip install -e .
   ```
4. Veritabanı şeması:
   ```bash
   alembic upgrade head
   ```
5. (İsteğe bağlı) Örnek kullanıcılar: `python scripts/seed_users.py`
6. Uygulamayı başlatın:
   ```bash
   uvicorn src.main:app --reload
   ```
7. API dokümantasyonu: [http://localhost:8000/docs](http://localhost:8000/docs)

### Task directory (target_scan)

`POST /v1/scan_document/target_scan` ile gönderilen PDF’ler ve meta bilgisi geçici olarak diske yazılır; Celery worker aynı dizinden okuyarak işi çalıştırır. **API ve worker aynı task dizinini görmelidir.**

- **Ortam değişkeni:** `LEXNORM_TASK_BASE_DIR` (örn. `/data/lexnorm_tasks`). Tanımlı değilse `gettempdir()/lexnorm_tasks` kullanılır.
- **Docker Compose:** Aynı path hem `app` hem `celery_worker` container’ına **aynı volume** olarak mount edilir (ör. `lexnorm_task_data:/tmp/lexnorm_tasks`). Böylece API’nin yazdığı `task_id/doc_0.pdf` ve `meta.json` worker tarafından okunabilir.
- **Farklı hostlar:** API ve worker ayrı makinelerdeyse bu yöntem çalışmaz; ileride task meta’sı Redis, dosyalar object storage ile paylaşılacak şekilde refactor gerekir.

### Docker Compose ile

Servisler: uygulama (API), Celery worker (target_scan görevleri), Redis, PostgreSQL. Ortam değişkenleri `.env` dosyasından okunur (`OLLAMA_URL`, `MODEL_NAME`, `DATABASE_URL`, `REDIS_URL`, JWT ayarları vb.).

```bash
# .env dosyasının dolu olduğundan emin olun
make build
make create-db   # ilk seferde
make migrate
make seed-users  # isteğe bağlı
docker compose up -d   # veya make up
```

Uygulama varsayılan olarak 8000 portunda çalışır (APP_CONTAINER_PORT ile değiştirilebilir).

### Target scan (çoklu PDF, konsolide çıktı)

1. **JWT alın:** `POST /v1/authentication` ile giriş yapıp access token alın.
2. **Tarama başlatın:** `POST /v1/scan_document/target_scan` — `documents` (PDF’ler), `announcement_types` (her PDF için ilan türü, JSON array), `target_company_name` veya `target_mersis` gönderin. Yanıt: `202` + `task_id`.
3. **Sonuç sorgulama:** `GET /v1/scan_document/target_scan/task/{task_id}` — işlem tamamlandıysa `scan_result_id` döner.
4. **Kayıtlı sonuç:** `GET /v1/scan_document/scan_results/{scan_result_id}` — konsolide tablolar ve `belge_bazli_metinler` dahil tam sonuç.

### Örnek istek (tek PDF tarama)

```bash
# Önce /v1/authentication ile JWT alın, sonra:
curl -X POST "http://localhost:8000/v1/scan_document/scan?announcement_type=kuruluş&target_company_name=Parla%20Enerji" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "document=@path/to/ilan.pdf"
```

Hedef şirket filtresi için `target_company_name` veya `target_mersis` query parametresi kullanılabilir; ikisi de verilmezse tüm çıkarılan şirketler döner.

## Çıktılar ve teslim formatı

- **Tek tarama:** API yanıtında ve veritabanında `result` alanında JSON saklanır (`companies` array, `company_information`, sermaye, yönetim, esas sözleşme maddeleri vb.).
- **Target scan sonucu:** `guncel_sirket_bilgileri`, `yonetim_kurulu_uyeleri`, `konsolide_esas_sozlesme`, `belge_bazli_metinler` (her PDF için hedef şirkete ait eksiksiz metin) döner ve `GET /scan_results/{id}` ile alınır.
- **Örnek sonuçlar:** `result/` klasöründe örnek JSON dosyaları (kuruluş ilanı, denetçi değişikliği vb.) bulunur.
- **API çıktıları (teslim):** Target scan ve tek tarama sonuçlarının örnek çıktıları `deliverables/` klasöründe JSON olarak yer alır; güncel şirket bilgileri, yönetim kurulu, konsolide esas sözleşme ve belge bazlı metinler bu dosyalarda bulunabilir.
- **Teslim çıktıları:** Tablolar ve belge bazlı metinler `deliverables/` altında veya `scripts/run_consolidation.py` ile JSON/Markdown/Word olarak üretilebilir.

## Proje Yapısı (özet)

- `src/api/v1/` — Scan ve auth endpoint’leri
- `src/pipelines/` — OCR, extraction pipeline, prompt’lar, hedef şirket filtresi
- `src/consolidation/` — Çoklu belge birleştirme (güncel tablo, YK tablosu, esas sözleşme)
- `src/cruds/`, `src/models/`, `src/schemas/` — Veritabanı ve API şemaları
- `scripts/` — Seed, konsolidasyon script’i (`run_consolidation.py`), belge metin çıkarımı (`run_extract_text.py`)
- `tests/` — Birim testleri (hedef şirket filtresi, konsolidasyon); `uv run pytest tests/`

Detaylı çalıştırma adımları için [RUN.md](RUN.md) dosyasına bakın.
