# AGENTS.md

이 문서는 DeskPose Coach 프로젝트에서 AI coding agent가 코드를 작성하거나 수정할 때 따라야 할 작업 지침입니다.

---

## 1. Project Overview

DeskPose Coach는 웹캠을 이용해 사용자의 **앉은 자세**와 **화면 집중도**를 실시간으로 분석하고, 그 결과를 macOS 상단 메뉴바에 표시하는 컴퓨터비전 기반 애플리케이션입니다.

이 프로젝트는 별도의 딥러닝 모델을 직접 학습하지 않습니다.  
사전 학습된 landmark detection 모델을 활용하여 신체 자세와 얼굴/눈 움직임을 분석한 뒤, 기하학적 지표와 rule-based scoring 방식으로 자세 점수와 집중도 점수를 계산합니다.

DeskPose Coach의 핵심은 다음과 같습니다.

- webcam-based computer vision pipeline
- MediaPipe 기반 pose / face landmark 추출
- rule-based posture scoring
- coarse gaze zone estimation
- lightweight focus estimation
- macOS menu bar UI 연동
- CSV logging
- debug overlay visualization

---

## 2. Core Goals

이 프로젝트의 핵심 목표는 다음과 같습니다.

1. 웹캠 기반 real-time computer vision pipeline 구현
2. MediaPipe Pose 기반 자세 landmark 추출
3. MediaPipe Face Landmarker 기반 얼굴/눈 landmark 추출
4. 자세 관련 기하학적 지표 계산
5. coarse gaze zone 추정
6. posture score 및 focus score 계산
7. macOS 메뉴바에 실시간 상태 표시
8. CSV 로그 저장
9. 디버그 창을 통한 landmark 시각화

DeskPose Coach는 의료용 자세 진단기나 연구 수준의 eye tracker가 아닙니다.  
정확한 진단보다 **작동 가능한 computer vision MVP**와 **macOS UI 연동**이 핵심입니다.

---

## 3. Technology Stack

다음 기술 스택을 기본으로 사용합니다.

| Category | Stack |
|---|---|
| Language | Python |
| Computer Vision | OpenCV, MediaPipe |
| Numerical | NumPy |
| UI | rumps |
| Data | pandas, matplotlib |
| Platform | macOS |

다른 GUI 프레임워크로 변경하지 마세요.

피해야 할 것:

- Swift로 재작성
- PyQt 도입
- Electron 도입
- 불필요한 웹 서버 도입
- custom deep learning model 학습
- 대용량 dataset 추가
- 복잡한 backend server 구조 추가

---

## 4. Project Structure

기본 프로젝트 구조는 다음과 같습니다.

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
│   ├── gaze_analyzer.py
│   ├── focus_score.py
│   └── config.py
├── outputs/
├── assets/
└── docs/
```

추가 컴퓨터비전 기능 구현 과정에서 다음 파일을 추가할 수 있습니다.

```text
src/
├── head_pose_analyzer.py
├── eye_analyzer.py
├── distance_analyzer.py
├── study_event_segmenter.py
└── debug_overlay.py
```

---

## 5. File Responsibilities

### main.py

앱의 실행 진입점입니다.

역할:

- DeskPose Coach 앱 실행
- macOS menu bar app 시작
- 불필요한 로직을 직접 포함하지 않기

`main.py`는 최대한 단순하게 유지하세요.

---

### src/menubar_app.py

macOS 메뉴바 UI를 담당합니다.

역할:

- rumps 기반 메뉴바 앱 생성
- Start Monitoring 메뉴
- Stop Monitoring 메뉴
- Debug Window 토글
- Quit 메뉴
- posture score와 focus score를 메뉴바 title에 표시
- background camera worker와 연결

예상 메뉴바 표시 예시:

```text
🟢 P:90 F:88
🟡 P:72 F:61
🔴 P:45 F:38
```

`P`는 posture score, `F`는 focus score입니다.

---

### src/camera_worker.py

웹캠 입력과 실시간 분석 루프를 담당합니다.

역할:

- OpenCV로 웹캠 열기
- 프레임 읽기
- pose analyzer 실행
- face analyzer 실행
- gaze analyzer 실행
- posture score 계산
- focus score 계산
- 최신 분석 결과를 menubar app에 전달
- CSV 로그 저장
- 카메라 안전 종료

중요:

- 메뉴바 UI가 멈추지 않도록 background thread에서 실행하세요.
- 카메라 종료 시 `cap.release()`를 반드시 호출하세요.
- 디버그 창 사용 시 종료 시점에 `cv2.destroyAllWindows()`를 호출하세요.

---

### src/pose_analyzer.py

신체 자세 landmark 추출을 담당합니다.

역할:

- MediaPipe Pose 초기화
- frame preprocessing
- pose landmark 추출
- 필요한 landmark 좌표 반환
- 디버그 시 skeleton 또는 keypoint 시각화

주요 landmark 예시:

- nose
- left_ear / right_ear
- left_shoulder / right_shoulder
- left_hip / right_hip

---

### src/posture_score.py

자세 지표와 posture score 계산을 담당합니다.

역할:

- neck angle 계산
- shoulder slope 계산
- torso lean 계산
- posture score 계산
- posture status 분류

사용 지표:

| Metric | Description |
|---|---|
| Neck angle | 목이 얼마나 기울어져 있는지 |
| Shoulder slope | 어깨가 얼마나 기울어져 있는지 |
| Torso lean | 상체가 얼마나 기울어져 있는지 |

기본 posture status rule:

| Score | Status |
|---|---|
| 80 이상 | Good |
| 60 ~ 79 | Warning |
| 60 미만 | Bad |

---

### src/face_analyzer.py

얼굴 및 눈 주변 landmark 추출을 담당합니다.

역할:

- MediaPipe Face Landmarker 초기화
- 얼굴 감지 여부 확인
- 얼굴 landmark 추출
- 눈 주변 landmark 추출
- head direction 추정에 필요한 좌표 반환
- 디버그 시 face landmark 시각화

반환 정보 예시:

- `face_detected`
- `face_landmarks`
- `left_eye_landmarks`
- `right_eye_landmarks`
- `nose_position`
- `face_center`

---

### src/gaze_analyzer.py

대략적인 gaze zone 추정을 담당합니다.

역할:

- 얼굴 landmark 기반 head yaw 추정
- 얼굴 landmark 기반 head pitch 추정
- 눈 landmark 기반 eye movement ratio 계산
- coarse gaze zone 분류

중요 제약:

이 프로젝트는 정확한 픽셀 단위 gaze tracking을 목표로 하지 않습니다.

목표는 다음 정도입니다.

- 사용자가 화면을 보고 있는가?
- 사용자가 왼쪽/오른쪽/위/아래를 보는가?
- 얼굴이 감지되지 않는가?
- 사용자가 화면에서 시선을 벗어났는가?

가능한 gaze state:

```text
Center
Left
Right
Up
Down
Away
No Face
```

---

### src/focus_score.py

집중도 점수와 focus status 계산을 담당합니다.

역할:

- face detection status 반영
- head yaw penalty 반영
- head pitch penalty 반영
- gaze zone penalty 반영
- focus score 계산
- focus status 분류

기본 focus status rule:

| Score | Status |
|---|---|
| 75 이상 | Focused |
| 45 ~ 74 | Distracted |
| 45 미만 | Away |

주의:

- focus score는 실제 심리학적 집중도를 의미하지 않습니다.
- 웹캠 기반 시선/얼굴 방향 정보를 이용한 lightweight estimate입니다.
- README나 코드 주석에서 과도한 정확도 주장을 하지 마세요.

---

### src/config.py

프로젝트 전체 설정값을 관리합니다.

포함할 수 있는 설정:

- camera index
- frame width
- frame height
- posture threshold
- focus threshold
- CSV log path
- debug window name
- update interval
- MediaPipe confidence threshold

예시 설정 이름:

```python
CAMERA_INDEX
FRAME_WIDTH
FRAME_HEIGHT
GOOD_THRESHOLD
WARNING_THRESHOLD
FOCUSED_THRESHOLD
DISTRACTED_THRESHOLD
CSV_LOG_PATH
DEBUG_WINDOW_NAME
UPDATE_INTERVAL_SECONDS
```

---

## 6. MVP Implementation Priority

기능을 구현할 때는 반드시 아래 순서를 따르세요.

1. macOS 메뉴바 앱 실행
2. Start / Stop Monitoring 기능
3. 웹캠 프레임 입력
4. pose landmark 추출
5. 자세 지표 계산
6. posture score 계산
7. face landmark 추출
8. gaze zone 추정
9. focus score 계산
10. 메뉴바 상태 업데이트
11. CSV 로그 저장
12. 디버그 화면 구현

아래 작업은 MVP 이후로 미루세요.

- 앱 패키징
- 커스텀 아이콘
- 알림 기능
- calibration UI
- 고급 분석 그래프
- 장시간 통계 dashboard
- 정확한 pixel-level gaze tracking

---

## 7. Additional Computer Vision Features

DeskPose Coach는 학습 중 사용자의 상태를 더 풍부하게 분석하기 위해 추가 컴퓨터비전 기능을 확장할 수 있습니다.

추가 기능들은 다음 원칙을 따라야 합니다.

- lightweight하게 구현하기
- MVP를 망가뜨리지 않기
- heavy model training을 도입하지 않기
- large dataset을 추가하지 않기
- rule-based 또는 simple geometric approximation을 우선하기
- 발표에서 설명 가능한 수준으로 구현하기

---

## 8. Additional Feature Priority

추가 컴퓨터비전 기능은 다음 순서로 구현하세요.

1. Head Pose Estimation
2. Coarse Gaze Zone Estimation
3. Blink / Eye Closure Detection
4. Debug Overlay Visualization
5. Face-to-Screen Distance Estimation
6. Study State Event Segmentation
7. Optional Gaze Calibration

중요:

- visual analysis pipeline이 안정적으로 동작하기 전에는 고급 report, custom icon, app packaging, notification 기능을 구현하지 마세요.
- 추가 기능은 기존 posture score / focus score pipeline과 충돌하지 않도록 작게 나누어 구현하세요.

---

## 9. Head Pose Estimation

Face landmark를 이용하여 사용자의 머리 방향을 추정합니다.

추정할 값:

- `head_yaw`
- `head_pitch`
- `head_roll`

이 값들은 사용자가 화면을 정면으로 보고 있는지, 화면 밖을 보고 있는지, 고개를 과도하게 숙이고 있는지 판단하는 데 사용합니다.

가능한 상태:

```text
Forward
Looking Left
Looking Right
Looking Down
Head Tilted
No Face
```

Implementation notes:

- Use MediaPipe face landmarks.
- Prefer simple geometric approximation first.
- Do not implement heavy 3D face reconstruction unless explicitly requested.
- Use temporal smoothing if the output is too unstable.
- Return `No Face` when face landmarks are not detected.

Expected return fields:

```python
{
    "head_yaw": float,
    "head_pitch": float,
    "head_roll": float,
    "head_state": str
}
```

---

## 10. Coarse Gaze Zone Estimation

눈 주변 landmark를 이용하여 사용자의 대략적인 시선 방향을 추정합니다.

MVP는 정확한 픽셀 단위 gaze tracking을 목표로 하지 않습니다.  
목표는 사용자의 시선 방향을 대략적인 zone으로 분류하는 것입니다.

가능한 gaze zone:

```text
Center
Left
Right
Up
Down
Away
No Face
```

Implementation notes:

- Use eye landmark ratios.
- Compare iris or eye center position relative to eye corners when available.
- Use rule-based thresholds.
- Optional calibration can be added later.
- Do not claim exact gaze tracking accuracy.
- Return `No Face` when face landmarks are not detected.

Expected return fields:

```python
{
    "gaze_zone": str,
    "eye_horizontal_ratio": float,
    "eye_vertical_ratio": float
}
```

---

## 11. Gaze Calibration

Gaze calibration은 선택 기능입니다.

사용자별 눈 모양, 카메라 위치, 화면 크기 차이를 줄이기 위해 간단한 calibration을 추가할 수 있습니다.

Suggested calibration targets:

```text
Center
Left
Right
Up
Down
```

Implementation notes:

- Store calibration data in memory first.
- File-based calibration storage is optional.
- Do not block the MVP if calibration is incomplete.
- The app should still work with default thresholds.

Possible output file:

```text
outputs/gaze_calibration.json
```

---

## 12. Blink and Eye Closure Detection

눈 landmark를 이용하여 사용자의 눈 깜빡임과 장시간 눈 감김 상태를 감지합니다.

가능한 상태:

```text
Eye Open
Blink
Long Eye Closure
Drowsy Signal
```

Implementation notes:

- Use Eye Aspect Ratio or a similar landmark-based metric.
- A short eye closure should be treated as a blink.
- A longer eye closure should be treated as a drowsiness signal.
- Use frame count or timestamp duration to distinguish blink from long eye closure.
- Avoid making medical or clinical drowsiness claims.

Expected return fields:

```python
{
    "eye_state": str,
    "eye_aspect_ratio": float,
    "blink_count": int,
    "eye_closed_duration": float
}
```

---

## 13. Face-to-Screen Distance Estimation

얼굴 landmark 또는 얼굴 bounding box의 크기를 이용하여 사용자가 화면에 너무 가까이 있는지 추정합니다.

정확한 실제 거리(cm)를 측정하지 않습니다.  
대신 웹캠 프레임 안에서 얼굴이 차지하는 상대적인 크기를 이용합니다.

사용 가능한 visual proxy:

- face bounding box width
- face bounding box height
- eye-to-eye distance
- face area ratio in frame

가능한 상태:

```text
Too Close
Normal Distance
Too Far
No Face
```

Expected return fields:

```python
{
    "distance_state": str,
    "face_width_ratio": float,
    "eye_distance": float
}
```

---

## 14. Study State Event Segmentation

프레임 단위 예측 결과를 시간 구간 단위의 study state event로 변환합니다.

가능한 event:

```text
Focused
Looking Away
Bad Posture
Drowsy
No Face
```

Implementation notes:

- Avoid logging every frame as an event.
- Start an event only when a state persists for a minimum duration.
- End the event when the state changes or returns to normal.
- Save event summaries to CSV.
- Keep the event logic simple and rule-based for the MVP.

Suggested CSV fields:

```text
start_time,end_time,event_type,duration,avg_posture_score,avg_focus_score
```

Possible output file:

```text
outputs/study_events.csv
```

---

## 15. Debug Overlay Visualization

디버그 화면에서는 웹캠 프레임 위에 분석 결과를 시각화합니다.

표시할 정보:

- Pose skeleton
- Face landmarks
- Eye landmarks
- Head pose values
- Gaze zone
- Eye state
- Posture score
- Focus score
- Current study state

Implementation notes:

- Use OpenCV drawing functions.
- Keep the overlay readable.
- Do not overcrowd the frame.
- Debug visualization should be optional.
- The app should still run without the debug window.
- The overlay should be useful for project demos and debugging.

---

## 16. Suggested Additional Files

필요하다면 다음 파일을 추가할 수 있습니다.

```text
src/head_pose_analyzer.py
src/eye_analyzer.py
src/distance_analyzer.py
src/study_event_segmenter.py
src/debug_overlay.py
```

Suggested responsibilities:

| File | Responsibility |
|---|---|
| `head_pose_analyzer.py` | Calculate yaw, pitch, roll, and classify head state |
| `eye_analyzer.py` | Detect blink, eye closure, gaze ratio, and eye state |
| `distance_analyzer.py` | Estimate relative face-to-screen distance |
| `study_event_segmenter.py` | Convert frame-level states into time-based study events |
| `debug_overlay.py` | Draw pose, face, gaze, and score information on the frame |

Keep modules small and focused.

---

## 17. Coding Rules

다음 규칙을 지켜주세요.

1. 코드는 단순하고 읽기 쉽게 작성하세요.
2. MVP 구현을 우선하세요.
3. 불필요한 dependency를 추가하지 마세요.
4. 파일 상단에는 해당 파일의 역할을 설명하는 주석을 작성하세요.
5. 중요한 계산 로직에는 짧은 주석을 추가하세요.
6. 큰 함수 하나에 모든 로직을 넣지 마세요.
7. camera, pose, face, gaze, score, UI 로직을 분리하세요.
8. output 파일은 `outputs/` 안에 저장하세요.
9. 대용량 영상 파일을 commit하지 마세요.
10. macOS에서 `python main.py`로 실행 가능해야 합니다.

---

## 18. Naming Style

명확한 영어 이름을 사용하세요.

좋은 예시:

- `posture_score`
- `focus_score`
- `neck_angle`
- `shoulder_slope`
- `torso_lean`
- `head_yaw`
- `head_pitch`
- `gaze_zone`
- `face_detected`
- `camera_worker`
- `pose_result`
- `face_result`

피해야 할 예시:

- `data`
- `result`
- `temp`
- `value`
- `thing`
- `a`
- `b`
- `x1`
- `x2`

단, 수학적 계산에서 짧은 지역 변수는 허용됩니다.

---

## 19. Execution

앱은 다음 명령어로 실행 가능해야 합니다.

```bash
python main.py
```

가상환경 사용을 전제로 합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 20. macOS Notes

웹캠이 열리지 않을 경우 macOS 카메라 권한 문제일 가능성이 큽니다.

사용자가 확인해야 할 경로:

```text
System Settings
→ Privacy & Security
→ Camera
→ Terminal 또는 사용 중인 IDE 허용
```

코드에서는 카메라가 열리지 않을 경우 적절한 에러 메시지를 출력해야 합니다.

---

## 21. CSV Logging

CSV 로그에는 가능한 한 다음 정보를 저장하세요.

- timestamp
- posture_score
- posture_status
- neck_angle
- shoulder_slope
- torso_lean
- focus_score
- focus_status
- face_detected
- gaze_zone
- head_yaw
- head_pitch

CSV 저장 경로는 기본적으로 `outputs/` 아래에 두세요.

예시:

```text
outputs/posture_focus_log.csv
```

---

## 22. Debug Window

디버그 화면에서는 다음 정보를 보여주면 좋습니다.

- webcam frame
- pose landmarks
- face landmarks
- eye landmarks
- posture score
- focus score
- gaze zone
- eye state
- current status

단, 디버그 화면은 필수 UI가 아니라 개발 및 발표 보조 기능입니다.  
메뉴바 앱의 실시간 상태 표시가 더 중요합니다.

---

## 23. Accuracy and Claim Limitations

다음과 같은 표현은 피하세요.

- 정확한 집중도 측정
- 정확한 시선 좌표 추정
- 의료용 자세 진단
- 사용자의 실제 집중 상태를 완벽히 판단
- exact gaze tracking
- medical-grade posture diagnosis
- accurate attention measurement
- clinical drowsiness detection

대신 다음 표현을 사용하세요.

- 대략적인 화면 집중도 추정
- coarse gaze zone estimation
- rule-based posture scoring
- webcam-based lightweight monitoring
- lightweight focus estimation
- visual attention proxy
- drowsiness signal
- term project MVP

The project should be described as a computer vision term project, not as a medical or psychological assessment tool.

---

## 24. Commit Message Guide

짧고 명확한 commit 메시지를 사용하세요.

좋은 예시:

- `Add menu bar app`
- `Implement webcam capture`
- `Add pose analyzer`
- `Implement posture scoring`
- `Add face analyzer`
- `Add gaze zone estimation`
- `Implement focus scoring`
- `Connect scores to menu bar`
- `Add CSV logging`
- `Add debug visualization`
- `Add head pose analyzer`
- `Add eye closure detection`

---

## 25. Final Deliverables

최종 프로젝트는 최소한 다음을 만족해야 합니다.

- `python main.py` 실행 가능
- macOS 메뉴바에 앱 표시
- Start / Stop Monitoring 가능
- 웹캠에서 프레임 입력 가능
- posture score 계산 가능
- focus score 계산 가능
- 메뉴바 title 실시간 업데이트 가능
- CSV 로그 저장 가능
- debug window 표시 가능
- README에 실행 방법과 프로젝트 설명 포함
- AGENTS.md에 coding agent 지침 포함

---

## 26. Most Important Constraints

이 프로젝트는 3일 내 완성을 목표로 하는 컴퓨터비전 텀프로젝트입니다.

완벽한 정확도보다 중요한 것은 다음입니다.

1. 실시간으로 동작하는가?
2. 웹캠 입력이 안정적으로 처리되는가?
3. 자세 분석과 집중도 분석이 분리되어 있는가?
4. 점수가 메뉴바 UI에 연결되는가?
5. 결과를 CSV로 저장할 수 있는가?
6. 결과를 발표에서 시각적으로 설명할 수 있는가?

MVP를 망가뜨릴 정도로 복잡한 기능은 추가하지 마세요.
