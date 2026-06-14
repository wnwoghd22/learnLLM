# Transformer 및 CNN-ViT 혼합 아키텍처 이론 계보

> ResNet-DenseNet-SENet-MobileNet-EfficientNet 계보에 이어, Transformer 계열 및 CNN+ViT 혼합 아키텍처의 이론적 기반을 정리합니다.

---

## 1. Mean Field / Signal Propagation (Transformer 버전)

### Attention is Not All You Need (Dong et al., ICML 2021)
- **핵심:** Skip connection과 MLP가 없으면 attention만으로 표현이 rank-1로 붕괴
- **의미:** Transformer 이론의 출발점. Attention 자체만으로는 깊은 층을 쌓을 수 없음

### Signal Propagation in Transformers (Noci et al., NeurIPS 2022)
- **핵심:** Rank collapse와 gradient vanishing을 연결한 mean-field 분석
- **의미:** ResNet의 signal propagation 이론이 Transformer로 확장

### Deep Transformers without Shortcuts (He et al., ICLR 2023)
- **핵심:** Skip/LN 없이도 학습되도록 attention 커널을 교정
- **의미:** "Resurrecting the Sigmoid"의 정신적 후속작

### The Shaped Transformer (Noci et al., NeurIPS 2023)
- **핵심:** Depth/width 동시 극한에서의 SDE 분석
- **의미:** Mean field 이론의 현대적 확장

### Geometric Dynamics of Signal Propagation (Cowsik et al., 2024)
- **핵심:** Ganguli 그룹의 Transformer판 edge-of-chaos
- **의미:** Poole/Schoenholz 계보의 정통 후속

### Infinite Attention (Hron et al., ICML 2020)
- **핵심:** Attention의 무한폭 커널 극한 (NNGP/NTK)
- **의미:** CNN NNGP/NTK 이론의 Transformer 확장

---

## 2. Identity Matters (Transformer 버전)

### On Layer Normalization in the Transformer Architecture (Xiong et al., ICML 2020)
- **핵심:** Pre-LN vs Post-LN의 gradient 스케일 분석
- **의미:** He et al. ECCV 2016 (Identity Mappings)의 Transformer 버전

### Understanding the Difficulty of Training Transformers (Liu et al., EMNLP 2020)
- **핵심:** Admin init, residual branch의 분산 증폭 분석
- **의미:** Transformer training instability의 이론적 분석

### Fixup Initialization (Zhang et al., ICLR 2019)
- **핵심:** Normalization 없이 identity 근방에서 시작
- **의미:** ResNet의 초기화 이론이 Transformer로 확장

### ReZero (Bachlechner et al., 2021)
- **핵심:** Residual connection을 학습 가능한 스케일로 초기화
- **의미:** Skip connection의 중요성을 이론적으로 뒷받침

### T-Fixup (Huang et al., ICML 2020)
- **핵심:** Transformer에 특화된 Fixup 변형
- **의미:** Identity initialization의 Transformer 적용

### Batch Normalization Biases Residual Blocks (De & Smith, NeurIPS 2020)
- **핵심:** BN+ResNet이 잘 되는 이유가 identity bias
- **의미:** MBConv 계열(ResNet+BN 상속)에 직접 적용되는 이론

### Stable ResNet (Hayou et al., AISTATS 2021)
- **핵심:** Residual branch를 1/√L로 스케일링하는 이론적 근거
- **의미:** Deep network의 안정적 학습 조건

### DeepNet (Wang et al., 2022)
- **핵심:** 1,000층 Transformer를 위한 스케일링
- **의미:** 위 이론들의 대규모 실전판

---

## 3. Dynamical Isometry / 안정성

### The Lipschitz Constant of Self-Attention (Kim et al., ICML 2021)
- **핵심:** Dot-product attention은 Lipschitz가 아님
- **의미:** Attention이 conv와 근본적으로 다른 지점

### Stabilizing Transformer Training (Zhai et al., ICML 2023)
- **핵심:** σReparam으로 attention entropy 붕괴 방지
- **의미:** 실전 안정성 기법의 이론적 근거

### Deep Kernel Shaping (Martens et al., 2021)
- **핵심:** Skip도 norm도 없이 깊은 망 학습
- **의미:** Dynamical isometry 프로그램의 집대성

### Deep Learning without Shortcuts (Zhang et al., ICLR 2022)
- **핵심:** Kernel shaping을 통한 vanilla network 학습
- **의미:** ResNet 없이도 깊은 망 학습 가능

### Small-Scale Proxies for Large-Scale Transformer Instabilities (Wortsman et al., 2023)
- **핵심:** Logit 발산, attention entropy 붕괴 등 체계적 정리
- **의미:** 실전 불안정성의 분류

---

## 4. Loss Landscape (ViT/ConvNet 버전)

### How Do Vision Transformers Work? (Park & Kim, ICLR 2022)
- **핵심:** Hessian 스펙트럼, landscape 시각화로 MSA vs Conv 비교
- **의미:** Li et al. 2018 (Visualizing Loss Landscape)의 ViT 버전

### When Vision Transformers Outperform ResNets (Chen et al., ICLR 2022)
- **핵심:** ViT landscape가 더 sharp, SAM이 이를 보정
- **의미:** Sharp landscape와 generalization의 관계

### Gradient Descent at the Edge of Stability (Cohen et al., ICLR 2021)
- **핵심:** Landscape와 최적화 동역학의 연결
- **의미:** Modern optimization theory

### A Loss Curvature Perspective (Gilmer et al., ICLR 2022)
- **핵심:** Training instability의 curvature 분석
- **의미:** Landscape 기반 training 분석

---

## 5. 스케일링 이론 (보너스)

### Tensor Programs IV/V/VI (Yang & Hu; μP/μTransfer)
- **핵심:** Mean field 이론의 현대적 완성형
- **의미:** 위 모든 이론들의 수렴점

### The Principles of Deep Learning Theory (Roberts et al., 2022)
- **핵심:** 책. Residual network 챕터가 전체를 통일
- **의미:** Mean field theory의 교과서

### MBConv: Signal Propagation in Unnormalized ResNets (Brock et al., ICLR 2021)
- **핵심:** MBConv의 signal propagation 분석
- **의미:** EfficientNet/MobileNet의 이론적 기반

---

## 계보적 연결

```
CNN Mean Field (Poole 2016, Schoenholz 2017)
    ↓
ResNet Signal Propagation (Yang 2017, Xiao 2018)
    ↓
Transformer Signal Propagation (Dong 2021, Noci 2022)
    ↓
Geometric Dynamics (Cowsik 2024)

ResNet Identity (He 2016)
    ↓
Transformer Normalization (Xiong 2020, Liu 2020)
    ↓
DeepNet (Wang 2022)

Dynamical Isometry (Xiao 2018)
    ↓
Deep Kernel Shaping (Martens 2021)
    ↓
Transformer Stability (Zhai 2023)

Loss Landscape (Li 2018)
    ↓
ViT Landscape (Park 2022)
    ↓
Edge of Stability (Cohen 2021)
```

---

*이 문서는 이론적 계보를 따라 정리한 것이며, 각 논문의 상세 분석은 이슈 #17 댓글에서 확인할 수 있습니다.*
