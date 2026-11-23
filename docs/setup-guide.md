# 설치 가이드 (처음부터)

아무것도 없는 상태에서 이 비서를 만드는 순서예요. 1~5단계만 하면 디스코드에서 대화하는 비서가 켜지고, 6단계부터는 기능을 하나씩 붙이는 단계예요. 각 단계는 앞 단계가 끝났다고 보고 적었어요. 쓰고 싶지 않은 기능의 단계는 건너뛰어도 돼요.

이 문서에서 `<내아이디>`는 내 GitHub 아이디, `<공인 IP>`는 내 VM의 공인 IP로 바꿔 읽으세요.

## 시작 전에

### 만들 계정

| 서비스 | 주소 | 필수 여부 | 비용 |
| --- | --- | --- | --- |
| Oracle Cloud | cloud.oracle.com | 필수 | 무료 (가입 때 카드 등록만) |
| GitHub | github.com | 필수 | 무료 |
| Discord | discord.com | 필수 | 무료 |
| Anthropic Console | console.anthropic.com | 필수 | API 사용량만큼 (비서가 월 100달러로 제한) |
| Google (Gmail, Cloud) | google.com | 선택 | 무료 |
| Microsoft | account.microsoft.com, portal.azure.com | 선택 | 무료 |
| Notion | notion.so | 선택 | 무료 |
| 카카오 Developers | developers.kakao.com | 선택 | 무료 (하루 한도 안) |
| 공공데이터포털 | data.go.kr | 선택 | 무료 |
| healthchecks.io | healthchecks.io | 선택 | 무료 |

### PC에 필요한 것

- Windows PowerShell (기본 설치됨). `ssh`, `scp` 명령이 들어 있어요. macOS·Linux는 터미널을 쓰면 되고, 아래 `icacls` 대신 `chmod 600 키파일`이에요.
- 브라우저 하나. 각 콘솔에 로그인해서 키를 받아요.
- 메모장. 받은 키를 VM에 넣기 전까지 잠깐 보관해요. 다 넣은 뒤에는 지워요.

### 비밀값 규칙

키와 토큰은 VM의 `.env`·`data/` 폴더, GitHub Secrets, 폰 앱 안에만 둬요. 채팅, 코드, 문서, 이슈에는 적지 않아요. 로그나 채팅에 나갔다면 바로 재발급해요.

## 1단계 Oracle: 무료 VM 만들기

비서가 24시간 돌 서버예요. Always Free 범위 안에서만 만들면 요금이 나가지 않아요.

### 계정 만들기

1. cloud.oracle.com → **Start for free** → 이메일 인증.
2. Home Region은 **South Korea North (Chuncheon)** 또는 Central (Seoul)을 골라요. 나중에 바꿀 수 없어요.
3. 카드를 등록해요. 본인 확인용이고, **유료 계정으로 업그레이드하지 않으면** 청구되지 않아요.

### VM 만들기

1. 왼쪽 위 메뉴 → **Compute** → **Instances** → **Create instance**.
2. Name: `ai-assistant`.
3. **Image and shape** → Edit
   - Image: **Canonical Ubuntu** (24.04 또는 22.04)
   - Shape: **VM.Standard.E2.1.Micro** (Always Free-eligible 표시 확인). A1.Flex도 무료지만 자리가 없는 경우가 많아요
4. **Networking**: 새 VCN과 **공개 서브넷**을 만들고, **Assign a public IPv4 address**를 켜요.
5. **Add SSH keys** → **Generate a key pair for me** → **Save private key**. 내려받은 파일을 `C:\Users\<내 계정>\.ssh\oracle.key`로 옮겨요. 이 파일은 다시 받을 수 없어요.
6. Boot volume은 기본값 그대로 두고 **Create**.
7. 상태가 **Running**이 되면 상세 화면의 **Public IP address**를 적어 둬요.

비서는 밖에서 들어오는 연결을 받지 않아서, 방화벽(Security List)은 기본 SSH(22번) 규칙만 있으면 돼요.

### Windows에서 접속하기

1. 키 파일을 내 계정만 읽을 수 있게 바꿔요. 안 하면 `UNPROTECTED PRIVATE KEY FILE` 오류가 나요 (PowerShell).

   ```
   $k = "$env:USERPROFILE\.ssh\oracle.key"
   icacls $k /inheritance:r
   icacls $k /grant:r "$($env:USERNAME):(R)"
   icacls $k
   ```

   마지막 줄 출력에 내 계정 한 줄만 남아야 해요.
2. 접속해요. 처음 한 번은 `yes`를 입력해요.

   ```
   ssh -i "$env:USERPROFILE\.ssh\oracle.key" ubuntu@<공인 IP>
   ```
3. `ubuntu@...:~$` 프롬프트가 나오면 성공이에요. 이 문서에서 "VM에서"는 이 창에서 치라는 뜻이에요.

### 스왑 만들기 (VM에서, 한 번만)

메모리가 1GB라 설치 중에 모자랄 수 있어요. 2GB 스왑을 더해요.

```
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

`free -h`의 Swap 줄에 2.0Gi가 보이면 돼요. VM을 다시 켜도 유지돼요.

## 2단계 GitHub: 저장소와 비서용 토큰

### 저장소 준비

이 저장소(github.com/Ashegyu/claude-discord-assistant)를 내 계정으로 가져와요. 저장소 화면 오른쪽 위 **Fork** → Owner는 내 계정 → **Create fork**. 이후 `<내아이디>/claude-discord-assistant`가 내 비서의 저장소예요. 비공개로 두고 싶으면 포크 대신 새 비공개 저장소를 만들고 코드를 올려도 돼요.

### 비서용 토큰 만들기

VM이 저장소를 받고, 비서가 다른 저장소를 읽고, 자기 개선 PR을 올리려면 토큰이 필요해요.

1. github.com → 프로필 → **Settings** → 맨 아래 **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Token name: `ai-assistant`, Expiration: 90일 또는 1년.
3. Repository access: 반드시 **Only select repositories** → `claude-discord-assistant`와 비서가 볼 내 저장소들을 골라요. "Public repositories"로 두면 비공개 저장소에서 404가 나요.
4. Repository permissions

| 권한 | 수준 | 쓰는 곳 |
| --- | --- | --- |
| Contents | Read and write | 코드 읽기, 대시보드 게시, 자기 개선 |
| Pull requests | Read and write | 자기 개선 PR |
| Issues | Read and write | 이슈 조회·등록 |
| Actions | Read and write | 플레이테스트·워크플로 실행 |
| Metadata | Read (자동) | 기본 |

5. **Generate token** → `github_pat_…` 값을 메모장에 복사해 둬요. 이때 한 번만 보여요. 5단계에서 저장소를 받을 때와 `.env`의 `GITHUB_TOKEN`에 써요.

비서는 이 토큰의 만료일을 스스로 읽고 14·7·3·1·0일 전에 알려줘요.

## 3단계 Discord: 서버와 봇

비서와 대화할 내 서버와 봇 계정을 만들어요. 비서는 내 계정에만 응답해요.

### 서버와 채널

1. 디스코드 왼쪽 **+** → **직접 만들기** → 나와 친구들을 위한 서버 → 이름 정하기.
2. 텍스트 채널 두 개를 만들어요: `#비서`(홈 채널, 대화·알림), `#결제`(13단계에서 씀).

### 봇 만들기

1. discord.com/developers/applications → **New Application** → 이름(예: 비서) → Create.
2. 왼쪽 **Bot**
   - **Reset Token** → 토큰을 메모장에 복사 (`DISCORD_TOKEN`). 다시 보려면 재발급해야 해요
   - **Public Bot** 끄기
   - Privileged Gateway Intents에서 **Message Content Intent** 켜기 → Save Changes
3. 왼쪽 **OAuth2** → **URL Generator**
   - Scopes: `bot`
   - Bot Permissions: View Channels, Send Messages, Send Messages in Threads, Create Public Threads, Embed Links, Attach Files, Read Message History, Add Reactions. **Administrator는 고르지 않아요**
4. 맨 아래 만들어진 주소를 열어 방금 만든 서버를 고르고 봇을 추가해요.

### ID 얻기

1. 디스코드 앱 → 사용자 설정 → **고급** → **개발자 모드** 켜기.
2. 내 프로필을 우클릭(폰은 길게 누르기) → **사용자 ID 복사** → `DISCORD_OWNER_ID`.
3. `#비서` 채널을 우클릭 → **채널 ID 복사** → `DISCORD_HOME_CHANNEL_ID`.

홈 채널은 반드시 **봇을 추가한 그 서버**의 채널이어야 해요. 다른 서버의 채널 ID를 넣으면 `Unknown Channel` 오류가 나고, 채널에서 말해도 답이 없어요. 비서는 홈 채널, DM, 홈 채널 안 스레드에서 대답해요.

## 4단계 Anthropic API 키

비서의 머리인 Claude를 부르는 키예요.

1. console.anthropic.com에 로그인해요. 조직이 여러 개면 크레딧이 있는 조직을 골라요.
2. **Settings → API Keys → Create Key** → 이름 `ai-assistant` → `sk-ant-…` 값을 메모장에 복사해요 (`ANTHROPIC_API_KEY`).
3. **Billing**에 크레딧이 남아 있는지 봐요. 크레딧이 0이면 비서가 대답하지 못해요.

비서는 스스로 월 100달러 한도를 지켜요. 80%와 100%에서 알리고, 넘으면 작은 모델만 쓰는 절약 모드로 바뀌어요. 웹 검색은 하루 50회까지예요. 바꾸는 법은 14단계에 있어요.

## 5단계 비서 설치하고 처음 켜기

여기까지 하면 디스코드에서 대화하는 비서가 켜져요. 모두 VM에서 해요.

1. 저장소를 받아요. 비공개 저장소라면 Username에는 GitHub 아이디, Password에는 2단계의 토큰을 붙여 넣어요 (화면에 안 보여도 들어가요).

   ```
   sudo apt-get update && sudo apt-get install -y git
   git clone https://github.com/<내아이디>/claude-discord-assistant.git ai-assistant
   cd ai-assistant
   git config credential.helper store
   ```

   마지막 줄은 다음 `git pull`부터 토큰을 다시 묻지 않게 해줘요. `!update`가 동작하려면 필요해요.
2. 설치 스크립트를 실행해요. 파이썬 가상환경을 만들고 패키지를 설치하고, 시간대를 서울로 맞추고, `.env` 파일을 만든 뒤 멈춰요. 5~10분 걸려요.

   ```
   bash deploy/setup.sh
   ```
3. `.env`를 열어 필수 네 줄과 GitHub 토큰을 채워요. 나머지는 빈칸으로 두고 6단계부터 채워요.

   ```
   nano .env
   ```

   ```
   ANTHROPIC_API_KEY=sk-ant-...
   DISCORD_TOKEN=...
   DISCORD_OWNER_ID=...
   DISCORD_HOME_CHANNEL_ID=...
   GITHUB_TOKEN=github_pat_...
   ```

   nano에서 저장은 **Ctrl+O → Enter**, 나가기는 **Ctrl+X**예요. `=` 앞뒤에 띄어쓰기나 따옴표를 넣지 않아요.
4. 스크립트를 한 번 더 실행해요. 이번에는 비서를 systemd 서비스 `ai-assistant`로 등록하고 켜요. VM이 다시 켜져도 자동으로 올라와요.

   ```
   bash deploy/setup.sh
   journalctl -u ai-assistant -f
   ```

   로그에 로그인 성공 줄이 보이면 Ctrl+C로 로그 보기를 끝내요. 비서는 계속 돌아요.
5. 디스코드 `#비서`에서 `!help`를 치면 명령 목록이 와요. "안녕"에 대답하면 1차 완성이에요.
6. 포크한 저장소를 쓰도록 바꿔요 (`#비서`에서). 기본 설정에는 원래 저장소 주인의 값이 들어 있어요.

   ```
   !set github.repos [<내아이디>/저장소1, <내아이디>/저장소2]
   !set self_improve.repo <내아이디>/claude-discord-assistant
   !set playtest.repo <내아이디>/claude-discord-assistant
   !set pages.repo <내아이디>/claude-discord-assistant
   !set pages.base_url https://<내아이디>.github.io/claude-discord-assistant
   !restart
   ```

   `!set`으로 바꾼 값은 VM의 `config.local.yaml`에만 저장돼요. `config.yaml`을 VM에서 직접 고치면 `!update`가 충돌하니 고치지 않아요.

### 다른 방법: Docker로 설치하기 (선택)

위 2~4번 대신 Docker로 돌릴 수도 있어요. 파이썬 가상환경과 systemd를 직접 다루지 않아도 되고, 컨테이너가 꺼지면 자동으로 다시 켜져요. 메모리를 조금 더 써서, 1GB VM이면 1단계의 스왑을 꼭 만들어 두세요.

1. Docker를 설치해요 (VM에서, 한 번만).

   ```
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
   sudo usermod -aG docker $USER
   ```

   마지막 줄 뒤에는 SSH를 한 번 끊었다가 다시 접속해야 `sudo` 없이 `docker`를 쓸 수 있어요.
2. 1번처럼 저장소를 받고 `.env`를 만들어 채워요.

   ```
   cd ~/ai-assistant
   cp .env.example .env
   nano .env
   ```
3. 빌드하고 켜요. 처음 빌드는 5~10분 걸려요.

   ```
   docker compose up -d --build
   docker compose logs -f
   ```
4. 디스코드에서 `!help`로 확인해요.

| 하려는 일 | Docker에서 |
| --- | --- |
| 로그 보기 | `docker compose logs -f` |
| 재시작 | 디스코드 `!restart`, 또는 `docker compose restart` |
| 끄기 / 켜기 | `docker compose stop` / `docker compose start` |
| 업데이트 | 디스코드 `!update` (컨테이너가 알아서 다시 켜짐). `requirements.txt`나 `Dockerfile`이 크게 바뀌면 `git pull && docker compose up -d --build` |
| 구글 로그인 (7단계) | 터널을 붙여 접속한 뒤 `docker compose run --rm -p 127.0.0.1:8765:8765 -e OAUTH_BIND_ADDR=0.0.0.0 assistant python deploy/google_auth.py` (유튜브는 끝에 `--youtube`) |
| MS·카카오 로그인 (8·10단계) | `docker compose run --rm assistant python deploy/ms_auth.py`, `docker compose run --rm assistant python deploy/kakao_auth.py` |
| 백업 복구 | `docker compose stop && docker compose run --rm assistant python deploy/restore.py --latest && docker compose start` |

이 문서의 다른 단계에서 `.venv/bin/python deploy/…`라고 나오면, Docker에서는 `docker compose run --rm assistant python deploy/…`로 바꿔 실행해요. `sudo systemctl …` 명령은 위 표의 Docker 명령으로 바꿔요. 코드·`.env`·`data/`·`config.local.yaml`은 컨테이너 안이 아니라 저장소 폴더에 그대로 있어요.

### 이후 키를 추가할 때마다

6단계부터는 매번 같은 패턴이에요. VM에서 `nano ~/ai-assistant/.env`로 값을 넣고, 디스코드에서 `!restart` 하거나 VM에서 재시작해요.

```
sudo systemctl restart ai-assistant
```

## 6단계 Gmail

비서가 메일을 읽고 중요한 메일을 알려주고 답장 초안을 만들어요. **읽기만** 하고, 읽음 표시도 바꾸지 않고, 메일을 보내지 않아요.

1. myaccount.google.com → **보안** → **2단계 인증**을 켜요. 앱 비밀번호는 2단계 인증이 켜져 있어야 만들 수 있어요.
2. 같은 화면 위쪽 검색창에 **앱 비밀번호** 검색 → 앱 이름 `ai-assistant` → **만들기**.
3. Gmail 설정 → 전달 및 POP/IMAP → **IMAP 사용**이 켜져 있는지 봐요.
4. 나온 16자리를 띄어쓰기 없이 VM `.env`에 넣어요.

   ```
   GMAIL_ADDRESS=내메일@gmail.com
   GMAIL_APP_PASSWORD=abcdefghijklmnop
   ```
5. `!restart` → 디스코드에서 "오늘 온 메일 요약해줘"로 확인해요.

구글 비밀번호를 바꾸면 앱 비밀번호도 무효가 돼요. 그때 새로 만들어 교체해요.

## 7단계 Google Cloud (캘린더·드라이브·생일·유튜브·시트)

구글 캘린더 일정 읽기·추가, 드라이브 검색·백업, 주소록 생일, 유튜브 구독 새 영상, 지출 시트를 쓰려면 OAuth 로그인이 필요해요. 토큰은 두 개를 받아요. 구글이 유튜브 권한을 다른 권한과 함께 요청하지 못하게 해서예요.

### 개인정보처리방침 페이지 먼저 만들기

구글 동의 화면에 홈페이지와 개인정보처리방침 주소가 있어야 저장돼요.

1. Notion 등에 "ai-assistant 개인정보처리방침" 페이지를 만들고 "개인용 비서이며 데이터는 본인 서버에만 저장하고 제3자에게 주지 않는다"는 내용을 적어요.
2. 웹에 공개 게시하고 주소를 복사해요 (Notion: 공유 → 게시 → 웹에 게시).

### 콘솔 준비 (PC 브라우저)

1. console.cloud.google.com → 위쪽 프로젝트 선택 → **새 프로젝트** → 이름 `ai-assistant` → 만들기.
2. **API 및 서비스 → 라이브러리**에서 다섯 개를 하나씩 검색해 **사용**을 눌러요.
   - Google Calendar API
   - Google Drive API
   - People API
   - YouTube Data API v3
   - Google Sheets API
3. **Google 인증 플랫폼**(OAuth 동의 화면) → 시작하기
   - 앱 이름 `ai-assistant`, 지원 이메일은 내 Gmail
   - 대상: **외부**
   - 연락처 이메일 → 동의 → 만들기
4. **브랜딩** 탭: 홈페이지와 개인정보처리방침 주소에 위에서 복사한 주소를 넣고 저장.
5. **대상** 탭: 테스트 사용자에 내 Gmail 추가 → **앱 게시**(프로덕션으로 전환). 테스트 상태로 두면 토큰이 7일마다 만료돼요. 나만 쓰므로 검수는 받지 않아도 돼요.
6. **클라이언트** 탭 → **클라이언트 만들기** → 유형 **데스크톱 앱** → 만들기 → **JSON 다운로드**.
7. JSON을 VM으로 복사해요 (PC PowerShell, 다운로드 폴더에서).

   ```
   scp -i "$env:USERPROFILE\.ssh\oracle.key" .\client_secret_*.json ubuntu@<공인 IP>:~/ai-assistant/data/client_secret.json
   ```

### 로그인 (SSH 터널)

VM에는 브라우저가 없어서, PC 브라우저가 VM의 8765번 포트로 이어지게 접속해요.

1. PC에서 터널을 붙여 접속해요.

   ```
   ssh -i "$env:USERPROFILE\.ssh\oracle.key" -L 8765:localhost:8765 ubuntu@<공인 IP>
   ```
2. 그 창에서 기본 토큰을 받아요.

   ```
   cd ~/ai-assistant && .venv/bin/python deploy/google_auth.py
   ```
3. 출력된 주소를 PC 브라우저에 붙여 넣고 로그인해요. "확인되지 않은 앱"이 뜨면 **고급 → ai-assistant(으)로 이동**, 권한은 모두 체크하고 계속. "완료"가 뜨면 `data/google_token.json`이 생겨요.
4. 같은 창에서 유튜브 토큰을 따로 받아요. 결과는 `data/google_youtube_token.json`이에요.

   ```
   .venv/bin/python deploy/google_auth.py --youtube
   ```
5. `sudo systemctl restart ai-assistant` → 디스코드에서 "이번 주 일정 알려줘", `!yt`, `!birthdays`로 확인해요.

| 받은 권한 | 쓰는 기능 |
| --- | --- |
| 캘린더 일정 읽기·쓰기 | 일정 조회·추가, 아침 브리핑, 출발 알림 |
| 드라이브 읽기 전용 | 드라이브 검색 |
| 드라이브 drive.file | 백업, 지출 시트 (비서가 만든 파일만 수정) |
| 연락처 읽기 | 생일·기념일 알림 (매일 08:07) |
| 유튜브 읽기 | 구독 채널 새 영상 요약 (매일 19:00) |

### 로그인이 실패할 때

| 증상 | 해결 |
| --- | --- |
| `Address already in use` | 이전 시도가 8765번 포트를 잡고 있어요. `sudo fuser -k -9 8765/tcp` 후 다시 |
| PC 창에 `channel 3: open failed` | 스크립트가 안 돌고 있어요. 2번을 실행해 둔 채로 주소를 열어요 |
| `scopes cannot be requested together` | 유튜브는 `--youtube`로 따로 받아요 |
| 브랜딩 저장 안 됨 | 홈페이지·개인정보처리방침 주소를 넣어요 |

## 8단계 Microsoft To Do와 갤럭시 리마인더

비서에게 말한 할 일이 폰의 삼성 리마인더에 뜨고, 폰에서 완료하면 비서도 알아요. 삼성 리마인더 ↔ Microsoft To Do ↔ 비서 순서로 이어져요. 갤럭시가 아니어도 Microsoft To Do 앱으로 같은 효과를 낼 수 있어요.

### 폰

1. Microsoft 계정이 없으면 account.microsoft.com에서 만들어요.
2. 삼성 리마인더 앱 → ≡ → 설정 → **Microsoft To Do와 동기화** → 그 계정으로 로그인. 목록은 기본 "작업"을 써요.

### Azure 앱 등록 (PC 브라우저)

1. portal.azure.com에 같은 Microsoft 계정으로 로그인 → 검색창에 **앱 등록** → **새 등록**.
2. 이름 `ai-assistant`, 지원되는 계정 유형 **개인 Microsoft 계정만** → 등록. 리디렉션 URI는 비워 둬요.
3. **인증** → 고급 설정 → **퍼블릭 클라이언트 흐름 허용: 예** → 저장.
4. **API 권한** → 권한 추가 → Microsoft Graph → 위임된 권한 → `Tasks.ReadWrite`, `offline_access` 체크 → 추가.
5. **개요**의 **애플리케이션(클라이언트) ID**를 VM `.env`에 넣어요.

   ```
   MS_CLIENT_ID=복사한 ID
   MS_TENANT=consumers
   ```

### 로그인 (VM, 터널 필요 없음)

1. VM에서 실행해요.

   ```
   cd ~/ai-assistant && .venv/bin/python deploy/ms_auth.py
   ```
2. 화면의 주소를 폰이나 PC에서 열고 코드를 입력 → **리마인더와 연결한 같은 계정**으로 로그인 → 승인.
3. "목록: 작업 (기본)"이 보이고 `data/ms_token.json`이 생기면 재시작해요. 동기화한 목록이 기본 목록이 아니면 `!set todo.list_name 목록이름`.
4. 디스코드에서 "내일 9시에 우유 사기 알려줘" → 몇 분 뒤 폰 리마인더에 뜨면 성공이에요.

토큰은 비서가 자동으로 갱신해요. 90일 넘게 안 쓰면 만료되고, 그때는 1번부터 다시 해요. 요금은 없어요.

## 9단계 Notion: 메모·지출·나중에 읽기·독서

비서는 Notion에 메모와 기록을 남겨요. 통합(비서의 Notion 계정 같은 것)을 만들고, 페이지 하나와 그 아래 데이터베이스 3개를 만들어 연결해요.

### 통합 만들기

1. notion.so/my-integrations → **새 통합** → 이름 `ai-assistant`, 유형 **내부**, 워크스페이스 선택 → 저장.
2. **내부 통합 시크릿**을 보기 → 복사 → VM `.env`의 `NOTION_TOKEN`에 넣어요.

### 페이지와 DB 만들기

1. Notion에 새 페이지 **비서 메모**를 만들어요.
2. 그 페이지 안에서 `/데이터베이스` → **데이터베이스 - 인라인**을 세 번 만들고, 아래 표대로 이름과 속성을 맞춰요. **속성 이름이 한 글자라도 다르면 기록이 실패해요.** 기본 "이름" 속성은 표의 제목 속성 이름으로 바꿔요.

| DB 이름 | 속성 (유형) |
| --- | --- |
| 지출 | 내용 (제목), 날짜 (날짜), 금액 (숫자), 분류 (선택), 가게 (텍스트), 결제수단 (텍스트), 메모 (텍스트) |
| 나중에 읽기 | 제목 (제목), URL (URL), 요약 (텍스트), 종류 (선택), 태그 (다중 선택), 읽음 (체크박스), 저장일 (날짜) |
| 독서 | 제목 (제목), 저자 (텍스트), 출판사 (텍스트), ISBN (텍스트), 상태 (선택), 기록일 (날짜), 메모 (텍스트), 표지 (URL), 링크 (URL) |

선택 속성의 값은 비서가 쓸 때 자동으로 생겨요. 미리 만들고 싶다면 이 값들이에요.

- 지출 › 분류: 식비, 카페, 교통, 쇼핑, 생활, 의료, 문화, 기타
- 나중에 읽기 › 종류: 글, 영상, 문서, 기타 / 태그: `assistant/readlater.py`의 `TAGS`에 적힌 값 (내 관심사로 바꿔 쓰세요)
- 독서 › 상태: 읽고 싶음, 읽는 중, 완독, 중단

### 연결하고 ID 넣기

1. **비서 메모** 페이지 오른쪽 위 **··· → 연결 → ai-assistant**. 아래 DB 3개도 같이 연결돼요.
2. ID를 모아요. 페이지나 DB를 전체 화면으로 열고 **링크 복사** → 주소의 `?` 앞 32자리(숫자와 영문)가 ID예요.
3. 디스코드로 비서에게 알려줘요.

   ```
   !set notion.memo_parent_page_id 비서메모ID
   !set notion.expense_database_id 지출ID
   !set notion.readlater_database_id 나중에읽기ID
   !set notion.books_database_id 독서ID
   !restart
   ```
4. 확인: "점심 9000원 식비로 기록해줘" → 지출 DB에 한 줄이 생기면 돼요. `!spend undo`로 지워요.

`notion.devlog_database_id`는 개발 일지 DB용 항목이에요. 쓰지 않으면 `!set notion.devlog_database_id ""`로 비워 둬요.

## 10단계 카카오

카카오 앱 하나로 나에게 보내기, 장소 검색, 출발 알림 길찾기, 다음 검색(블로그·카페·책), 웹 카드 카톡 공유, 톡캘린더를 모두 써요.

### 앱 만들기 (developers.kakao.com)

1. 카카오 계정으로 로그인 → **내 애플리케이션** → **애플리케이션 추가** → 앱 이름 `ai-assistant`, 회사명은 본인 이름.
2. **카카오 로그인** → 활성화 **ON**.
3. **카카오 로그인 → 동의항목**에서 두 개를 선택 동의로 켜요.
   - 카카오톡 메시지 전송 (`talk_message`)
   - 톡캘린더 및 일정 생성, 조회, 편집/삭제 (`talk_calendar`)
4. **플랫폼 키 → REST API 키** → 리다이렉트 URI에 `https://localhost` 등록.
5. **보안(클라이언트 시크릿)** → 코드 생성 → 사용함. 시크릿을 틀리게 넣으면 `KOE010` 오류가 나요.
6. **카카오맵** → 사용 설정 **ON**. 출발 알림의 대중교통·자동차 길찾기에 필요해요 (무료 한도: 대중교통 하루 1,000건, 자동차 10,000건).
7. **JavaScript 키** → **JavaScript SDK 도메인**에 `https://<내아이디>.github.io` 등록. **제품 링크 관리 → 웹 도메인**에도 같은 주소를 등록해요. 웹 카드의 카톡 공유 버튼에 필요해요.
8. VM `.env`에 넣어요.

   ```
   KAKAO_REST_API_KEY=REST API 키
   KAKAO_CLIENT_SECRET=클라이언트 시크릿
   KAKAO_JS_KEY=JavaScript 키
   ```

### 로그인 토큰 받기 (VM)

1. VM에서 실행해요.

   ```
   cd ~/ai-assistant && .venv/bin/python deploy/kakao_auth.py
   ```
2. 출력된 주소를 폰이나 PC 브라우저로 열고 모두 동의해요.
3. `https://localhost/?code=…`로 이동하고 페이지가 안 열려요. 정상이에요. **주소창의 주소 전체**를 복사해 터미널에 붙여 넣고 Enter.
4. "허락된 권한"에 `talk_message`와 `talk_calendar`가 보이고 `data/kakao.json`이 생기면 재시작해요.
5. 확인: "이거 카톡으로 보내줘: 테스트" → 카카오톡 나와의 채팅에 오면 돼요.

이 토큰은 비서가 쓸 때마다 자동으로 갱신해요. 톡캘린더 연동은 기본으로 꺼져 있고, 14단계에서 켜요.

## 11단계 GitHub Pages·Secrets·Actions

웹 카드·대시보드 게시, 플레이테스트, 결제 문자 앱 빌드는 저장소에서 돌아요.

### Pages 켜기 (웹 카드·대시보드)

1. 저장소에 `gh-pages` 브랜치가 생기도록 한 번 돌려요. 저장소 → **Actions** → `pages` 워크플로 → **Run workflow**. 포크했다면 Actions 탭에서 먼저 **워크플로 사용**을 눌러야 해요.
2. 저장소 → **Settings → Pages** → Source **Deploy from a branch** → Branch `gh-pages`, 폴더 `/ (root)` → Save.
3. 몇 분 뒤 `https://<내아이디>.github.io/claude-discord-assistant`가 열리면 돼요. `site/` 폴더만 공개되고, 카드 내용은 링크의 `#` 뒤에만, 대시보드 데이터는 암호문으로만 올라가요.
4. 디스코드에서 `!dash` → 링크가 열리면 성공이에요. 404가 나면 2단계 토큰의 Repository access와 Contents 쓰기 권한을 확인해요.

### Secrets 넣기

저장소 → **Settings → Secrets and variables → Actions → New repository secret**.

| 이름 | 값 | 쓰는 곳 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | 4단계의 키 | 플레이테스트 |
| `DISCORD_WEBHOOK_URL` | `#비서` 채널 웹후크 주소 (채널 편집 → 연동 → 웹후크 → 새 웹후크 → URL 복사) | 플레이테스트 결과 알림 |

### Actions

| 워크플로 | 도는 때 | 하는 일 |
| --- | --- | --- |
| `test` | 코드가 바뀔 때 | 오프라인 테스트 |
| `pages` | 코드가 바뀔 때 | `site/` → `gh-pages` 게시 |
| `playtest` | `!playtest` | AI가 웹 게임을 해 보고 결과를 디스코드로 (`!set playtest.url 게임주소`) |
| `android` | `android/` 폴더가 바뀔 때 | 결제 문자 앱 APK → Releases `paysms-app` |

비공개 저장소는 Actions 무료 시간이 있어요. 결제 차단으로 안 돌면 github.com → Settings → **Billing and licensing → Budgets**에서 Actions 예산을 올려요. 자기 개선 PR은 매주 일요일 밤에 올라오고, 자동 병합하지 않으니 직접 보고 병합해요.

## 12단계 공공데이터포털과 healthchecks.io

### 공공데이터포털 (부산 버스 도착·기상특보)

부산 버스 정보는 부산 전용이에요. 다른 지역이면 기상특보만 신청해도 돼요.

1. data.go.kr 회원가입 → 로그인.
2. 검색창에서 두 API를 찾아 각각 **활용신청**해요. 활용목적은 "개인 비서 프로그램"으로 적으면 돼요. 보통 바로 승인돼요.
   - 부산광역시_부산버스정보시스템
   - 기상청_기상특보 조회서비스
3. **마이페이지 → 데이터 활용 → 인증키 발급현황**에서 **일반 인증키(Decoding)**를 복사해 VM `.env`에 넣어요.

   ```
   DATA_GO_KR_KEY=복사한 키
   ```
4. 재시작 후 디스코드에서 `!bus 정류장 이름`으로 확인해요. 승인 직후에는 키가 퍼지는 데 한두 시간 걸릴 수 있어요.

날씨·파도는 키 없이 동작해요. 기준 위치는 `!set busan.place 동네이름`으로 바꿔요. 활용기간은 API마다 정해져 있어요. 마이페이지에서 만료일을 보고 끝나기 전에 연장 신청해요.

### healthchecks.io (비서 생존 감시)

VM이 꺼지면 비서는 스스로 알릴 수 없어요. 비서가 5분마다 신호를 보내고, 끊기면 healthchecks.io가 디스코드로 알려줘요.

1. healthchecks.io 무료 가입 → **Add Check** → 이름 `ai-assistant` → Schedule에서 **Period 5분, Grace 10분**.
2. **Integrations** → **Discord** → Add Integration → 디스코드 화면에서 서버와 `#비서` 채널 선택 → 승인.
3. 체크 화면의 **Ping URL**(`https://hc-ping.com/…`)을 VM `.env`에 넣고 재시작해요.

   ```
   HEALTHCHECK_URL=https://hc-ping.com/...
   ```
4. 5분 안에 체크 상태가 **up**(초록)이 되면 돼요.

## 13단계 결제 문자 자동 기록

카드로 결제하면 지출이 Notion에 자동으로 기록돼요. 9단계(지출 DB)가 먼저 돼 있어야 해요. 안드로이드 폰 전용이에요.

1. **카드사 승인 문자** → 폰 메시지 앱 알림
2. **결제 문자 전달 앱**이 카드 결제 문자만 골라 웹후크로 전송
3. **#결제 채널**에 문자가 올라옴
4. **비서**가 금액·가맹점을 읽어 Notion 지출에 기록하고 기록 카드를 남김

### 카드사 알림을 문자로 바꾸기

각 카드사 앱에서 승인 알림 수신 방법을 **문자(SMS)**로 바꿔요. 국내 카드사는 건별 승인 메일이 거의 없고, 문자는 월 수수료(보통 300원)가 있어요.

### 디스코드 채널과 웹후크

1. `#결제` 채널 → 채널 편집 → **연동 → 웹후크 → 새 웹후크** → **웹후크 URL 복사**. 비공개 채널이면 채널 권한에 비서를 추가해요.
2. URL은 `https://discord.com/api/webhooks/숫자/토큰` 모양이에요. **숫자**가 웹후크 ID예요. 전체 URL은 폰 앱에만 넣고 어디에도 붙여 넣지 않아요.
3. `#결제` 채널 우클릭 → **채널 ID 복사**.
4. `#비서`에서 비서를 켜요.

   ```
   !set paysms.channel_id 채널ID
   !set paysms.webhook_id 웹후크ID
   !set paysms.enabled true
   !restart
   !pay
   ```

   `!pay`가 "켜짐"으로 나오면 돼요.

### 전달 앱 설치 (PC에서 USB로)

앱은 저장소 `android/` 폴더에 있고, GitHub Actions가 APK로 만들어 Releases에 올려요. 폰에서 바로 설치하면 Play 프로텍트가 막아서 PC에서 USB로 설치해요.

1. PC 브라우저로 `github.com/<내아이디>/claude-discord-assistant/releases/tag/paysms-app` → 번호가 가장 큰 `paysms-번호.apk`를 받아요. 파일은 17KB 정도예요. 포크 직후라 Release가 없다면 Actions의 `android` 워크플로를 **Run workflow**로 한 번 돌려요.
2. adb를 받아요 (PC PowerShell). winget은 `Installer hash does not match`로 실패할 수 있어서 구글에서 직접 받아요.

   ```
   Invoke-WebRequest "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" -OutFile "$env:TEMP\platform-tools.zip"
   Expand-Archive "$env:TEMP\platform-tools.zip" -DestinationPath "$env:USERPROFILE\Desktop" -Force
   cd "$env:USERPROFILE\Desktop\platform-tools"
   ```
3. 받은 APK를 바탕화면의 `platform-tools` 폴더로 옮겨요.
4. 폰: 설정 → 휴대전화 정보 → 소프트웨어 정보 → **빌드번호 7번** 터치 → 설정 → 개발자 옵션 → **USB 디버깅** 켜기.
5. USB로 연결 → 폰에 뜨는 "USB 디버깅을 허용하시겠습니까?"에서 허용.
6. 같은 PowerShell에서 설치해요.

   ```
   .\adb.exe devices
   .\adb.exe install paysms-1.apk
   ```

   `devices`에 `device`가 보이고 `install`에 `Success`가 나오면 돼요. `unauthorized`면 폰의 허용 창을 아직 안 누른 거예요.
7. **USB 디버깅을 다시 꺼요.**

새 버전을 깔 때는 기존 앱을 지우고 설치해요. 서명 키가 빌드마다 달라서예요. 지우면 웹후크 주소를 다시 넣어야 해요. 지우지 않고 업데이트하고 싶으면 서명 키를 만들어 저장소 Secrets `PAYSMS_KEYSTORE_B64`(키스토어 파일 base64), `PAYSMS_KEYSTORE_PASSWORD`에 넣어요.

### 앱 설정 (화면 위에서부터)

앱 이름은 "결제 문자 전달"이에요.

1. **① 알림 접근 권한 설정 열기** → "결제 문자 전달" 허용. "제한된 설정"으로 막히면 앱 아이콘을 길게 눌러 앱 정보 → 오른쪽 위 ⋮ → **제한된 설정 허용**을 먼저 해요.
2. **② 배터리 사용 제한 풀기** → 앱 정보 → 배터리 → **제한 없음**. 안 하면 며칠 뒤 멈춰요.
3. **③ 웹후크 주소** 붙여 넣기 → 주소 저장. 화면에는 끝 4글자만 보여요.
4. **④ 테스트 보내기** → `#결제`에 글이 오고 비서가 👀를 붙여요.
5. **결제 문자 예시로 테스트** → 비서가 1,000원 기록 카드를 붙여요. **기록 지우기**로 지워요.

앱은 삼성 메시지·구글 메시지 앱의 알림만 읽고, 카드사 이름 + 승인/취소 + 금액이 모두 있는 문자만 보내요. 다른 문자는 폰 밖으로 나가지 않아요. 못 보낸 문자는 3일까지 보관했다가 다시 보내요.

### 기록 규칙

| 상황 | 비서가 하는 일 |
| --- | --- |
| 승인 문자 | 바로 기록. 버튼은 고칠 때만 눌러요 |
| 분류 바꾸기를 누름 | 그 가맹점은 다음부터 바꾼 분류로 기록 |
| 같은 금액이 10분 안에 또 옴 | 기록하지 않고 [기록]/[무시]를 물음. [기록]을 눌러야 저장 |
| 똑같은 글이 다시 옴 | 조용히 넘김 |
| 취소 문자 | 45일 안의 같은 금액 기록을 찾아 지움 |
| 결제예정·광고·인증번호 | 무시하고 👀만 남김 |
| 해외 결제(원화 없음) | 기록하지 않음 |

카드 버튼은 24시간이 지나거나 비서가 재시작되면 눌리지 않아요. 그 뒤에는 Notion에서 직접 고치거나, 방금 건이면 `!spend undo`로 지워요. 받은 문자를 `!pay test 문자 내용`으로 붙이면 기록하지 않고 어떻게 읽는지만 보여줘요.

## 14단계 디스코드에서 마무리 설정

키를 다 넣었으면 `#비서`에서 한 번씩 해 두는 설정이에요. `!set`으로 바꾼 값은 VM의 `config.local.yaml`에만 저장되고, `!restart` 후 적용돼요.

| 할 일 | 명령 | 쓰는 기능 |
| --- | --- | --- |
| 집·회사 주소 등록 | `!place 집 주소`, `!place 회사 주소` | 출발 알림 (평일 09~18시는 회사, 그 외 집에서 출발) |
| 톡캘린더 켜기 | `!set talkcal.enabled true` | 구글 일정을 카톡 캘린더로, 카톡 일정을 브리핑에 |
| 날씨 기준 위치 | `!set busan.place 해운대` | 날씨·파도·특보 (기본 부산시청) |
| 월 예산 | `!set budget.monthly_usd 100` | Claude 비용 상한 |
| 하루 웹 검색 | `!set budget.daily_web_searches 50` | 검색 비용 상한 |
| 중요 메일 보낸 사람 | `!set mail.vip_senders [boss@company.com]` | 항상 중요로 알림 |
| 재발급 날짜 기록 | `!renewed 키 YYYY-MM-DD` | `config.yaml`의 `renewals.items`에 적은 항목의 재발급 알림 |

모두 입력했으면 `!restart`를 한 번 해요. `!config`로 바꾼 값을, `!renewals`로 재발급 일정을 확인해요.

### 자동으로 도는 일정

| 시각 | 하는 일 |
| --- | --- |
| 04:37 | Notion 지출 → 구글 시트 동기화 |
| 07:47 | 아침 브리핑 |
| 08:07 | 생일·기념일 |
| 09:07 | 토큰·재발급 점검 |
| 12:30, 18:30 | 모아 둔 알림 요약 |
| 19:00 | 유튜브 구독 새 영상 |
| 21:07 | 하루치 메일 요약 |
| 일요일 21:07 | 나의 한 주 |
| 일요일 22:37 | 자기 개선 PR |
| 23:00~07:00 | 조용한 시간 (급한 알림만) |

여기까지 하면 설정은 끝이에요. 기능별 사용법은 [usage.md](usage.md)나 디스코드의 `!help 주제`(예: `!help 결제 문자`)로 볼 수 있어요.

## 운영: 업데이트, 재발급, 문제 해결

### 업데이트와 재시작

| 하려는 일 | 방법 |
| --- | --- |
| 최신 코드 받기 | 디스코드 `!update` (git pull 후 재시작) |
| 재시작 | 디스코드 `!restart`, 또는 VM `sudo systemctl restart ai-assistant` |
| 상태 보기 | VM `sudo systemctl status ai-assistant` |
| 로그 보기 | VM `journalctl -u ai-assistant -n 50` (실시간은 `-f`) |
| VM이 꺼져 있음 | Oracle 콘솔 → Compute → Instances → Start |
| 백업에서 복구 | `sudo systemctl stop ai-assistant && .venv/bin/python deploy/restore.py --latest && sudo systemctl start ai-assistant` |

포크한 저장소라면 원래 저장소의 새 기능은 내 저장소 화면의 **Sync fork**로 받은 뒤 `!update` 해요. VM에서 `config.yaml`을 직접 고치지 않아요. 이미 고쳐서 충돌했다면 VM에서 `cd ~/ai-assistant && git checkout -- config.yaml && git pull` 후 `!set`으로 다시 넣어요.

### 만료와 재발급

비서가 매일 09:07에 점검하고 14·7·3·1·0일 전에 디스코드로 알려줘요.

| 항목 | 만료 | 재발급 |
| --- | --- | --- |
| GitHub 토큰 | 만들 때 정한 날 | 2단계대로 새로 만들어 `.env` 교체 |
| 구글 토큰 2개 | 프로덕션이면 사실상 없음 | 7단계 로그인 다시 |
| Microsoft 토큰 | 90일 미사용 시 | 8단계 로그인 다시 |
| 카카오 토큰 | 쓸 때마다 자동 갱신 | 실패 알림이 오면 10단계 로그인 다시 |
| Gmail 앱 비밀번호 | 구글 비밀번호를 바꿀 때 | 6단계 다시 |
| 공공데이터 키 | API별 활용기간 | 마이페이지에서 연장 신청 |
| Anthropic·Notion·Discord 키 | 없음 | 유출 시 해당 콘솔에서 재발급 |
| 대시보드 링크 | 없음 | 새어 나가면 `!dash reset` |
| 웹후크 주소 | 없음 | 새어 나가면 채널 편집에서 지우고 새로 만들기 |

재발급한 뒤에는 꼭 재시작하고, 날짜로 관리하는 항목은 `!renewed 키 날짜`로 기록해요.

### 자주 만나는 문제

| 증상 | 원인과 해결 |
| --- | --- |
| SSH `UNPROTECTED PRIVATE KEY FILE` | 키 파일 권한. 1단계의 `icacls` 세 줄 |
| SSH `Permission denied (publickey)` | 키 파일 경로나 권한, 사용자 이름 `ubuntu` 확인 |
| 채널에서 말해도 답이 없음 | `DISCORD_HOME_CHANNEL_ID`가 봇이 없는 서버의 채널. 로그에 `Unknown Channel` |
| `!dash`가 GitHub 404 | 토큰이 Public repositories로 돼 있거나 `pages.repo`가 내 저장소가 아님 |
| `!update` 실패 | VM에서 `config.yaml`을 고쳤거나 git 토큰이 저장 안 됨. 5단계 1번의 `credential.helper` |
| "톡캘린더를 못 불러옴" | `talkcal.enabled`가 꺼져 있음. 14단계 |
| 구글 로그인 오류 | 7단계 "로그인이 실패할 때" 표 |
| 카카오 `KOE010` | 클라이언트 시크릿이 틀림. `.env`의 `KAKAO_CLIENT_SECRET` 확인 |
| 지출 기록 실패 | Notion DB 속성 이름이 9단계 표와 다르거나 통합이 연결 안 됨 |
| APK 설치를 Play 프로텍트가 막음 | 13단계의 USB(adb) 설치 |
| 결제했는데 기록이 없음 | 앱 "최근 기록"에 줄이 없으면 알림 접근·배터리 설정, 있으면 `!pay`와 `paysms` 값 |
| 👀만 붙고 기록 안 됨 | 비서가 결제 문자로 못 읽음. 그 문자를 `!pay test`로 확인 |
| 비서가 아예 조용함 | healthchecks 알림을 확인하고 VM 상태와 로그를 봐요 |

## 그만 쓰기: 잠시 멈추기와 완전히 정리하기

### 잠시 멈추기

| 하려는 일 | 방법 |
| --- | --- |
| 비서 끄기 | VM에서 `sudo systemctl stop ai-assistant` (다시 켜기는 `start`). Docker는 `docker compose stop` |
| VM을 다시 켜도 안 켜지게 | `sudo systemctl disable ai-assistant` (되돌리기는 `enable`) |
| Claude 비용만 막기 | Anthropic Console → API Keys에서 비서 키 비활성화 |
| 기능 하나만 끄기 | `!set 기능.enabled false` → `!restart`. 끌 수 있는 기능: `paysms`, `talkcal`, `birthdays`, `youtube`, `expense_sheet`, `commute`, `briefing`, `self_improve`, `todo` |

비서를 끄면 healthchecks.io가 "down" 알림을 보내요. 오래 끌 거면 healthchecks.io에서 그 체크를 **Pause** 해 두세요.

### 완전히 정리하기

위에서부터 순서대로 하면 돼요. 쓰지 않은 서비스는 건너뛰어요. 메뉴 이름은 각 서비스가 바꿀 수 있어요.

1. **백업이 필요하면 먼저 받아요.** 디스코드 `!backup` → 구글 드라이브에 저장돼요. Notion 기록은 Notion에 그대로 남아요.
2. **비서를 끄고 다시 켜지지 않게 해요.**

   ```
   sudo systemctl disable --now ai-assistant
   ```

   Docker로 설치했다면 `docker compose down`이에요.
3. **요금이 나가는 것부터 해지해요.**

| 서비스 | 해지·삭제 방법 | 안 하면 |
| --- | --- | --- |
| 카드사 승인 문자 | 각 카드사 앱 → 카드 이용 알림 → 문자(SMS) 해지. 무료인 앱 푸시로 바꿔도 돼요 | 월 요금이 계속 나가요 |
| Anthropic | Console → API Keys → 비서 키 **Delete**. 비서 전용 워크스페이스를 만들었다면 그것도 보관 처리 | 키가 새면 요금이 나갈 수 있어요 |
| GitHub Actions 예산 | 예산을 올려 뒀다면 Settings → Billing and licensing → Budgets에서 되돌리기 | 공개 저장소면 상관없어요 |

4. **각 서비스의 연결을 끊어요.**

| 서비스 | 연결 끊기 |
| --- | --- |
| Discord | 개발자 포털 → 내 앱 → 맨 아래 **Delete App**. `#비서`·`#결제` 채널 편집 → 연동 → 웹후크 삭제 |
| Gmail | myaccount.google.com → 보안 → 앱 비밀번호 → ai-assistant 삭제 |
| Google (OAuth) | myaccount.google.com → 보안 → 서드 파티 앱 및 서비스 → ai-assistant → **모든 액세스 삭제**. Cloud 콘솔의 프로젝트도 지우려면 IAM 및 관리자 → 설정 → 종료 |
| Microsoft | account.microsoft.com → 개인 정보 → 앱 및 서비스의 액세스 권한에서 ai-assistant 제거. portal.azure.com → 앱 등록 → ai-assistant → 삭제. 삼성 리마인더의 To Do 동기화는 원하면 끄기 |
| Notion | 비서 메모 페이지 ··· → 연결 → ai-assistant 연결 해제. notion.so/my-integrations에서 통합 삭제. 페이지와 DB 내용은 남아요 |
| 카카오 | 카카오톡 → 설정 → 카카오계정 → 연결된 서비스 관리 → ai-assistant 연결 끊기. developers.kakao.com → 내 애플리케이션 → 앱 삭제. 톡캘린더에 복사된 일정은 남아요 |
| GitHub | Settings → Developer settings → Fine-grained tokens → 비서 토큰 삭제. 저장소 Settings → Secrets 삭제, Pages 끄기. 저장소 자체는 보관(Archive)하거나 삭제 |
| 공공데이터포털 | 마이페이지 → 데이터 활용 → 활용신청 현황에서 해지 (요금은 없어요) |
| healthchecks.io | 체크 삭제 (안 지우면 "down" 알림이 계속 와요). 계정은 Account Settings에서 삭제 |
| 폰 | 결제 문자 전달 앱 삭제. 알림 접근 권한도 같이 사라져요 |

5. **VM과 데이터를 지워요.** Oracle 콘솔 → Compute → Instances → 인스턴스 → **Terminate** → "부트 볼륨 영구 삭제"에 체크. VM 안의 `.env`, 토큰, 대화 기록, 서재 파일이 모두 지워지고 되돌릴 수 없어요. VCN 같은 네트워크 자원은 남아도 요금은 없어요. Oracle 계정을 해지하려면 계정 메뉴 → 계정 해지 요청.
6. **남는 데이터를 정리해요 (선택).** 구글 드라이브 `ai-assistant-backup` 폴더, 구글 시트 "지출 (비서)", Notion 비서 메모 페이지, 카카오 톡캘린더의 복사된 일정, PC의 SSH 키 파일(`oracle.key`)과 adb 폴더.
