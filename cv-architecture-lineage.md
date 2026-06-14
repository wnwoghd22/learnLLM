# Computer Vision Architecture Lineage

> From ResNet to EfficientNet, and from CNN to Transformer/ViT hybrid architectures.

---

## Part 1: CNN 계열 (ResNet → DenseNet → SENet → MobileNet → EfficientNet)

### 1. ResNet (Residual Learning, He et al., 2016)

**핵심 문제:** Deeper but not Better — 네트워크가 깊어질수록 성능이 저하

**극복 기술:** Shortcut connection (Skip connection)

**성능 향상 원인 분석:**
- Vanishing gradient 해결이 아님 (BN만으로 충분)
- **Dynamical Isometry** — Jacobian 값을 1로 유지하여 정보 전파 보장
  - "Resurrecting the sigmoid in deep learning through dynamical isometry: theory and practice" (2017)의 이론적 기반

---

### 2. DenseNet (Huang et al., 2017)

**핵심 문제:** ResNet의 단순 add 방식의 정보 흐름 한계

**극복 기술:** Densely Connected — 각 layer가 앞의 모든 layer의 출력을 concat으로 받음

**장단점:**
- 장점: Better performance through feature reuse
- 단점: Memory overhead — concat으로 인한 메모리 증가

---

### 3. SENet (Squeeze-and-Excitation Networks, Hu et al., 2018)

**핵심 문제:** 모든 channel이 동등한 중요도를 가진다는 가정의 비효율성

**극복 기술:** Squeeze & Excitation
- **Squeeze:** Global Information Embedding (Global Average Pooling)
- **Excitation:** Adaptive Recalibration — channel-wise attention을 통한 중요도 재조정

**의미:** "Some channels are more important than others"

---

### 4. MobileNet (Howard et al., 2017)

**핵심 문제:** CNN의 computational efficiency

**극복 기술:**
- Depthwise-Pointwise Convolution (Separable Convolution)
- Inverted bottleneck

**목표:** Edge device에서의 효율적인 inference

---

### 5. EfficientNet (Tan & Le, 2019)

**핵심 문제:** Scale의 황금비 — width, depth, resolution의 최적 조합

**극복 기술:** Compound Scaling

**아키텍처 구성:**
- MBConv (MobileNet의 Inverted bottleneck)
- S & E (SENet의 Squeeze-and-Excitation)
- Compound scale method (width × depth × resolution의 균형 잡힌 scaling)

---

## Part 2: Transformer 계열 및 CNN-ViT 혼합

### 1. Mean Field / Signal Propagation (Transformer 버전)

#### Attention is Not All You Need (Dong et al., ICML 2021)
- **핵심:** Skip connection과 MLP가 없으면 attention만으로 표현이 rank-1로 붕괴
- **의미:** Transformer 이론의 출발점

#### Signal Propagation in Transformers (Noci et al., NeurIPS 2022)
- **핵심:** Rank collapse와 gradient vanishing을 연결한 mean-field 분석

#### Deep Transformers without Shortcuts (He et al., ICLR 2023)
- **핵심:** Skip/LN 없이도 학습되도록 attention 커널을 교정
- **의미:** "Resurrecting the Sigmoid"의 정신적 후속작

#### The Shaped Transformer (Noci et al., NeurIPS 2023)
- **핵심:** Depth/width 동시 극한에서의 SDE 분석

#### Geometric Dynamics of Signal Propagation (Cowsik et al., 2024)
- **핵심:** Ganguli 그룹의 Transformer판 edge-of-chaos
- **의미:** Poole/Schoenholz 계보의 정통 후속

#### Infinite Attention (Hron et al., ICML 2020)
- **핵심:** Attention의 무한폭 커널 극한 (NNGP/NTK)

---

### 2. Identity Matters (Transformer 버전)

#### On Layer Normalization in the Transformer Architecture (Xiong et al., ICML 2020)
- **핵심:** Pre-LN vs Post-LN의 gradient 스케일 분석
- **의미:** He et al. ECCV 2016 (Identity Mappings)의 Transformer 버전

#### Understanding the Difficulty of Training Transformers (Liu et al., EMNLP 2020)
- **핵심:** Admin init, residual branch의 분산 증폭 분석

#### Fixup Initialization (Zhang et al., ICLR 2019)
- **핵심:** Normalization 없이 identity 근방에서 시작

#### ReZero (Bachlechner et al., 2021)
- **핵심:** Residual connection을 학습 가능한 스케일로 초기화

#### T-Fixup (Huang et al., ICML 2020)
- **핵심:** Transformer에 특화된 Fixup 변형

#### Batch Normalization Biases Residual Blocks (De & Smith, NeurIPS 2020)
- **핵심:** BN+ResNet이 잘 되는 이유가 identity bias
- **의미:** MBConv 계열에 직접 적용되는 이론

#### Stable ResNet (Hayou et al., AISTATS 2021)
- **핵심:** Residual branch를 1/√L로 스케일링

#### DeepNet (Wang et al., 2022)
- **핵심:** 1,000층 Transformer를 위한 스케일링

---

### 3. Dynamical Isometry / 안정성

#### The Lipschitz Constant of Self-Attention (Kim et al., ICML 2021)
- **핵심:** Dot-product attention은 Lipschitz가 아님

#### Stabilizing Transformer Training (Zhai et al., ICML 2023)
- **핵심:** σReparam으로 attention entropy 붕괴 방지

#### Deep Kernel Shaping (Martens et al., 2021)
- **핵심:** Skip도 norm도 없이 깊은 망 학습

#### Deep Learning without Shortcuts (Zhang et al., ICLR 2022)
- **핵심:** Kernel shaping을 통한 vanilla network 학습

#### Small-Scale Proxies for Large-Scale Instabilities (Wortsman et al., 2023)
- **핵심:** Logit 발산, attention entropy 붕괴 등 체계적 정리

---

### 4. Loss Landscape (ViT/ConvNet 버전)

#### How Do Vision Transformers Work? (Park & Kim, ICLR 2022)
- **핵심:** Hessian 스펙트럼, landscape 시각화로 MSA vs Conv 비교
- **의미:** Li et al. 2018 (Visualizing Loss Landscape)의 ViT 버전

#### When Vision Transformers Outperform ResNets (Chen et al., ICLR 2022)
- **핵심:** ViT landscape가 더 sharp, SAM이 이를 보정

#### Gradient Descent at the Edge of Stability (Cohen et al., ICLR 2021)
- **핵심:** Landscape와 최적화 동역학의 연결

#### A Loss Curvature Perspective (Gilmer et al., ICLR 2022)
- **핵심:** Training instability의 curvature 분석

---

### 5. 스케일링 이론 (보너스)

#### Tensor Programs IV/V/VI (Yang & Hu; μP/μTransfer)
- **핵심:** Mean field 이론의 현대적 완성형

#### The Principles of Deep Learning Theory (Roberts et al., 2022)
- **핵심:** Residual network 챕터가 전체를 통일

#### MBConv: Signal Propagation in Unnormalized ResNets (Brock et al., ICLR 2021)
- **핵심:** MBConv의 signal propagation 분석

---

## 전체 계보적 연결

```
[Part 1: CNN]
ResNet (Skip, Dynamical Isometry)
    ↓
DenseNet (Dense concat)
    ↓
SENet (Channel attention)
    ↓
MobileNet (Depthwise separable)
    ↓
EfficientNet (Compound scaling)

[Part 2: Transformer]
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

*Part 1 내용은 CNN review.pptx를 참고하여 정리되었습니다.*  
*Part 2 내용은 이슈 #17 댓글에서 상세 분석을 확인할 수 있습니다.*
