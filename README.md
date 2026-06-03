# DeskPose Coach

웹캠을 이용해 사용자의 **앉은 자세**와 **화면 집중도**를 실시간으로 분석하고, 결과를 macOS 상단 메뉴바에 표시하는 컴퓨터비전 기반 애플리케이션입니다.

사전 학습된 landmark detection 모델을 활용하여 신체 자세와 얼굴/눈 움직임을 분석한 뒤, 기하학적 지표와 rule-based scoring 방식으로 자세 점수 및 집중도 점수를 계산합니다.

---

## 개요

일반적인 자세 교정 도구는 외부 센서나 별도의 하드웨어가 필요한 경우가 많습니다. DeskPose Coach는 노트북 또는 데스크탑의 기본 웹캠만으로 작동하는 lightweight computer vision system을 목표로 합니다.

분석하는 상태는 크게 두 가지입니다.

1. 사용자의 앉은 자세
2. 사용자의 화면 집중도

최종 분석 결과는 macOS 메뉴바에 실시간으로 표시됩니다.

```text
🟢 P:90 F:88
🟡 P:72 F:61
🔴 P:45 F:38
```

> `P` = Posture Score, `F` = Focus Score

---

## 주요 기능

- 웹캠 기반 실시간 모니터링
- MediaPipe 기반 pose / face landmark 추출
- baseline calibration 기반 자세 변화 감지
- 거북목 risk, slouch risk, 화면 거리 proxy 계산
- 얼굴 방향, iris ratio, 눈 감김을 이용한 coarse gaze zone 추정
- Reading mode를 통한 책/노트 보기 상태 반영
- blink / long eye closure 기반 drowsy signal
- 자세 점수 및 집중도 점수 계산
- study state event segmentation
- 일일 공부 세션 기록 및 누적 공부 시간 표시
- macOS 메뉴바 상태 표시
- CSV 로그, 세션 이벤트, 일일 공부 기록 저장
- 디버그 창을 통한 landmark 시각화

---

## 기술 스택

| 분류 | 항목 |
|---|---|
| Language | Python |
| Computer Vision | OpenCV, MediaPipe |
| Numerical | NumPy |
| UI | rumps |
| Data | pandas, matplotlib |
| Platform | macOS |

---

## 프로젝트 구조

```text
deskpose-coach/
├── main.py
├── requirements.txt
├── README.md
├── AGENTS.md
├── src/
│   ├── menubar_app.py
│   ├── camera_worker.py
│   ├── pose_analyzer.py
│   ├── posture_score.py
│   ├── face_analyzer.py
│   ├── head_pose_analyzer.py
│   ├── eye_analyzer.py
│   ├── gaze_analyzer.py
│   ├── distance_analyzer.py
│   ├── focus_score.py
│   ├── study_event_segmenter.py
│   ├── study_session.py
│   ├── session_summary.py
│   └── config.py
├── outputs/
├── assets/
└── docs/
```

---

## 동작 방식

```text
웹캠 프레임 입력 (OpenCV)
    ↓
신체 landmark 추출 (MediaPipe Pose)
    ↓
얼굴/눈 landmark 추출 (MediaPipe Face Landmarker)
    ↓
자세 지표 계산
    ↓
Posture Score 계산
    ↓
얼굴 방향 / iris 기반 시선 방향 / 눈 상태 분석
    ↓
Focus Score 계산
    ↓
Study State Event 분류
    ↓
macOS 메뉴바 실시간 표시
    ↓
CSV 로그 저장
```

---

## 자세 분석

DeskPose Coach는 pose landmark와 face landmark를 이용하여 사용자의 앉은 자세를 분석합니다.
`Start Monitoring` 직후 약 3초 동안 사용자의 정자세를 baseline으로 저장한 뒤, 이후 변화량을 기준으로 점수를 계산합니다.

### 사용 지표

| 지표 | 설명 |
|---|---|
| Head offset | 머리가 어깨 중심에서 얼마나 벗어났는지 |
| Shoulder slope | 어깨가 얼마나 기울어져 있는지 |
| Face ratio delta | 얼굴이 어깨 대비 얼마나 커졌는지 |
| Slouch delta | 정자세 대비 어깨/상체가 얼마나 낮아졌는지 |
| Distance proxy | 얼굴 bbox 크기로 추정한 화면 거리 상태 |

각 지표에 penalty를 적용하여 최종 Posture Score를 계산합니다.

### 상태 분류

| 점수 | 상태 |
|---|---|
| 80 이상 | 🟢 Good |
| 60 ~ 79 | 🟡 Warning |
| 60 미만 | 🔴 Bad |

---

## 집중도 분석

DeskPose Coach는 사용자가 화면을 보고 있는지, 시선이 벗어났는지를 대략적으로 판단합니다.

> MVP 목표는 정확한 픽셀 단위 gaze tracking이 아니라, 화면/책/화면 밖을 대략적으로 구분하는 것입니다.

### 사용 지표

| 지표 | 설명 |
|---|---|
| Face detection status | 얼굴 감지 여부 |
| Head yaw | 고개의 좌우 방향 |
| Head pitch | 고개의 상하 방향 |
| Head roll | 고개 기울기 |
| Iris ratio | 눈 안에서 iris가 위치한 대략적인 비율 |
| Eye Aspect Ratio | 눈 감김 정도 |
| Coarse gaze zone | 대략적인 시선 영역 |

### Gaze State

```text
Center
Left
Right
Up
Down
Reading
Away
No Face
```

### 상태 분류

| 점수 | 상태 |
|---|---|
| 75 이상 | Focused |
| 45 ~ 74 | Distracted |
| 45 미만 | Away |

---

## Study State Events

프레임 단위 결과가 일정 시간 이상 지속되면 다음 study state event로 저장합니다.

```text
Focused
Reading
Looking Away
Bad Posture
Drowsy
No Face
Distracted
```

이벤트 로그는 다음 파일에 저장됩니다.

```text
outputs/study_events.csv
```

공부 세션을 종료하면 하루 단위 요약이 다음 파일에 저장됩니다.

```text
outputs/daily_sessions.csv
```

기록되는 항목은 세션 시작/종료 시간, 총 공부 시간, focused 시간, 좋은 자세/나쁜 자세 시간, 화면 이탈/얼굴 미감지 시간, 평균 posture/focus score입니다.

메뉴바의 `Show Session Summary`를 누르면 현재까지의 평균 posture/focus score와 주요 event 시간을 요약해서 확인할 수 있습니다.

---

## 실행 방법

```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 2. 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt

# 3. 실행
python main.py
```

메뉴바에서 사용할 수 있는 주요 동작은 다음과 같습니다.

- `Start Monitoring`: webcam 분석 시작
- `Stop Monitoring`: 분석 중지 및 열린 event 저장
- `Reset Posture Calibration`: 현재 자세를 기준으로 posture baseline 재설정
- `Show Debug Window`: 카메라 영상과 분석 패널 표시
- `Show Session Summary`: CSV 기반 세션 요약 표시
- `Open Outputs Folder`: 로그 저장 폴더 열기

---

## MediaPipe 모델 파일

최근 `mediapipe` Python 패키지는 `mediapipe.solutions` 대신 Tasks API를 사용하는 경우가 있어, 로컬에 `.task` 모델 파일이 필요할 수 있습니다.

필요한 모델 파일은 다음과 같습니다.

```text
assets/pose_landmarker_lite.task
assets/face_landmarker.task
```

이 저장소에는 모델 파일을 직접 포함하지 않습니다. 아래 명령으로 `assets/` 폴더에 내려받아 둔 뒤 실행하세요.

```bash
mkdir -p assets

curl -L -o assets/pose_landmarker_lite.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task

curl -L -o assets/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

앱은 [config.py](src/config.py)의 `POSE_MODEL_PATH`, `FACE_MODEL_PATH` 설정을 통해 위 파일을 로드합니다.

파일이 없으면 앱은 실행될 수 있지만, pose 또는 face 분석 기능이 비활성화될 수 있습니다.

---

## macOS 카메라 권한 설정

웹캠이 정상적으로 열리지 않는 경우 macOS 카메라 권한을 확인해야 합니다.

```text
System Settings
→ Privacy & Security
→ Camera
→ Terminal 또는 사용 중인 IDE 허용
```

---

## 개발 현황

- [x] macOS 메뉴바 앱 실행
- [x] 웹캠 프레임 입력
- [x] 자세 landmark 추출
- [x] 자세 점수 계산
- [x] 얼굴 landmark 추출
- [x] 대략적인 gaze zone 추정
- [x] 집중도 점수 계산
- [x] 메뉴바 상태 업데이트
- [x] CSV 로그 저장
- [x] 디버그 화면 구현
- [x] head pose estimation
- [x] blink / long eye closure detection
- [x] face-to-screen distance proxy
- [x] study state event segmentation
- [x] session summary menu
- [ ] optional gaze calibration

---

## 정확도 관련 주의

DeskPose Coach는 의료용 자세 진단기나 연구 수준의 eye tracker가 아닙니다.
모든 점수는 webcam landmark 기반의 lightweight visual proxy이며, 발표용 term project MVP 수준의 rule-based estimate입니다.

---

## 1. Head Pose Estimation

Face landmark를 이용하여 사용자의 머리 방향을 추정합니다.

추정할 값은 다음과 같습니다.

| 값 | 의미 |
|---|---|
| Head yaw | 고개가 좌우로 돌아간 정도 |
| Head pitch | 고개가 위아래로 움직인 정도 |
| Head roll | 고개가 좌우로 기울어진 정도 |

이를 통해 사용자가 화면을 정면으로 보고 있는지, 화면 밖을 보고 있는지, 고개를 과도하게 숙이고 있는지 판단할 수 있습니다.

예시 상태는 다음과 같습니다.

```text
Forward
Looking Left
Looking Right
Looking Down
Head Tilted
No Face
```

---

## 2. Coarse Gaze Zone Estimation

눈 주변 landmark를 이용하여 사용자의 대략적인 시선 방향을 추정합니다.

본 프로젝트는 정확한 픽셀 단위의 gaze tracking을 목표로 하지 않습니다. 대신 사용자가 화면 중앙, 왼쪽, 오른쪽, 위, 아래 중 어느 방향을 보고 있는지를 대략적으로 분류하는 것을 목표로 합니다.

가능한 gaze zone은 다음과 같습니다.

```text
Center
Left
Right
Up
Down
Away
No Face
```

추후에는 사용자별 눈 모양, 카메라 위치, 화면 크기 차이를 줄이기 위해 간단한 calibration 과정을 추가할 수 있습니다.

---

## 3. Gaze Calibration

Gaze calibration은 사용자별 눈 모양, 카메라 위치, 화면 크기 차이를 줄이기 위한 선택 기능입니다.

예시 calibration 과정은 다음과 같습니다.

1. 화면 중앙을 봅니다.
2. 화면 왼쪽을 봅니다.
3. 화면 오른쪽을 봅니다.
4. 화면 위쪽을 봅니다.
5. 화면 아래쪽을 봅니다.

각 방향을 볼 때의 eye landmark ratio를 저장한 뒤, 실시간 입력값과 비교하여 현재 gaze zone을 분류합니다.

가능한 저장 파일은 다음과 같습니다.

```text
outputs/gaze_calibration.json
```

MVP 단계에서는 calibration이 없어도 기본 threshold 기반으로 동작할 수 있도록 구현합니다.

---

## 4. Blink and Eye Closure Detection

눈 landmark를 이용하여 사용자의 눈 깜빡임과 장시간 눈 감김 상태를 감지합니다.

대표적으로 사용할 수 있는 지표는 Eye Aspect Ratio입니다. 눈이 정상적으로 떠 있는 경우와 감긴 경우에는 눈의 세로 길이와 가로 길이의 비율이 달라지므로, 이를 이용해 눈 상태를 구분할 수 있습니다.

구분 가능한 상태는 다음과 같습니다.

```text
Eye Open
Blink
Long Eye Closure
Drowsy Signal
```

이 기능은 학습 중 피로 또는 졸림 신호를 추정하는 데 활용할 수 있습니다.

단, 본 프로젝트는 의료용 졸림 감지 시스템이 아니므로, 결과는 사용자의 상태를 추정하기 위한 보조 신호로만 사용합니다.

---

## 5. Face-to-Screen Distance Estimation

얼굴 landmark 또는 얼굴 bounding box의 크기를 이용하여 사용자가 화면에 너무 가까이 있는지 추정합니다.

이 기능은 정확한 실제 거리(cm)를 측정하는 것이 아니라, 프레임 내 얼굴 크기나 양쪽 눈 사이 거리를 기준으로 상대적인 거리를 계산합니다.

사용할 수 있는 시각적 지표는 다음과 같습니다.

| 지표 | 설명 |
|---|---|
| Face bounding box width | 프레임에서 얼굴이 차지하는 가로 크기 |
| Face bounding box height | 프레임에서 얼굴이 차지하는 세로 크기 |
| Eye-to-eye distance | 양쪽 눈 사이의 거리 |
| Face area ratio | 전체 프레임 대비 얼굴 영역 비율 |

예시 상태는 다음과 같습니다.

```text
Too Close
Normal Distance
Too Far
No Face
```

이 기능은 자세 악화나 눈 피로 가능성을 보조적으로 판단하는 데 사용할 수 있습니다.

---

## 6. Study State Event Segmentation

프레임 단위로 계산된 자세, 시선, 눈 감김 정보를 시간 구간 단위의 학습 상태 이벤트로 변환합니다.

예를 들어, 다음과 같이 학습 중 상태 변화를 기록할 수 있습니다.

```text
00:00 - 03:12  Focused
03:12 - 03:25  Looking Away
03:25 - 08:44  Focused
08:44 - 09:10  Bad Posture
09:10 - 09:18  No Face
```

이를 통해 단순한 순간 점수뿐만 아니라, 학습 중 어떤 상태가 얼마나 오래 지속되었는지 분석할 수 있습니다.

저장 가능한 이벤트 예시는 다음과 같습니다.

| Event | 설명 |
|---|---|
| Focused | 자세와 시선이 모두 안정적인 상태 |
| Looking Away | 화면 밖을 보는 상태 |
| Bad Posture | 자세 점수가 낮은 상태 |
| Drowsy | 눈 감김이 오래 지속되는 상태 |
| No Face | 얼굴이 감지되지 않는 상태 |

이벤트 로그는 다음과 같은 CSV 형식으로 저장할 수 있습니다.

```text
start_time,end_time,event_type,duration,avg_posture_score,avg_focus_score
```

가능한 저장 파일은 다음과 같습니다.

```text
outputs/study_events.csv
```

---

## 7. Debug Overlay Visualization

디버그 화면에서는 웹캠 프레임 위에 분석 결과를 시각화합니다.

표시할 정보는 다음과 같습니다.

- Pose skeleton
- Face landmarks
- Eye landmarks
- Head pose direction
- Gaze zone
- Eye closure state
- Posture score
- Focus score
- Current study state

이 기능은 프로젝트 발표에서 컴퓨터비전 파이프라인이 실제로 어떻게 동작하는지 보여주는 핵심 시각 자료로 활용됩니다.

디버그 화면은 선택적으로 켜고 끌 수 있어야 하며, 앱의 기본 동작이 디버그 창에 의존하지 않도록 구현합니다.

---

## 정확도 및 표현상의 한계

DeskPose Coach는 완벽한 의료용 자세 진단기나 연구 수준의 eye tracker를 목표로 하지 않습니다.

따라서 다음과 같은 강한 표현은 사용하지 않습니다.

- Exact gaze tracking
- Medical-grade posture diagnosis
- Accurate attention measurement
- Clinical drowsiness detection

대신 다음과 같은 표현을 사용합니다.

- Coarse gaze zone estimation
- Lightweight focus estimation
- Webcam-based posture analysis
- Rule-based study state classification
- Visual attention proxy
- Drowsiness signal

본 프로젝트의 핵심 목표는 컴퓨터비전 분석 파이프라인 구현, rule-based scoring을 통한 실시간 상태 판단, 그리고 그 결과를 실제 데스크탑 UI와 연결하는 것입니다.

---

## 프로젝트 목표

DeskPose Coach는 웹캠 기반 landmark detection을 활용하여 사용자의 자세와 화면 집중 상태를 실시간으로 분석하는 컴퓨터비전 텀프로젝트입니다.

핵심 목표는 다음과 같습니다.

1. 웹캠 입력을 안정적으로 처리한다.
2. pose / face / eye landmark를 추출한다.
3. 기하학적 지표를 기반으로 자세와 집중도 점수를 계산한다.
4. macOS 메뉴바에 실시간 상태를 표시한다.
5. CSV 로그와 debug overlay를 통해 분석 결과를 확인할 수 있게 한다.
6. 추가 컴퓨터비전 기능을 통해 학습 상태 분석 시스템으로 확장한다.
