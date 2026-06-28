# Sky Segmentation 시스템 설계

> 관련 이슈: [#18 (모델 조사)](https://github.com/wnwoghd22/learnLLM/issues/18) · [#19 (학습 파이프라인)](https://github.com/wnwoghd22/learnLLM/issues/19) · [#20 (데이터셋 수집)](https://github.com/wnwoghd22/learnLLM/issues/20)

## 개요

`Stellar-Image-Revision/sky-segmentation` 레포지터리를 기반으로, 모델 교체, 데이터셋 준비, 학습/검증 자동화가 가능한 시스템을 구축한다.

### 현재 상태

- **레포:** `sky-segmentation` (`feature/mobile-net-v3` 브랜치)
- **학습 환경:** pixi (Python 3.10, PyTorch 2.7.1+cu128)
- **GPU:** orin(jetson) ↔ 99번 단말(Windows, RTX 4060 Ti) SSH 연결
- **모델:** MobileNetV3 + LR-ASPP (고정)
- **데이터셋:** COCO-Stuff sky subset (고정)
- **검증:** IoU만 측정
- **학습 스크립트:** `src/model/mobilenetv3/train.py` (모델별로 분리되어 있음)

### 워크플로우

```
orin (jetson)                    GitHub                    99번 (Windows agent)
┌──────────────────┐          ┌──────────┐              ┌────────────────────┐
│ 코드 수정         │ --push→  │  remote  │  ←pull--    │ pixi run train     │
│ 모델/데이터 추가  │           │  repo    │              │ --model X          │
└──────────────────┘          └──────────┘              │ --data-dir Y       │
                                                         │ → validate         │
                                                         │ → evaluate report  │
                                                         └────────────────────┘
```

orin에서 SSH로 99번 단말에 접속하여 `git pull` → 학습 → 검증을 트리거한다.

---

## 1. 모델 스위칭 시스템 (이슈 #18)

### 목표

`--model` CLI 인자 하나로 lightweight segmentation 모델을 교체할 수 있도록 한다.

### 대상 모델

| 모델 | 백본 | 특징 | 비고 |
|------|------|------|------|
| MobileNetV3 + LR-ASPP | MobileNetV3 | 현재 기준 모델 | 구현 완료 |
| Fast-SCNN | Custom | 두 경로(below/above) 구조 | BMVC 2019 |
| BiSeNetV2 | Custom | 양방향 경로 + attention | IJCV 2021 |
| DDRNet | Custom | Deep Dual-Resolution | T-ITS 2022 |
| PIDNet | Custom | 3-branch (P/I/D) | CVPR 2023 |
| SegFormer-B0 | MiT-B0 | Transformer 기반 | NeurIPS 2021 |

### 디렉토리 구조

```
src/model/
├── __init__.py          # 모델 registry 및 공용 인터페이스
├── base.py              # BaseSegmentor (공용 인터페이스 정의)
├── registry.py          # 모델 등록/조회
├── mobilenetv3/
│   ├── __init__.py
│   └── model.py
├── fast_scnn/
│   ├── __init__.py
│   └── model.py
├── bisenetv2/
│   ├── __init__.py
│   └── model.py
├── ddrnet/
│   ├── __init__.py
│   └── model.py
├── pidnet/
│   ├── __init__.py
│   └── model.py
└── segformer/
    ├── __init__.py
    └── model.py
```

### 공용 인터페이스

```python
# src/model/base.py
class BaseSegmentor(nn.Module):
    def __init__(self, num_classes: int = 1, **kwargs): ...
    def forward(self, x: Tensor) -> Tensor: ...  # [B, 1, H, W] logits
    @property
    def params_count(self) -> float: ...  # M params
    @property
    def flops_estimate(self) -> float: ...  # GFLOPs (input 512x512 기준)
```

### CLI 사용 예

```bash
# 모델 교체만으로 실험 가능
pixi run train --model fast_scnn --epochs 30
pixi run train --model segformer_b0 --epochs 50 --lr 6e-5
pixi run train --model pidnet --loss focal_dice --crop 512
```

---

## 2. 데이터셋 파이프라인 (이슈 #19, #20)

### 목표

多来源 데이터셋을 통합 포맷으로 변환하고, SAM 기반 boundary refinement를 옵션으로 제공한다.

### 통합 포맷

```
datasets/unified/
├── manifest.json        # 모든 샘플 메타데이터
├── images/
│   ├── coco_000001.jpg
│   ├── ade20k_000123.jpg
│   └── ...
└── masks/
    ├── coco_000001.png  # uint8, 0=non-sky / 255=sky
    ├── ade20k_000123.png
    └── ...
```

**manifest.json 스키마:**

```json
{
  "samples": [
    {
      "id": "coco_000001",
      "source": "coco-stuff",
      "image": "images/coco_000001.jpg",
      "mask": "masks/coco_000001.png",
      "split": "train",
      "width": 640,
      "height": 480
    }
  ],
  "splits": { "train": 8000, "val": 500, "test": 500 }
}
```

### 변환 스크립트

```
scripts/data_prep/
├── convert_coco.py          # COCO-Stuff → 통합 포맷
├── convert_ade20k.py        # ADE20K sky 클래스 추출
├── convert_cityscapes.py    # Cityscapes sky
├── convert_skyfinder.py     # SkyFinder
├── convert_swimseg.py       # SWIMSEG
├── sam_refine.py            # SAM/SAM2 boundary refinement
└── build_unified.py         # 여러 소스를 통합 manifest로 병합
```

### SAM Pseudo-labeling

- **기존 라벨이 있는 경우:** mask를 SAM prompt로 사용하여 boundary refinement
- **라벨이 없는 경우:** text/box prompt("sky")로 자동 마스크 생성
- **품질 필터링:** low-light, 과도한 occlusion 케이스 제거

### CLI 사용 예

```bash
# 개별 데이터셋 변환
pixi run -e data python scripts/data_prep/convert_coco.py --out datasets/unified
pixi run -e data python scripts/data_prep/convert_ade20k.py --out datasets/unified

# 통합 manifest 생성
pixi run -e data python scripts/data_prep/build_unified.py --dir datasets/unified

# SAM boundary refinement (옵션)
pixi run -e data python scripts/data_prep/sam_refine.py --input datasets/unified --model sam2
```

---

## 3. 학습/검증 자동화 (이슈 #19)

### 목표

학습 완료 후 자동으로 검증을 수행하고, 다양한 메트릭을 리포트한다.

### 스크립트 구조

```
scripts/
├── train.py               # 공용 학습 스크립트
├── validate.py             # 독립 검증 스크립트
├── evaluate.py             # 다양한 메트릭 계산
└── run_experiment.py       # 학습 → 검증 → 리포트 자동화
```

### 메트릭 확장

| 메트릭 | 용도 | 비고 |
|--------|------|------|
| mIoU | 전체 정확도 | 현재 구현됨 |
| Boundary IoU | 경계 정밀도 (구름, 나뭇가지) | wispy edges |
| HD95 | Hausdorff Distance 95% | 경계 거리 기반 |
| F1 / Dice | 픽셀 단위 정밀도/재현율 | |
| Gradient Error | soft boundary 품질 | |

### 학습 스크립트 (공용)

```bash
# 학습
pixi run train \
  --model fast_scnn \
  --data-dir datasets/unified \
  --loss focal_dice \
  --epochs 30 \
  --batch-size 16 \
  --crop 512 \
  --lr 1e-3 \
  --out runs

# 학습 중 TensorBoard 모니터링 (99번 단말에서)
pixi run tb  # port 3124
```

### 검증 스크립트 (독립)

```bash
# 학습된 체크포인트로 검증
pixi run validate \
  --checkpoint runs/fast_scnn_focal_dice_20260628/best.pt \
  --data-dir datasets/unified \
  --split test

# 상세 평가 리포트
pixi run evaluate \
  --checkpoint runs/fast_scnn_focal_dice_20260628/best.pt \
  --data-dir datasets/unified \
  --split test \
  --metrics all
```

### 실험 자동화

```bash
# 학습 → 검증 → 리포트를 한 번에
pixi run experiment \
  --model fast_scnn \
  --data-dir datasets/unified \
  --epochs 30 \
  --loss focal_dice
```

출력:
```
runs/fast_scnn_focal_dice_20260628-200000/
├── best.pt
├── last.pt
├── events.out.tfevents.*  # TensorBoard
├── report.json             # 메트릭 요약
└── report.md               # 사람용 리포트
```

---

## 4. Mobile Optimization (이슈 #19, Phase 3)

### 목표

학습된 모델을 모바일 배포용으로 최적화한다.

### 스크립트

```
scripts/optimize/
├── quantize.py             # INT8 양자화
├── distill.py              # Knowledge distillation
├── profile.py              # FLOPs, params, latency 측정
└── export_onnx.py          # ONNX 내보내기
```

### CLI 사용 예

```bash
# 양자화
pixi run optimize scripts/optimize/quantize.py --checkpoint runs/.../best.pt

# 프로파일링
pixi run optimize scripts/optimize/profile.py --model fast_scnn --input 512

# ONNX 내보내기
pixi run optimize scripts/optimize/export_onnx.py --checkpoint runs/.../best.pt
```

---

## 5. SSH 트리거 자동화

### orin → 99번 단말 학습 트리거

```bash
# orin에서 실행
ssh agent@172.30.1.99 'cd %USERPROFILE%\Documents\Github\sky-segmentation && \
  git pull origin feature/mobile-net-v3 && \
  pixi run -e default python -m scripts.train \
    --model mobilenetv3 \
    --epochs 30 \
    --loss bce_dice && \
  pixi run -e default python -m scripts.validate \
    --checkpoint runs/latest/best.pt \
    --split test'
```

### TensorBoard 원격 접근

99번 단말의 3124 포트를 orin에서 포워딩:

```bash
# orin에서 SSH 터널링
ssh -L 3124:localhost:3124 agent@172.30.1.99
# 브라우저에서 localhost:3124 접속
```

---

## 우선순위

| 단계 | 내용 | 관련 이슈 | 상태 |
|------|------|-----------|------|
| 0 | 현재 MobileNetV3 학습 돌리기 (환경 검증) | — | 대기 |
| 1 | 모델 스위칭 시스템 (registry + 공용 train.py) | #18 | 미시작 |
| 2 | 검증 메트릭 확장 (Boundary IoU, HD95, F1) | #19 | 미시작 |
| 3 | 데이터셋 변환 스크립트 (통합 포맷) | #20 | 미시작 |
| 4 | 학습→검증 자동화 스크립트 | #19 | 미시작 |
| 5 | SAM pseudo-labeling 파이프라인 | #19 | 미시작 |
| 6 | Mobile optimization (quantization, profiling) | #19 | 미시작 |

---

## 환경 정보

| 항목 | orin (jetson) | 99번 (Windows) |
|------|---------------|----------------|
| IP | 172.30.1.100 | 172.30.1.99 |
| OS | Ubuntu (arm64) | Windows 11 |
| GPU | jetson 내장 | RTX 4060 Ti (8GB) |
| 역할 | 코드 수정, 트리거 | GPU 학습, 검증 |
| SSH | — | agent 계정 접속 (공개키 인증) |
| Python | — | 3.14 (시스템) / 3.10 (pixi 환경) |
| CUDA | — | 13.1 (드라이버), 12.8 (PyTorch) |

---

_2026-06-28 작성_