# Windows 설치기

목표는 Python이 없는 Windows 사용자가 `VilmLyricsAlignerSetup.exe` 하나로
독립 실행형 데스크톱 앱을 설치하고, 필요하면 DaVinci Resolve Studio 연동도 함께 구성하는 것이다.

## 설치 동작

1. 네이티브 Avalonia 데스크톱 앱 설치 준비
2. DaVinci Resolve Studio 설치 여부 확인 및 선택 연동 제공
3. NVIDIA 드라이버와 CUDA PyTorch 사용 가능성 감지
4. `%LOCALAPPDATA%\LyricsAligner`에 전용 Python 3.11과 가상환경 설치
5. 검증된 NVIDIA 환경은 CUDA 12.6 PyTorch, 나머지는 CPU 전용 PyTorch 설치
6. 고정된 앱 의존성과 Vilm Lyrics Aligner `1.0.0` 설치
7. Whisper `small`, Demucs `htdemucs`, Silero VAD 다운로드와 자체 진단
8. Resolve 연동을 선택한 경우 등록된 Python.org 3.12를 확인하고, 없으면 서명과 SHA-256을 검증한 동봉 공식 패키지 설치
9. 선택한 경우 `%PROGRAMDATA%`의 Resolve Workflow Integration 폴더에 패널 설치
10. 사용자 설정·시작 메뉴 바로가기·Windows 앱 제거 항목 등록
11. 설치용 uv 캐시 삭제

앱의 AI Python은 전용으로 유지하며 시스템 `PATH`와 `PYTHONHOME`을 변경하지 않는다.
단, Resolve 연동을 선택했고 호환 Python이 없을 때는 Resolve가 발견할 수 있는
공용 Python.org 3.12를 설치한다. 모델과 실행 장치 선택은 사용자에게 노출하지 않는다.
EXE는 부트스트랩이며 해당 PC에 필요한 AI 런타임과 모델은 설치 중 다운로드한다.

uv는 버전과 Windows x64 ZIP의 SHA-256을 고정하며, 설치기는 압축을 풀기 전에
무결성을 검증한다. 제거 프로그램은 Resolve가 실행 중이면 중단하며, 설치된
패널·전용 런타임·모델 캐시와 등록 정보를 정리한다.

## 빌드

저장소 루트에서 실행한다.

```powershell
.\installer\windows\build-installer.ps1
```

결과는 `installer\windows\dist\VilmLyricsAlignerSetup.exe` 한 파일이어야 한다.
설치기 자체는 .NET 8 WinForms 자체 포함 단일 파일이며, payload에는 .NET 8/Avalonia 자체 포함 Desktop 단일 EXE가 들어간다.

## 검증 상태

- 단일 EXE 빌드 및 내장 payload 정합성 확인
- CPU 전용 PyTorch의 격리 설치, 모델 준비, 50초 오디오 전체 파이프라인 확인
- CUDA 가능한 개발 PC의 장치 선택과 전체 파이프라인 확인
- 설치 경로 기반 모델 캐시 격리와 제거 스크립트 단위 테스트 확인
- uv 버전/해시 고정, C# 컴파일과 검사 순서 테스트 확인

아직 남은 배포 차단 항목:

- 깨끗한 Windows CPU/NVIDIA 환경의 GUI 설치→Resolve 실행→제거 E2E
- 네트워크 실패·취소·재설치 복구 검증
- 배포용 코드 서명

이 항목들을 통과하기 전에는 외부 사용자용 정식 설치판으로 취급하지 않는다.
