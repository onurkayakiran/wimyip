# Kubernetes + Argo CD Dağıtımı

Bu doküman, `git push → GitHub Actions (build + GHCR push + manifest
güncelleme) → Argo CD (pull + sync) → rollout` zincirinin bu repo için nasıl
kurulduğunu ve bir cluster'da nasıl ayağa kaldırılacağını anlatır.

## Kapsam

docker-compose.yml'deki servislerden **sadece çekirdek olanlar** bu ilk
aşamada k8s/Argo CD'ye taşındı:

| Dahil |
|---|
| backend, worker, beat, ptr-worker, ptr-worker-country, apex-worker-country |
| frontend |
| remote-api |
| redis, unbound |

MongoDB harici/managed kalıyor — k8s'te Mongo manifesti yok, sadece bağlantı
bilgisi Secret olarak veriliyor.

`control` (docker.sock erişimli izole servis, admin panelindeki "servisi
yeniden başlat" özelliği için kullanılıyordu) ve `backup` (otomatik
mongodump) servisleri artık **tamamen kaldırıldı** — k8s'e taşınmadılar,
docker-compose'dan da silindiler. Admin panelindeki servis durumu/restart
özelliği bilerek kaldırıldı; MongoDB için otomatik yedekleme şu an
kasıtlı olarak yok (bkz. PLAN.md).

## Servis adı / port sözleşmesi

Uygulama kodu (nginx.conf, config.py) belirli Service adlarını sabit olarak
bekliyor — k8s manifestlerinde bu adlar **değiştirilmemeli**:

| Servis | Nereden bekleniyor | k8s Service adı | Port |
|---|---|---|---|
| backend | `frontend/nginx.conf` → `http://backend:8000` | `backend` | 8000 (ClusterIP) |
| redis | `backend/app/core/config.py` → `celery_broker_url` varsayılanı | `redis` | 6379 (ClusterIP) |
| unbound | `backend/app/core/config.py` → `ptr_resolver_host` varsayılanı | `unbound` | 53/udp+tcp (ClusterIP) |
| frontend | dış erişim | `frontend` | NodePort 30080 |
| remote-api | dış erişim | `remote-api` | NodePort 30082 |

NodePort numaraları `k8s/frontend.yaml` ve `k8s/remote-api.yaml` içinde
`nodePort:` alanından değiştirilebilir (30000-32767 aralığında).

Image'lar: `ghcr.io/onurkayakiran/wimyip-backend`,
`ghcr.io/onurkayakiran/wimyip-frontend`,
`ghcr.io/onurkayakiran/wimyip-remote-api`. backend image'ı worker, beat,
ptr-worker, ptr-worker-country ve apex-worker-country tarafından da
(farklı `command` ile) paylaşılıyor.

## Sır yönetimi

Sırlar (Mongo URI+parola, `ADMIN_PASSWORD`) `k8s/` klasöründe **değil** —
bu klasör Argo CD tarafından otomatik senkronize edildiği için oraya
gerçek sır koymak, sırların git geçmişinde kalıcı olarak saklanması
anlamına gelirdi.

Bunun yerine repo kökünde, `.gitignore`'a eklenmiş iki dosya var (proje
zaten `.env` için aynı deseni kullanıyor):

- `k8s-secrets.local.env` — backend/worker/beat/ptr-*/apex-* için:
  `MONGO_URI`, `MONGO_DB`, `ADMIN_PASSWORD`.
- `k8s-secrets-remote-api.local.env` — remote-api için, **izole**: sadece
  `MONGO_URI`, `MONGO_DB` (docker-compose.yml'deki tasarımla aynı: bu
  servis internete açık olduğu için `ADMIN_PASSWORD` /
  `CELERY_BROKER_URL` gibi sırlara hiç erişimi olmamalı).

**Bu iki dosya asla commit edilmemeli.** Cluster'a bir kere elle
uygulanırlar (aşağıdaki kurulum adımlarına bakın); değerleri değiştiğinde
dosyayı güncelleyip `kubectl apply`/`create --dry-run=client -o yaml |
kubectl apply -f -` ile tekrar uygulamak yeterli.

## Kurulum adımları

Aşağıdaki adımlar cluster'a `kubectl` erişimi olan biri tarafından, bir
kereye mahsus çalıştırılır.

### GitHub PAT (Personal Access Token) — adım 1 ve adım 3 için

Adım 1 (GHCR pull secret) `read:packages` yetkisi, adım 3 (Argo CD repo
bağlantısı, repo private olduğu için) ise repo okuma yetkisi (`repo`
scope) gerektiriyor. **Aynı PAT'i her iki adımda da kullanabilirsiniz** —
tek şart, token'ı oluştururken iki yetkiyi de birlikte vermek.

Güvenlik best-practice'i ayrı token kullanmaktır (bir yer sızarsa diğerini
etkilemez), ama tek kullanıcılı bir proje için tek PAT'le gitmek de makul
bir basitleştirmedir — karar size kalmış.

**Not:** `.github/workflows/deploy.yml` içindeki `secrets.GITHUB_TOKEN`
bambaşka bir şey — GitHub Actions'ın her workflow çalışması için otomatik
oluşturduğu geçici bir token, buradaki kişisel PAT'le karıştırılmamalı.

Classic PAT oluşturma adımları (iki yetkiyi de güvenilir şekilde
destekler):

1. GitHub → sağ üst profil fotoğrafı → **Settings**
2. Sol menü, en alt → **Developer settings**
3. **Personal access tokens → Tokens (classic)**
4. **Generate new token → Generate new token (classic)**
5. Bir isim verin (örn. `wimyip-ghcr-argocd`) ve bir **Expiration** (süre)
   seçin
6. Scope'lardan **`read:packages`** ve **`repo`** kutucuklarını işaretleyin
7. **Generate token**
8. Gösterilen token'ı hemen kopyalayın (bir daha gösterilmeyecek) — hem
   adım 1'deki `--docker-password=` hem adım 3'teki Argo CD "Connect
   Repo" parola alanına aynı değeri yapıştırın.

(Alternatif: **Fine-grained token** — Developer settings → Personal access
tokens → Fine-grained tokens → sadece `wimyip` reposu + "Contents:
Read-only" — daha dar kapsamlı olur, ama GHCR paket okuma izni bu modelde
daha yeni/tutarsız olduğu için iki amaç için birden classic PAT şu an
daha güvenilir.)

### 1. GHCR pull secret (repo private ise)

```bash
kubectl create namespace wimyip
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=onurkayakiran \
  --docker-password=<yukarıda oluşturduğunuz PAT> \
  -n wimyip
```

### 2. Uygulama sırları

```bash
kubectl create secret generic wimyip-secrets \
  -n wimyip \
  --from-env-file=k8s-secrets.local.env

kubectl create secret generic wimyip-remote-api-secrets \
  -n wimyip \
  --from-env-file=k8s-secrets-remote-api.local.env
```

### 3. Argo CD'ye repo erişimi (repo private ise)

Argo CD UI → Settings → Repositories → Connect Repo (HTTPS) → repo URL'si +
kullanıcı adı + repo-read yetkili PAT.

Repo URL olarak **`https://github.com/onurkayakiran/wimyip.git`** girin
(sonunda `.git` ile) — bu, `argocd/wimyip-app.yaml` içindeki
`spec.source.repoURL` ile birebir aynı olmalı. Argo CD bu iki URL'yi
normalize etmeden birebir string olarak eşleştiriyor; `.git`'li/`.git`'siz
karışık girilirse Argo CD bunları farklı repo kaydı sanır ve `Application`
senkronize olamaz ("repository not found" hatası).

### 4. Argo CD Application'ı oluştur

```bash
kubectl apply -f argocd/wimyip-app.yaml
```

Argo CD UI'da `wimyip` uygulaması görünmeli, `k8s/` klasöründeki
manifestleri deploy edip zamanla **Synced / Healthy** durumuna gelmeli.

### 5. GitHub repo ayarları

Settings → Actions → General → Workflow permissions → **"Read and write
permissions"** seçili olmalı (CI'ın `k8s/` altındaki manifestlere image tag
commit'i atabilmesi için).

### 6. İlk deploy

`backend/`, `frontend/` veya `remote-api/` altında bir değişiklik `main`'e
push edildiğinde `.github/workflows/deploy.yml` tetiklenir: sadece değişen
bileşenin image'ı build edilip GHCR'a atılır, ilgili `k8s/*.yaml`
dosyalarındaki `image:` satırı yeni SHA ile güncellenip commit'lenir, Argo
CD bu commit'i görüp cluster'ı senkronize eder.

`k8s/**` altındaki değişiklikler workflow'u tekrar tetiklemez
(`paths-ignore`) — bu olmasaydı build → commit → build → commit sonsuz
döngüsü oluşurdu.

## Doğrulama

```bash
kubectl get pods -n wimyip
kubectl get svc -n wimyip
kubectl -n argocd get application wimyip
```
