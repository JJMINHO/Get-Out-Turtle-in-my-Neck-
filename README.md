# DeskFlow Coach

[![Version](https://img.shields.io/badge/version-1.0.0-grey)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?logo=python&logoColor=white)](#)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.x-teal)](#)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv&logoColor=white)](#)
[![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.x-orange)](#)
[![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos)

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

### Real-time Audio Alerts (실시간 소리 알림)

모니터링 중 자세가 흐트러지거나 집중 상태가 장시간 끊길 경우, 소리로 즉시 피드백을 전달하여 사용자가 스스로 상태를 인지하고 교정할 수 있도록 돕습니다. (설정 파일 `src/config.py`에서 사운드 활성화 여부, 딜레이 시간 및 볼륨 관련 조정을 하실 수 있습니다.)

* **자세 경고음**: 나쁜 자세(`Bad` 상태)가 설정 시간 동안 지속될 시 경고음 발생
* **집중도 경고음**: 시선이 화면을 벗어나거나 집중 상태가 오랫동안 흐트러질 시 알림음 발생
* **졸음 방지 경고음**: 사용자의 눈 감김이 장시간 지속되는 등 졸음 신호가 지속해서 감지될 때 경보음 발생

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
| AI Feedback | OpenAI API|
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

## Getting Started

일반 사용자는 가상환경 구축 없이 즉시 실행이 가능한 **DMG 배포판 설치**를 권장합니다.

### 📥 DMG 배포판 실행 방법 (권장)

1. **앱 다운로드**: [📥 macOS용 DeskFlow_Coach.dmg 다운로드](https://drive.google.com/file/d/1Wlls9NvBhMybV81mm6agVb7Psj3echQE/view?usp=sharing)
2. **설치**: 다운로드한 `.dmg` 파일을 더블 클릭하여 열고, `DeskFlow Coach` 아이콘을 `Applications(응용 프로그램)` 폴더로 드래그 앤 드롭합니다.
3. **최초 실행 보안 승인 (macOS Gatekeeper 우회)**:
   - 애플 개발자 등록을 거치지 않은 비인증 인하우스 빌드 앱이므로, 최초 실행 시 차단 메시지가 나타납니다.
   - 이를 실행하려면 앱 아이콘을 마우스 **우클릭(또는 Control + 클릭)** 한 뒤 **[열기]**를 선택하여 실행해 주시거나, `시스템 설정 -> 개인정보 보호 및 보안 -> 일반` 탭 하단에서 **"확인 없이 열기(Open Anyway)"**를 클릭해 주시면 정상 실행됩니다. (최초 1회만 필요)
4. **카메라 권한 승인**: 첫 구동 시 나타나는 웹캠 카메라 접근 요청 팝업에서 **[허용]**을 반드시 선택해 주세요.
5. **AI 피드백 활성화 (선택 사항)**:
   - OpenAI 코칭 피드백 기능을 사용하시려면, 아래 경로로 폴더를 생성하고 `.env` 파일에 API Key를 작성해 줍니다.
   - 경로: `~/Library/Application Support/DeskFlow Coach/.env`
   - 내용 예시: `OPENAI_API_KEY=your-openai-api-key`

* **데이터 및 로그 저장 경로**: `~/Library/Application Support/DeskFlow Coach/`

---

## 데이터 및 로그

| 파일 | 설명 |
|---|---|
| `posture_focus_log.csv` | 프레임 단위 자세 / 집중도 로그 |
| `study_events.csv` | Focused, Bad Posture, No Face 등 구간 이벤트 |
| `daily_sessions.csv` | 하루 단위 세션 요약 |
| `calendar_events.csv` | 캘린더 일정 데이터 |
| `app.log` | 배포 앱 실행 로그 |

---

## Open Source

이 프로젝트는 OpenCV, MediaPipe, NumPy, pandas, matplotlib, CustomTkinter, rumps, Pillow, PyInstaller를 사용합니다.

OpenAI API와 Gemini API는 외부 AI 서비스이며, 이 저장소의 오픈소스 라이선스 범위에 포함되지 않습니다.

---

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.
