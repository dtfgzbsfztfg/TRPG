# 범용 TRPG 디스코드 봇 (스캐폴드)

주사위 굴리기 + 캐릭터 시트 + 전투(이니셔티브) 자동화를 갖춘 범용 TRPG 봇의 기본 뼈대입니다.
특정 시스템(D&D5e, 크툴루 등)에 종속되지 않고, `systems/*.yaml` 프로필만 추가하면 다른 시스템도 지원할 수 있게 설계했습니다.

## 폴더 구조
```
trpg_bot/
├── bot.py              # 봇 실행 진입점
├── db.py               # SQLite DB 접근 함수
├── requirements.txt
├── .env.example        # 복사해서 .env로 만들고 토큰 입력
├── cogs/
│   ├── dice.py         # /roll, /check
│   ├── character.py    # /char_create, /char_sheet, /char_set, /char_hp, /char_list, /char_delete, /check_stat
│   └── combat.py       # /combat_start, /combat_status, /combat_next, /combat_damage, /combat_end
├── systems/
│   └── generic.yaml    # 시스템 프로필 예시 (능력치, 판정 방식 정의)
└── utils/
    ├── dice.py          # 주사위 파싱/굴림 엔진
    └── systems.py       # 시스템 프로필 로더
```

## 준비물
1. Python 3.10 이상
2. [Discord Developer Portal](https://discord.com/developers/applications)에서 애플리케이션 생성 → Bot 탭에서 토큰 발급
3. Bot 탭에서 필요한 인텐트는 기본값으로 충분 (메시지 내용 인텐트는 불필요, 전부 슬래시 커맨드 기반)
4. OAuth2 → URL Generator에서 `bot`, `applications.commands` 스코프 체크 → 생성된 링크로 서버에 초대

## 설치 및 실행
```bash
cd trpg_bot
python -m venv venv
source venv/bin/activate   # Windows는 venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env 파일 열어서 DISCORD_TOKEN=발급받은토큰 입력

python bot.py
```
처음 실행하면 슬래시 커맨드가 디스코드 서버에 등록됩니다 (반영까지 최대 1시간 걸릴 수 있어요. 즉시 반영하려면 길드별 sync로 바꾸는 것도 가능).

## 사용 예시
```
/char_create name:빌런 system:generic hp:15
/char_sheet name:빌런
/char_set name:빌런 stat:str value:16
/check_stat name:빌런 stat:str
/roll expression:2d6+3 label:공격 피해
/combat_start participants:빌런:15,전사:20
/combat_status
/combat_next
/combat_damage name:빌런 delta:-5
/combat_end
```

## Railway 배포하기

이 저장소에는 배포용 파일이 이미 들어있어요: `Procfile`, `railway.json`, `.python-version`, `.gitignore`.

1. **GitHub에 올리기** (Railway는 GitHub 저장소 연동 배포가 가장 편해요)
   ```bash
   cd trpg_bot
   git init
   git add .
   git commit -m "init"
   git branch -M main
   git remote add origin <내_깃허브_저장소_URL>
   git push -u origin main
   ```
   `.env`는 `.gitignore`에 있어서 올라가지 않아요. 토큰은 절대 커밋하지 마세요.

2. **Railway에서 프로젝트 생성**
   - [railway.app](https://railway.app) 로그인 → New Project → Deploy from GitHub repo → 방금 올린 저장소 선택
   - Railway가 `railway.json`을 보고 Nixpacks 빌더로 자동 빌드하고, `python bot.py`로 실행합니다.

3. **환경변수 설정** (Railway 프로젝트 → Variables 탭)
   | 변수 | 값 |
   |---|---|
   | `DISCORD_TOKEN` | 디스코드 봇 토큰 |
   | `DB_PATH` | `/data/trpg.db` (아래 볼륨 설정과 짝을 맞춰야 함) |

4. **볼륨(Volume) 연결 — 꼭 하세요**
   Railway 컨테이너는 재배포/재시작 시 파일시스템이 초기화될 수 있어서, SQLite 파일을 그냥 두면
   캐릭터 데이터가 날아갑니다. Railway 프로젝트 → 서비스 → **Volumes** 탭에서:
   - Mount path: `/data`
   - 위에서 설정한 `DB_PATH=/data/trpg.db` 와 경로를 맞춰주세요.

5. **배포 확인**
   - Deployments 탭에서 로그를 보면 `✅ 로그인 완료: ...` 메시지가 뜨면 정상 기동된 것입니다.
   - 슬래시 커맨드가 서버에 바로 안 보이면 디스코드 클라이언트를 껐다 켜거나 최대 1시간 정도 기다려주세요.

6. **주의: 실행 개수는 항상 1개로 유지**
   - Railway에서 Replica(복제본)를 2개 이상으로 늘리면 같은 봇 토큰으로 두 프로세스가 동시에
     디스코드에 연결을 시도해 오류가 나거나 명령이 중복 응답될 수 있어요. Replica는 반드시 1로 두세요.

## 새 TRPG 시스템 추가하기

`systems/` 폴더에 새 yaml 파일을 만들면 됩니다 (예: `systems/coc.yaml`).

```yaml
name: "크툴루의 부름"
check_type: "percentile_under"   # 능력치 이하로 굴리면 성공
stats:
  - key: str
    label: "근력"
    default: 50
  - key: con
    label: "체력"
    default: 50
  # ...
default_hp: 10
```
`check_type`이 `percentile_under`면 `/check_stat`이 자동으로 1d100 언더 판정을, `d20_high`면 d20+수정치 판정을 합니다.
그 외 판정 방식이 필요하면 `cogs/character.py`의 `check_stat` 함수에 분기를 추가하면 됩니다.

## 다음에 확장하면 좋은 것들
- 몬스터/NPC 프리셋 DB (캐릭터와 별도 테이블)
- 상태이상(기절, 중독 등) 트래킹을 combat_sessions에 추가
- 인벤토리/아이템 시스템 (characters.extra_json 활용)
- 캐릭터 시트를 임베드 대신 이미지나 웹뷰로 렌더링
- GM 전용 권한 (특정 역할만 combat_* 명령 사용 가능하게 제한)
