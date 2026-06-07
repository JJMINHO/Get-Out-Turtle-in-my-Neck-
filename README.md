# DeskFlow Coach

웹캠으로 자세, 화면 집중 흐름, 하루 작업 리듬을 함께 보여주는 macOS 데스크톱 코치입니다.

DeskFlow Coach는 별도 센서 없이 카메라 입력만으로 사용자의 앉은 자세와 화면 주시 상태를 가볍게 분석하고, 이를 Performance Score, 일일 리포트, 캘린더 일정, 메뉴바 위젯으로 연결합니다. 의료용 진단 도구나 정확한 eye tracker가 아니라, 컴퓨터비전 기반의 업무 및 학습 코칭 도구입니다.


---

## Highlights

- 실시간 카메라 기반 자세 및 화면 집중 흐름 분석
- MediaPipe pose / face landmarks 기반 rule-based scoring
- macOS 메뉴바 위젯: `Show Dashboard`, `Start`/`Stop`, `Quit`
- 일일 통계 제공
- Performance Score와 일일 리포트
- 월별 캘린더와 일정 추가, 수정, 삭제
- 일정과 현재 score 기반의 AI feedback

---

## App Screens

### Dashboard

<img width="1277" height="981" alt="Image" src="https://github.com/user-attachments/assets/ddbdc7b0-3018-4812-b64b-28163550e557" />
<img width="1277" height="987" alt="Image" src="https://github.com/user-attachments/assets/214f3453-1d70-4762-8289-d6172ab93745" />
<img width="1277" height="978" alt="Image" src="https://github.com/user-attachments/assets/035603ff-8b02-4765-adfe-78cb1b2fad9d" />


### Calendar

<img width="1274" height="891" alt="Image" src="https://github.com/user-attachments/assets/cab387eb-24bb-44ff-90b8-125690106419" />

### Daily Report

<img width="956" height="1052" alt="Image" src="https://github.com/user-attachments/assets/e36ab44f-9c61-471a-a510-3a2e65ef5d1b" />

---

### Widget

<img width="608" height="29" alt="Image" src="https://github.com/user-attachments/assets/e828b04b-398d-4d25-85fd-d2b58148e665" />

## Main Features

### Real-time Vision Dashboard

대시보드는 앱 실행 직후 바로 열립니다. 카메라 화면, posture score, focus score, 작업 시간, 집중 시간, Performance Score, feedback을 한 화면에서 확인할 수 있습니다.

- 카메라 촬영 중일 때만 `Live Camera` 표시
- 카메라 view 토글 시 대시보드가 compact layout으로 자동 조정
- 시작 상태에서는 버튼이 `중지`, 중지 상태에서는 `시작`으로 표시
- 로컬 자세 피드백과 AI 일정 피드백을 분리해서 표시

### Posture Analysis

MediaPipe Pose와 Face landmarks를 사용해 사용자의 자세 변화를 추정합니다. 초기 baseline을 기준으로 얼굴/어깨 비율, 어깨 높이, 상체 기울기, 화면과의 상대 거리 등을 계산합니다.

표시 및 기록되는 주요 지표:

- posture score
- neck / shoulder / torso related metrics
- face-to-screen distance proxy
- posture status: `Good`, `Warning`, `Bad`
- posture reset calibration

### Focus Analysis

얼굴 감지 여부, head direction, coarse gaze zone, eye closure signal을 조합해 화면 집중 상태를 추정합니다.

표시 및 기록되는 주요 지표:

- focus score
- coarse gaze zone: `Center`, `Left`, `Right`, `Up`, `Down`, `Away`, `No Face`
- focused / distracted / away state
- blink and long eye closure signal
- reading-like state proxy

### Performance Score

Performance Score는 하루의 작업 흐름을 하나의 점수로 요약합니다. 시스템 상의 하루는 오전 5시에 시작해 다음날 오전 4시 59분에 끝납니다.

```text
Performance Score =
집중도 40점
+ 업무/학습량 30점
+ Focus & Posture 30점
```

사용되는 데이터:

- 총 작업 시간
- 총 집중 시간
- 집중도: 총 집중 시간 / 총 작업 시간
- 좋은 자세 유지 시간
- away / no face / drowsy signal 시간
- posture score와 focus score의 조합

### Calendar

대시보드에서 월별 캘린더를 열고 일정과 하루 기록을 함께 확인할 수 있습니다.

- 월별 이동
- 일정 추가, 수정, 삭제
- 날짜별 작업 시간, 집중 시간, Performance Score 표시
- 일정 종류와 중요도 설정
- 05:00 이전 기록은 전날 기준으로 표시

### AI Feedback

OpenAI API key를 설정하면 캘린더 일정과 현재 작업 흐름을 반영한 짧은 코칭 문구를 생성합니다. 가까운 시험, 프로젝트, 마감이 있거나 Performance Score가 낮을수록 더 직접적인 메시지를 요청합니다.

자세 관련 조언은 API가 아니라 로컬 디텍팅 수치로 생성되며, API는 일정, 업무량, 집중 흐름에 대한 문구에만 사용됩니다. 
API key가 없거나 호출에 실패하면 rule-based feedback이 표시됩니다.

### Menu Bar Widget

대시보드를 닫아도 앱은 메뉴바에 남아 상태를 표시할 수 있습니다.

메뉴 구성:

- `Show Dashboard`
- `Start` 또는 `Stop`
- `Quit`

`Quit`은 camera worker와 dashboard를 정리한 뒤 앱을 종료합니다.

---

## Technology Stack

| Area | Stack |
|---|---|
| Language | Python |
| Computer Vision | OpenCV, MediaPipe |
| Numerical | NumPy |
| UI | customtkinter, rumps |
| Data | CSV, pandas, matplotlib |
| Image Handling | Pillow |
| AI Feedback | OpenAI API, optional Gemini fallback |
| Packaging | PyInstaller, macOS `.app`, DMG |
| Platform | macOS |

---

## Vision Pipeline

```text
Webcam frame
→ OpenCV capture / preprocessing
→ MediaPipe Pose landmarks
→ MediaPipe Face / Eye landmarks
→ posture metrics
→ head / gaze / eye state analysis
→ posture score + focus score
→ work state segmentation
→ daily score + calendar + report
→ dashboard / menu bar / CSV logs
```

주요 컴퓨터비전 기술:

- webcam frame capture
- pose landmark detection
- face landmark detection
- iris and eye landmark ratios
- head yaw / pitch / roll approximation
- eye aspect ratio
- face-size based distance proxy
- rule-based posture scoring
- rule-based focus scoring
- time-based work state segmentation
- OpenCV debug overlay visualization

---

## Project Structure

```text
deskpose-coach/
├── main.py
├── README.md
├── LICENSE
├── requirements.txt
├── DeskFlowCoach.spec
├── assets/              # app icon and MediaPipe task models
├── scripts/             # macOS build script
├── src/                 # dashboard, camera worker, CV analyzers, scoring, feedback
└── outputs/             # source-run logs and CSV data
```

---

## Run From Source

```bash
cd /Users/randonlb/Desktop/deskpose-coach
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Source-run data is saved under `outputs/`.

---

## Windows Support

Windows terminal mode is currently in progress. The current release target is macOS, and the menu bar widget, `.app` bundle, and DMG packaging are macOS-only.

---

## Run the macOS App

```text
dist/DeskFlow Coach.app
dist/DeskFlow_Coach.dmg
```

App data is saved here:

```text
~/Library/Application Support/DeskFlow Coach
```

---

## Build for macOS

```bash
./scripts/build_macos_app.sh
```

Optional DMG:

```bash
hdiutil create -volname "DeskFlow Coach" \
  -srcfolder "dist/DeskFlow Coach.app" \
  -ov -format UDZO \
  "dist/DeskFlow_Coach.dmg"
```

---

## API Key Setup

AI feedback is optional. Without an API key, the app uses local rule-based feedback.

```bash
cp .env.example .env
```

```text
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.4-mini

# Optional fallback
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash
```

For the packaged app, place `.env` here:

```text
~/Library/Application Support/DeskFlow Coach/.env
```

Do not commit or bundle real API keys.

---

## Data and Logs

| File | Description |
|---|---|
| `posture_focus_log.csv` | posture / focus frame-level log |
| `study_events.csv` | Focused, Bad Posture, No Face 등 구간 이벤트 |
| `daily_sessions.csv` | 하루 단위 작업 세션 요약 |
| `calendar_events.csv` | 캘린더 일정 데이터 |
| `app.log` | 배포 앱 실행 로그 |

Source run: `outputs/`  
Packaged app: `~/Library/Application Support/DeskFlow Coach`

---

## Camera Permission

```text
System Settings
→ Privacy & Security
→ Camera
→ Terminal, IDE, 또는 DeskFlow Coach 허용
```

다른 앱이 카메라를 사용 중이면 OpenCV capture가 실패할 수 있습니다.

---

## Accuracy Notice

DeskFlow Coach is not a medical posture diagnosis tool, clinical drowsiness detector, exact gaze tracker, or psychological attention measurement system. Scores are lightweight webcam landmark-based visual proxies.

---

## Open Source

OpenCV, MediaPipe, NumPy, pandas, matplotlib, customtkinter, rumps, Pillow, and PyInstaller.

OpenAI API와 Gemini API는 외부 AI 서비스이며, 이 저장소의 오픈소스 라이선스 범위에 포함되지 않습니다.

---

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.
