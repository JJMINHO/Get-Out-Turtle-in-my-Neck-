# DeskFlow Coach

자세, 집중, 일정 흐름을 함께 읽어주는 macOS 작업 코치

DeskFlow Coach는 웹캠 기반 컴퓨터비전으로 사용자의 앉은 자세, 화면 집중 상태, 작업 흐름을 가볍게 분석하는 데스크톱 앱입니다. 별도 센서 없이 카메라 입력만으로 posture score, focus score, performance score를 계산하고, 그 결과를 대시보드와 메뉴바에서 바로 확인할 수 있습니다.

이 앱은 의료용 자세 진단기나 정확한 eye tracker가 아닙니다. DeskFlow Coach는 term project MVP 수준의 lightweight monitoring tool이며, 작업 습관을 돌아보기 위한 시각적 보조 도구입니다.

---

## 왜 DeskFlow Coach인가

책상 앞에 오래 앉아 있으면 자세는 무너지고, 집중은 조용히 흩어집니다. DeskFlow Coach는 이 흐름을 숫자와 시각화로 보여줍니다.

- 지금 자세가 안정적인지
- 화면을 보고 있는지, 자주 이탈하는지
- 오늘 얼마나 공부했고 얼마나 집중했는지
- 마감 일정 대비 지금 페이스가 괜찮은지
- 하루 작업의 양과 질이 어느 정도였는지

DeskFlow Coach는 단순히 "카메라 화면을 보여주는 앱"이 아니라, 컴퓨터비전 분석 결과를 하루 단위 performance score와 리포트로 연결합니다.

---

## 주요 기능

### 실시간 자세 분석

MediaPipe pose / face landmarks를 활용해 사용자의 앉은 자세를 분석합니다.

- posture score
- forward head / slouch risk proxy
- shoulder slope
- face-to-screen distance proxy
- baseline calibration 기반 자세 변화 감지

### 실시간 집중도 분석

얼굴 방향, 눈 주변 landmark, iris 위치, 눈 감김 신호를 이용해 화면 집중 상태를 대략적으로 추정합니다.

- focus score
- coarse gaze zone
- reading state
- away / no face state
- blink / long eye closure 기반 drowsy signal

### Performance Score

하루 작업 흐름을 하나의 점수로 요약합니다. 하루 기준은 05:00부터 다음날 04:59까지입니다.

```text
Performance Score =
집중도 40점
+ 업무/학습량 30점
+ Focus & Posture 30점
```

점수는 다음 데이터를 조합합니다.

- 총 작업 시간
- 총 집중 시간
- 집중도: 총 집중 시간 / 총 작업 시간
- 좋은 자세 유지 시간
- away / no face / drowsy signal 시간
- posture score와 focus score의 조합

### Daily Vision Report

하루의 작업 상태를 리포트 창에서 시각적으로 확인할 수 있습니다.

- Performance Score
- score parts: focus, work/study amount, Focus & Posture
- daily metrics progress bars
- Focus x Posture quadrant
- work state timeline
- state duration summary

### 캘린더와 일정 관리

대시보드에서 월별 캘린더를 열고 일정을 관리할 수 있습니다.

- 월별 캘린더 보기
- 일정 추가 / 수정 / 삭제
- 날짜 입력창 클릭 시 날짜 선택 목록 표시
- 시험, 프로젝트, 마감, 과제 일정 기록
- 일정이 OpenAI AI coach feedback에 반영됨

### OpenAI AI Coach Feedback

OpenAI API를 연결하면 Feedback 카드가 더 맥락 있는 작업 코치처럼 동작합니다.

입력으로 사용되는 정보:

- 오늘 집중 작업 시간
- 현재 세션 시간
- posture score
- focus score
- focused / away / no face 시간
- 캘린더의 시험 및 마감 일정

출력 예시:

```text
마감이 가까운데 집중 시간이 부족합니다. 지금은 정리보다 제출 가능한 결과물을 만드는 데 25분만 몰아붙이세요.
```

API key가 없거나 호출에 실패하면 기존 rule-based feedback이 자동으로 표시됩니다.

### 메뉴바 위젯

대시보드를 닫아도 앱은 메뉴바 위젯으로 남을 수 있습니다.

```text
P: 90 | F: 88
```

메뉴바에서는 모니터링 시작/중지, 디버그 창, 캘린더 요약, 출력 폴더 열기 등을 사용할 수 있습니다.

---

## 화면 구성

DeskFlow Coach의 기본 화면은 healthcare dashboard 스타일로 구성되어 있습니다.

- Live Camera preview
- Posture Score
- Focus Score
- Focus Session
- Focus Work Time
- Performance Score
- OpenAI / Gemini fallback / rule-based Feedback
- Calendar
- Daily Vision Report

카메라 뷰를 끄면 대시보드는 compact mode로 전환되어 더 작은 화면에서도 점수와 피드백을 볼 수 있습니다.

---

## 사용 기술

| 영역 | 사용 기술 |
|---|---|
| Language | Python |
| Computer Vision | OpenCV, MediaPipe |
| Numerical | NumPy |
| UI | customtkinter, rumps |
| Data | pandas, matplotlib, CSV |
| Image Handling | Pillow |
| AI Feedback | OpenAI API, optional Gemini fallback |
| Platform | macOS |

---

## 컴퓨터비전 파이프라인

```text
Webcam frame
→ OpenCV preprocessing
→ MediaPipe pose landmarks
→ MediaPipe face / eye landmarks
→ posture metrics
→ gaze / head / eye state analysis
→ posture score + focus score
→ work state segmentation
→ daily score + visual report
```

사용된 주요 비전 분석:

- webcam frame capture
- pose landmark detection
- face landmark detection
- iris / eye landmark ratio
- head yaw / pitch / roll approximation
- eye aspect ratio
- face size based distance proxy
- rule-based posture scoring
- rule-based focus scoring
- time-based work state segmentation

---

## 설치 및 실행

### 1. 저장소 준비

```bash
cd /Users/randonlb/Desktop/deskpose-coach
```

### 2. 가상환경 생성 및 활성화

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 실행

```bash
python main.py
```

---

## AI Feedback API 설정

OpenAI API를 연결하면 Feedback 카드가 일정, 집중 상태, 누적 작업 시간을 반영해 더 맥락 있는 코칭 문구를 생성합니다.
프로젝트 루트에 `.env` 파일을 만듭니다.

```bash
cp .env.example .env
```

`.env`:

```text
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.4-mini

# Optional fallback
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash
```

`OPENAI_API_KEY`가 있으면 OpenAI Responses API를 먼저 사용하고, 없으면 Gemini 설정을 fallback으로 확인합니다.
배포 환경에서는 `.env` 파일을 포함하지 말고, OS 환경변수나 패키징 도구의 secret 설정으로 API 키를 주입하세요.

---

## macOS 앱 번들 빌드

PyInstaller로 `.app` 번들을 만들 수 있습니다.

```bash
./scripts/build_macos_app.sh
```

빌드 결과:

```text
dist/DeskFlow Coach.app
```

배포 앱은 분석 로그와 일정 데이터를 다음 위치에 저장합니다.

```text
~/Library/Application Support/DeskFlow Coach
```

배포 앱에서 API 키를 사용하려면 다음 파일을 만들 수 있습니다.

```text
~/Library/Application Support/DeskFlow Coach/.env
```

예시:

```text
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.4-mini
```

`.env` 파일과 실제 API 키는 앱 번들 또는 저장소에 포함하지 마세요.

---

## 캘린더 일정 데이터

일정은 다음 CSV에 저장됩니다.

```text
outputs/calendar_events.csv
```

형식:

```csv
date,title,type,priority
2026-06-10,운영체제 기말고사,exam,high
2026-06-12,캡스톤 프로젝트 제출,deadline,high
```

대시보드 캘린더에서 직접 추가, 수정, 삭제할 수 있습니다.

---

## 로그와 리포트

DeskFlow Coach는 분석 결과를 `outputs/` 아래에 저장합니다.

| 파일 | 설명 |
|---|---|
| `outputs/posture_focus_log.csv` | frame-level posture / focus 로그 |
| `outputs/study_events.csv` | Focused, Bad Posture, No Face 등 구간 이벤트 |
| `outputs/daily_sessions.csv` | 하루 단위 작업 세션 요약 |
| `outputs/calendar_events.csv` | 시험, 마감, 프로젝트 일정 |

대용량 영상 파일이나 원본 webcam frame은 기본적으로 저장하지 않습니다.

---

## macOS 카메라 권한

카메라가 열리지 않으면 macOS 권한을 확인하세요.

```text
System Settings
→ Privacy & Security
→ Camera
→ Terminal 또는 사용 중인 IDE 허용
```

다른 앱이 카메라를 사용 중인 경우에도 webcam capture가 실패할 수 있습니다.

---

## 정확도 및 책임 고지

DeskFlow Coach는 다음을 제공하지 않습니다.

- 의료용 자세 진단
- 임상 수준 졸림 감지
- 정확한 시선 좌표 추정
- 심리학적 집중도 측정
- 사용자 상태에 대한 완전한 판단

이 앱의 점수는 webcam landmark 기반의 lightweight visual proxy입니다. 자세와 집중 습관을 돌아보는 참고 지표로 사용하세요.

---

## 오픈소스

DeskFlow Coach는 다음 오픈소스 기술을 사용합니다.

- OpenCV
- MediaPipe
- NumPy
- pandas
- matplotlib
- customtkinter
- rumps
- Pillow

OpenAI API와 Gemini API는 외부 AI 서비스이며 오픈소스 라이브러리가 아닙니다.

---

## 프로젝트 상태

현재 구현된 기능:

- macOS 대시보드 앱
- 메뉴바 위젯
- webcam 분석 루프
- posture score
- focus score
- work state segmentation
- CSV logging
- calendar schedule management
- OpenAI AI feedback with Gemini fallback
- daily performance score
- daily vision report
- debug visualization

추후 개선 아이디어:

- 일일 리포트의 더 정교한 chart rendering
- 사용자별 작업 기준 설정
- 캘린더 일정 알림
- optional gaze calibration
- macOS app packaging

---

## License

DeskFlow Coach is released under the MIT License. See [LICENSE](LICENSE) for details.
