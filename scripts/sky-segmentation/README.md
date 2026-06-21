# Sky Segmentation Training Pipeline

learnLLM의 sky-segmentation 프로젝트를 위한 end-to-end 학습 파이프라인 스크립트 모음입니다.

## 프로젝트 개요

**목표:** 모바일 기기에서 실시간으로 동작하는 하늘 분할(sky segmentation) 모델 개발

**핵심 요구사항:**
- 저VRAM, 저지연, 저전력
- 90%+ mIoU 정확도
- 실시간 inference (모바일 기준)

**참고 프로젝트:** [sky-segmentation](https://github.com/Stellar-Image-Revision/sky-segmentation)

---

## 디렉토리 구조

```
scripts/sky-segmentation/
├── data/
│   └── sam_pseudo_label.py       # SAM 기반 pseudo-labeling
├── training/
│   └── train_segmentation.py     # 모델 학습 스크립트
├── evaluation/
│   └── evaluate.py               # 종합 평가 스크립트
├── optimization/
│   └── quantize_and_profile.py   # 양자화 및 프로파일링
└── README.md
```

---

## Phase 1: Dataset Preparation

### 1.1 SAM Pseudo-labeling

SAM(Segment Anything Model)을 사용하여 하늘 마스크를 생성하거나 기존 라벨을 정제합니다.

```bash
# 새로운 마스크 생성 (자동 포인트 샘플링)
python data/sam_pseudo_label.py \
    --input-dir ./raw_images \
    --output-dir ./masks \
    --method auto

# 기존 라벨 정제
python data/sam_pseudo_label.py \
    --input-dir ./raw_images \
    --output-dir ./masks_refined \
    --refine

# SAM 2 사용 (더 높은 품질)
python data/sam_pseudo_label.py \
    --input-dir ./raw_images \
    --output-dir ./masks \
    --model-type vit_h \
    --checkpoint sam_vit_h.pth
```

**주요 기능:**
- Automatic sky detection (top portion point sampling)
- Manual point/box prompt 지원
- Existing mask refinement
- Quality check (sky ratio filtering)

---

## Phase 2: Model Training

### 2.1 지원 모델

| 모델 | Backbone | 특징 | 권장 용도 |
|------|----------|------|-----------|
| DeepLabV3+ | MobileNetV3 | 안정적, 검증됨 | 베이스라인 |
| Fast-SCNN | Custom | 초저지연 | 실시간 앱 |
| BiSeNetV2 | Custom | bilateral guidance | 고품질 경계 |
| SegFormer-B0 | MiT | Transformer | 높은 정확도 |

### 2.2 학습 실행

```bash
# DeepLabV3+MobileNetV3 학습
python training/train_segmentation.py \
    --model deeplabv3_mobilenet \
    --data-dir ./data \
    --output-dir ./checkpoints/deeplabv3 \
    --epochs 100 \
    --batch-size 16 \
    --lr 0.01 \
    --pretrained

# Fast-SCNN 학습 (빠른 실험)
python training/train_segmentation.py \
    --model fast_scnn \
    --data-dir ./data \
    --output-dir ./checkpoints/fast_scnn \
    --epochs 50 \
    --batch-size 32 \
    --lr 0.045

# SegFormer-B0 학습 (높은 정확도)
python training/train_segmentation.py \
    --model segformer_b0 \
    --data-dir ./data \
    --output-dir ./checkpoints/segformer \
    --epochs 100 \
    --lr 0.00006 \
    --optimizer adamw \
    --scheduler cosine_warmup
```

**학습 설정:**
- Optimizer: SGD (momentum=0.9) 또는 AdamW
- LR Schedule: Poly (기본), Cosine Annealing, Cosine with Warmup
- Loss: CrossEntropy (기본), CE+Dice
- Augmentation: Random flip, rotation, color jitter

---

## Phase 3: Evaluation

### 3.1 종합 평가

4가지 메트릭으로 평가합니다:

```bash
python evaluation/evaluate.py \
    --model-path ./checkpoints/best_model.pth \
    --model-name deeplabv3_mobilenet \
    --data-dir ./data \
    --split test
```

**평가 메트릭:**

| 메트릭 | 설명 | 중요도 |
|--------|------|--------|
| mIoU | 클래스별 IoU 평균 | 기본 정확도 |
| Boundary IoU | 경계 영역 IoU | 구름/나무 경계 |
| HD95 | Hausdorff Distance 95% | 최악의 케이스 |
| Gradient Error | Gradient magnitude L1 | Soft boundary quality |

---

## Phase 4: Mobile Optimization

### 4.1 양자화 및 프로파일링

```bash
# 기본 프로파일링
python optimization/quantize_and_profile.py \
    --model-path ./checkpoints/best_model.pth \
    --model-name deeplabv3_mobilenet \
    --output-dir ./optimized

# INT8 정적 양자화
python optimization/quantize_and_profile.py \
    --model-path ./checkpoints/best_model.pth \
    --model-name deeplabv3_mobilenet \
    --data-dir ./data \
    --quantize \
    --quantization-type static \
    --export-onnx

# ONNX 변환만
python optimization/quantize_and_profile.py \
    --model-name fast_scnn \
    --export-onnx \
    --output-dir ./optimized
```

**출력:**
- `baseline_profile.json`: FP32 모델 정보
- `quantized_profile.json`: INT8 모델 정보 (speedup 포함)
- `model.onnx`: ONNX 포맷 모델

---

## 데이터셋 통합 포맷

모든 데이터셋은 다음 unified format으로 변환되어야 합니다:

```
data/
├── images/
│   ├── image_001.jpg
│   ├── image_002.jpg
│   └── ...
├── masks/
│   ├── image_001_mask.png
│   ├── image_002_mask.png
│   └── ...
└── splits.json
```

**splits.json 예시:**
```json
{
  "train": [
    {"image": "images/image_001.jpg", "mask": "masks/image_001_mask.png", "source": "ade20k"},
    ...
  ],
  "val": [...],
  "test": [...]
}
```

---

## Requirements

```bash
# 기본
pip install torch torchvision

# SAM
pip install segment-anything

# Transformers (SegFormer)
pip install transformers

# 평가/시각화
pip install scikit-image scipy Pillow tqdm

# 프로파일링
pip install thop

# ONNX
pip install onnx onnxruntime
```

---

## 참고 이슈

- [#18: FLOPs ↓ Accuracy ↑ (90%+) Mobile Segmentation Models](../../issues/18)
- [#19: Segmentation Model Fine-tuning & Training Pipeline](../../issues/19)

---

## 라이선스

스크립트는 sky-segmentation 프로젝트의 학습/배포 목적으로 작성되었습니다.
