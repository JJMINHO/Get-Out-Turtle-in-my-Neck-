# DeskPose Coach

DeskPose Coach is a macOS menu bar application that analyzes sitting posture in real time using computer vision.

The app captures webcam frames, estimates body landmarks with MediaPipe Pose, calculates posture-related angles such as neck tilt, shoulder slope, and torso lean, and updates the macOS menu bar status based on the user's posture score.

## Features

- Real-time webcam-based posture monitoring
- Pose landmark extraction using MediaPipe
- Neck angle, shoulder slope, and torso lean calculation
- Rule-based posture scoring
- macOS menu bar status display
- CSV logging for posture analysis

## Tech Stack

- Python
- OpenCV
- MediaPipe
- NumPy
- rumps
- macOS

## Project Structure

deskpose-coach/
- main.py
- requirements.txt
- README.md
- src/
- outputs/
- assets/
- docs/

## Goal

The goal of this project is to build a lightweight computer vision system that provides real-time posture feedback through the macOS menu bar.
