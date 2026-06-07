# DeskFlow Coach

웹캠으로 자세, 화면 집중 흐름, 하루 작업 리듬을 함께 보여주는 macOS 데스크톱 코치입니다.

DeskFlow Coach는 별도 센서 없이 카메라 입력만으로 사용자의 앉은 자세와 화면 주시 상태를 가볍게 분석하고, 이를 Performance Score, 일일 리포트, 캘린더 일정, 메뉴바 위젯으로 연결합니다. 의료용 진단 도구나 정확한 eye tracker가 아니라, 컴퓨터비전 기반의 작업 습관 모니터링 MVP입니다.

![DeskFlow Coach dashboard demo](docs/images/dashboard-demo.png)

> Demo image placeholder: 위 경로에 대시보드 실행 화면을 넣으면 됩니다.

---

## Highlights

- 실시간 카메라 기반 자세 및 화면 집중 흐름 분석
- MediaPipe pose / face landmarks 기반 rule-based scoring
- macOS 메뉴바 위젯: `Show Dashboard`, `Start` 또는 `Stop`, `Quit`
- 일일 통계 제공
- Performance Score와 일일 리포트
- 월별 캘린더와 일정 추가, 수정, 삭제
- 일정과 현재 score 기반의 AI feedback

---

## App Screens

### Dashboard

<img width="1277" height="981" alt="Image" src="https://github.com/user-attachments/assets/dbb72200-627f-408e-85f4-e8bf88f97f64" />
<img width="1277" height="987" alt="Image" src="https://github.com/user-attachments/assets/f5337963-dfe6-4317-a368-b539e0ecfa3d" />
<img width="1277" height="987" alt="Image" src="https://github.com/user-attachments/assets/333c7763-b8fb-4713-80ee-47de25f256ab" />

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

Performance Score는 하루의 작업 흐름을 하나의 점수로 요약합니다. 하루 기준은 오전 5시에 시작해 다음날 오전 4시 59분에 끝납니다.

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

자세 관련 조언은 API가 아니라 로컬 디텍팅 수치로 생성됩니다. API는 일정, 업무량, 집중 흐름에 대한 문구에만 사용됩니다. API key가 없거나 호출에 실패하면 rule-based feedback이 표시됩니다.

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
├── requirements.txt
├── README.md
├── LICENSE
├── DeskFlowCoach.spec
├── assets/
│   ├── app_icon.png
│   └── app_icon.icns
├── scripts/
│   └── build_macos_app.sh
├── src/
│   ├── camera_worker.py
│   ├── dashboard_ui.py
│   ├── menubar_app.py
│   ├── pose_analyzer.py
│   ├── face_analyzer.py
│   ├── gaze_analyzer.py
│   ├── posture_score.py
│   ├── focus_score.py
│   ├── daily_score.py
│   ├── study_event_segmenter.py
│   └── ai_feedback.py
└── outputs/
```

---

## Run From Source

### 1. Clone or open the project

```bash
cd /Users/randonlb/Desktop/deskpose-coach
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start the app

```bash
python main.py
```

소스 실행 시 데이터는 기본적으로 `outputs/` 아래에 저장됩니다.

---

## Windows Support

Windows terminal mode is currently in progress.

The computer vision pipeline and dashboard are being prepared for Windows terminal execution, but the current release target is macOS. The macOS menu bar widget, `.app` bundle, and DMG packaging remain macOS-only.

---

## Run the macOS App

빌드된 앱을 실행하려면 다음 파일을 엽니다.

```text
dist/DeskFlow Coach.app
```

또는 DMG를 열어 설치합니다.

```text
dist/DeskFlow_Coach.dmg
```

배포 앱의 데이터 저장 위치:

```text
~/Library/Application Support/DeskFlow Coach
```

---

## Build for macOS

PyInstaller 기반 빌드 스크립트를 사용합니다. 프로젝트에 `.venv`가 있으면 해당 Python을 우선 사용합니다.

```bash
./scripts/build_macos_app.sh
```

빌드 결과:

```text
dist/DeskFlow Coach.app
```

DMG를 만들려면:

```bash
hdiutil create -volname "DeskFlow Coach" \
  -srcfolder "dist/DeskFlow Coach.app" \
  -ov -format UDZO \
  "dist/DeskFlow_Coach.dmg"
```

---

## API Key Setup

AI feedback은 선택 기능입니다. API key가 없어도 앱은 로컬 rule-based feedback으로 동작합니다.

소스 실행용 `.env`:

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

배포 앱에서 API key를 사용하려면 다음 위치에 `.env` 파일을 둡니다.

```text
~/Library/Application Support/DeskFlow Coach/.env
```

실제 API key는 저장소, README, 앱 번들에 포함하지 마세요.

---

## Data and Logs

DeskFlow Coach는 분석 결과를 CSV로 저장합니다.

| File | Description |
|---|---|
| `posture_focus_log.csv` | posture / focus frame-level log |
| `study_events.csv` | Focused, Bad Posture, No Face 등 구간 이벤트 |
| `daily_sessions.csv` | 하루 단위 작업 세션 요약 |
| `calendar_events.csv` | 캘린더 일정 데이터 |
| `app.log` | 배포 앱 실행 로그 |

소스 실행에서는 `outputs/`에 저장되고, 배포 앱에서는 `~/Library/Application Support/DeskFlow Coach`에 저장됩니다.

---

## Camera Permission

macOS에서 카메라가 열리지 않으면 권한을 확인하세요.

```text
System Settings
→ Privacy & Security
→ Camera
→ Terminal, IDE, 또는 DeskFlow Coach 허용
```

다른 앱이 카메라를 사용 중이면 OpenCV capture가 실패할 수 있습니다.

---

## Accuracy Notice

DeskFlow Coach는 다음을 제공하지 않습니다.

- 의료용 자세 진단
- 임상 수준 졸림 감지
- 정확한 시선 좌표 추정
- 심리학적 집중도 측정
- 사용자 상태에 대한 완전한 판단

이 앱의 점수는 webcam landmark 기반의 lightweight visual proxy입니다. 자세와 작업 습관을 돌아보기 위한 참고 지표로 사용하세요.

---

## Open Source

DeskFlow Coach는 다음 오픈소스 기술을 사용합니다.

- OpenCV
- MediaPipe
- NumPy
- pandas
- matplotlib
- customtkinter
- rumps
- Pillow
- PyInstaller

OpenAI API와 Gemini API는 외부 AI 서비스이며, 이 저장소의 오픈소스 라이선스 범위에 포함되지 않습니다.

---

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.
