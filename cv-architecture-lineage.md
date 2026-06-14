# Computer Vision Architecture Lineage

> From ResNet to EfficientNet, and from CNN to Transformer/ViT hybrid architectures.

---

## Part 1: CNN 계열 (ResNet → DenseNet → SENet → MobileNet → EfficientNet)

### 1. ResNet (Residual Learning, He et al., 2016)

**핵심 문제:** Deeper but not Better — 네트워크가 깊어질수록 성능이 저하

**극복 기술:** Shortcut connection (Skip connection)

**설명/근거:**
- Vanishing gradient 해결이 아님 (BN만으로 충분)
- **Dynamical Isometry** — Jacobian 값을 1로 유지하여 정보 전파 보장
  - "Resurrecting the sigmoid in deep learning through dynamical isometry: theory and practice" (2017)의 이론적 기반

---

### 2. DenseNet (Huang et al., 2017)

**핵심 문제:** ResNet의 단순 add 방식의 정보 흐름 한계

**극복 기술:** Densely Connected — 각 layer가 앞의 모든 layer의 출력을 concat으로 받음

**설명/근거:**
- 장점: Better performance through feature reuse
- 단점: Memory overhead — concat으로 인한 메모리 증가

---

### 3. SENet (Squeeze-and-Excitation Networks, Hu et al., 2018)

**핵심 문제:** 모든 channel이 동등한 중요도를 가진다는 가정의 비효율성

**극복 기술:** Squeeze & Excitation

**설명/근거:**
- **Squeeze:** Global Information Embedding (Global Average Pooling) — 전체 공간 정보를 하나의 값으로 압축
- **Excitation:** Adaptive Recalibration — channel-wise attention을 통해 중요한 채널을 강조, 덜 중요한 채널을 억제
- 직관: "Some channels are more important than others"

---

### 4. MobileNet (Howard et al., 2017; Sandler et al., 2018)

**핵심 문제:** Standard CNN은 computational cost가 너무 높아 edge device에서 실용적이지 않음

**극복 기술:** Depthwise-Pointwise Convolution (Separable Convolution)

**설명/근거:**
- **Standard Conv:** FLOPs = D_K × D_K × M × N × D_F × D_F (공간 + 채널 동시 처리)
- **Depthwise Separable:** FLOPs = (D_K × D_K × M × D_F × D_F) + (M × N × D_F × D_F) (공간과 채널 분리 처리)
- **→ 약 8~9배 FLOPs 감소**
- **Inverted Bottleneck (MobileNetV2):** ResNet bottleneck은 "compress → process → expand"인데, MobileNetV2는 "expand → process → compress"
  - **왜 inverted인가?** ReLU가 낮은 차원(thin representation)에서 정보를 더 많이 잃기 때문. 높은 차원에서 ReLU를 쓰고, projection 전에는 linear activation (non-linearity 제거)로 정보 보존

---

### 5. EfficientNet (Tan & Le, ICML 2019)

**핵심 문제:** Width, depth, resolution 중 하나만 scale하면 효과가 빠르게 포화됨

**극복 기술:** Compound Scaling

**설명/근거:**
- **Width↑만:** receptive field는 고정, 표현력은 제한 (underfitting)
- **Depth↑만:** gradient vanishing, inference cost 급증
- **Resolution↑만:** width/depth가 따라가지 못하면 fine detail을 잡을 수 없음
- **Compound Scaling:** width, depth, resolution을 동시에 균형 있게 증가
  - depth: d = α^φ, width: w = β^φ, resolution: r = γ^φ
  - φ는 compound coefficient, α, β, γ는 grid search로 찾은 상수 (α·β²·γ² ≈ 2)
- **Architecture:** MnasNet (Tan et al., CVPR 2019)의 NAS로 찾은 baseline (multi-objective: accuracy + latency)
  - MBConv (MobileNetV2의 inverted bottleneck) + SE (SENet의 squeeze-and-excitation)

---

## Part 2: Transformer 계열 및 CNN-ViT 혼합

### 1. Mean Field / Signal Propagation (Transformer 버전)

#### Attention is Not All You Need (Dong et al., ICML 2021)

**핵심 문제:** Attention만으로 깊은 네트워크를 쌓으면 표현력이 붕괴하는가?

**극복 기술:** Skip connection + MLP의 필수성 이론적 입증

**설명/근거:**
- **Rank collapse proof:** Skip connection과 MLP가 없으면 attention만으로는 깊은 층을 거치며 표현이 rank-1로 붕괴
- **의미:** Transformer 이론의 출발점. Attention 자체만으로는 정보 전파 불가

---

#### Signal Propagation in Transformers (Noci et al., NeurIPS 2022)

**핵심 문제:** Transformer의 signal propagation이 어떻게 작동하고, 어디서 gradient가 소실되는가?

**극복 기술:** Mean field analysis로 rank collapse와 gradient vanishing 연결

**설명/근거:**
- ResNet의 signal propagation 이론(Poole/Schoenholz)을 Transformer로 확장
- **Rank collapse → gradient vanishing:** 표현의 rank가 붕괴하면 backward pass에서 gradient도 vanishing
- Layer normalization의 역할을 수학적으로 정량화

---

#### Deep Transformers without Shortcuts (He et al., ICLR 2023)

**핵심 문제:** Skip connection과 LayerNorm 없이도 Transformer를 학습할 수 있는가?

**극복 기술:** Attention kernel을 교정하여 skip/LN 없이도 학습되도록 구조 변경

**설명/근거:**
- **"Resurrecting the Sigmoid"의 정신적 후속:** Dynamical isometry의 아이디어를 Transformer attention에 적용
- Attention kernel을 수정하여 signal propagation이 깊은 층에서도 붕괴하지 않도록 설계
- **의미:** Skip connection이 없어도 깊은 망을 학습할 수 있는 조건을 제시

---

#### The Shaped Transformer (Noci et al., NeurIPS 2023)

**핵심 문제:** Depth와 width가 동시에 증가할 때의 극한 동작은 어떻게 되는가?

**극복 기술:** SDE (Stochastic Differential Equation) 분석으로 depth/width 동시 극한에서의 거동 분석

**설명/근거:**
- **Mean field → SDE:** 단일 극한(mean field)을 넘어 동시 극한에서의 stochastic behavior 분석
- Scaling law의 이론적 기반 제공: width↑와 depth↑가 상호작용하는 방식 수학적 정리
- **의미:** 현대 large model scaling의 이론적 토대

---

#### Geometric Dynamics of Signal Propagation (Cowsik et al., 2024)

**핵심 문제:** Transformer의 edge-of-chaos는 CNN과 어떻게 다른가?

**극복 기술:** Geometric dynamics framework로 Transformer-specific signal propagation 분석

**설명/근거:**
- **Ganguli 그룹의 직계 후속:** Poole/Schoenholz의 CNN edge-of-chaos를 Transformer에 확장
- **Trainability prediction:** Signal propagation의 geometric property로 학습 가능성 예측
- **의미:** CNN과 Transformer의 근본적 차이를 signal propagation 관점에서 통일

---

#### Infinite Attention (Hron et al., ICML 2020)

**핵심 문제:** Attention의 무한폭 극한에서는 어떤 kernel이 나오는가?

**극복 기술:** NNGP (Neural Network Gaussian Process)와 NTK (Neural Tangent Kernel)를 attention에 적용

**설명/근거:**
- **Attention kernel limit:** Width → ∞일 때 attention의 kernel을 닫힌 형태로 도출
- **CNN NNGP/NTK의 Transformer 확장:** Lee et al. (2018)의 CNN 무한폭 이론을 attention mechanism에 일반화
- **의미:** Attention의 Bayesian interpretation과 optimization dynamics 이론적 기반

---

### 2. Identity Matters (Transformer 버전)

#### On Layer Normalization in the Transformer Architecture (Xiong et al., ICML 2020)

**핵심 문제:** Pre-LN vs Post-LN, 왜 하나는 학습되고 하나는 폭발하는가?

**극복 기술:** Layer normalization의 위치(placement)에 따른 gradient 스케일 분석

**설명/근거:**
- **Post-LN (원본 Transformer):** Gradient가 residual branch를 타고 exponential하게 증폭 → 폭발
- **Pre-LN:** Gradient가 LayerNorm에 의해 안정화. Residual path의 gradient scale이 O(1)로 유지
- **의미:** He et al. ECCV 2016 (Identity Mappings)의 Transformer 버전. Identity mapping의 역할을 정량화

---

#### Understanding the Difficulty of Training Transformers (Liu et al., EMNLP 2020)

**핵심 문제:** Transformer가 왜 ResNet보다 학습이 어려운가?

**극복 기술:** Admin initialization + residual branch의 분산 증폭 분석

**설명/근거:**
- **Residual branch의 분산 증폭:** Transformer의 residual branch가 깊어질수록 출력 분산이 exponential하게 증가
- **Admin init:** Xavier/He initialization을 수정하여 residual branch의 분산을 1로 유지
- **의미:** Initialization이 Transformer training의 핵심 bottleneck임을 입증

---

#### Fixup Initialization (Zhang et al., ICLR 2019)

**핵심 문제:** Normalization 없이도 깊은 네트워크를 학습할 수 있는가?

**극복 기술:** Identity 근방에서 시작하는 scaling-aware initialization

**설명/근거:**
- **ResNet의 scaling 문제:** Plain ResNet은 initialization만으로도 gradient vanishing/exploding
- **Fixup:** Residual branch의 초기 scale을 0에 가깝게 시작하여, 학습 초기에 network가 거의 identity function처럼 동작
- **의미:** Normalization이 없어도 깊은 망을 학습할 수 있는 조건 제시

---

#### ReZero (Bachlechner et al., 2021)

**핵심 문제:** Residual connection의 초기 스케일을 어떻게 자동으로 조절할까?

**극복 기술:** Residual connection을 학습 가능한 스케일 파라미터로 초기화

**설명/근거:**
- **Residual scaling:** 각 residual branch마다 학습 가능한 스칼라를 곱하고, 초기값을 0으로 설정
- **초기 학습 안정성:** 초기에는 residual branch가 무시되고, 점차적으로 학습되어 정보가 흐름
- **의미:** Skip connection의 중요성을 이론적으로 뒷받침, DeepNet의 전신

---

#### T-Fixup (Huang et al., ICML 2020)

**핵심 문제:** Transformer에 특화된 Fixup은 어떻게 설계하는가?

**극복 기술:** Transformer architecture에 맞춘 scaling-aware initialization

**설명/근거:**
- **Attention-specific scaling:** Attention의 dot-product 특성에 맞춘 variance 분석
- **T-Fixup scaling:** Word embedding, attention, FFN 각각에 다른 scaling factor 적용
- **의미:** Fixup의 Transformer 버전, layer normalization 없이 학습 가능

---

#### Batch Normalization Biases Residual Blocks (De & Smith, NeurIPS 2020)

**핵심 문제:** BN + ResNet이 왜 plain network보다 월등히 잘 되는가? 진짜 이유가 무엇인가?

**극복 기술:** BN의 identity bias 효과 분석

**설명/근거:**
- **BN의 hidden effect:** Batch Normalization이 residual branch의 평균을 0, 분산을 1로 맞추면서, **residual branch가 identity mapping에서 크게 벗어나지 않도록 편향**
- **Identity bias:** Residual branch의 output이 작은 값으로 유지되어, 전체 network가 identity 근처에서 동작 → 학습 안정성
- **의미:** MBConv 계열(ResNet+BN을 상속)의 이론적 기반. EfficientNet의 성능 원인 중 하나

---

#### Stable ResNet (Hayou et al., AISTATS 2021)

**핵심 문제:** ResNet을 아주 깊게 쌓으면서도 안정화하려면 어떤 조건이 필요한가?

**극복 기술:** Residual branch를 1/√L로 스케일링

**설명/근거:**
- **Mean field stability:** Layer 수 L이 증가할 때 gradient가 폭발하지 않도록 residual branch의 기여를 1/√L로 축소
- **의미:** Arbitrary depth로의 scaling 이론적 기반. DeepNet의 이론적 근거

---

#### DeepNet (Wang et al., 2022)

**핵심 문제:** 1,000층 Transformer를 어떻게 학습할 수 있는가?

**극복 기술:** Deep scaling + residual scaling의 결합

**설명/근거:**
- **Deep scaling:** LayerNorm을 residual branch에도 적용하여 gradient를 안정화
- **Residual scaling:** Residual branch의 초기 scale을 작게 시작하여 정보 전파 보장
- **의미:** 위의 이론들(Fixup, ReZero, Stable ResNet)의 대규모 실전판. 1,000층 Transformer 학습 성공

---

### 3. Dynamical Isometry / 안정성

#### The Lipschitz Constant of Self-Attention (Kim et al., ICML 2021)

**핵심 문제:** Attention의 gradient가 안정적인가? Lipschitz constant는 어떻게 되는가?

**극복 기술:** Dot-product attention의 Lipschitz constant 분석

**설명/근거:**
- **결과:** Dot-product attention은 **Lipschitz가 아님** (unbounded)
- **의미:** Attention의 query-key dot-product가 값이 커질 때 gradient가 폭발할 수 있음 → Conv와 근본적으로 다른 안정성 특성
- **Practical implication:** Gradient clipping, scaled attention의 필요성

---

#### Stabilizing Transformer Training (Zhai et al., ICML 2023)

**핵심 문제:** Attention의 entropy가 붕괴하면 학습이 어떻게 망가지는가?

**극복 기술:** σReparam (spectral reparameterization)으로 attention entropy 붕괴 방지

**설명/근거:**
- **Attention entropy collapse:** Attention weights가 one-hot에 가까워지면 gradient vanishing
- **σReparam:** Weight matrix의 spectral norm을 제한하여 attention의 분산을 통제
- **의미:** Attention의 entropy를 안정화하는 practical technique에 이론적 근거

---

#### Deep Kernel Shaping (Martens et al., 2021)

**핵심 문제:** Skip connection 없이, normalization 없이 깊은 망을 학습할 수 있는가?

**극복 기술:** Kernel shaping을 통해 dynamical isometry 달성

**설명/근거:**
- **Kernel shaping:** Activation function의 statistical properties를 조절하여 Jacobian의 singular values를 1로 유지
- **Dynamical isometry without shortcuts:** Skip connection이나 BN 없이도 깊은 층을 통과해도 정보가 붕괴하지 않도록 설계
- **의미:** Schoenholz/Yang의 edge-of-chaos 프로그램의 집대성

---

#### Deep Learning without Shortcuts (Zhang et al., ICLR 2022)

**핵심 문제:** Vanilla deep network (no skip, no norm)도 학습 가능한가?

**극복 기술:** Deep kernel shaping의 practical implementation

**설명/근거:**
- **No shortcuts needed:** Martens et al.의 이론을 실제 네트워크에 적용
- **Activation shaping:** Deep network의 activation statistics를 조절하는 구체적 기법 제시
- **의미:** ResNet의 skip connection이 필수적이지 않을 수도 있다는 이론적 가능성 제시

---

#### Small-Scale Proxies for Large-Scale Instabilities (Wortsman et al., 2023)

**핵심 문제:** 대규모 Transformer의 학습 불안정성은 어떤 종류가 있고, 어떻게 조기 발견할 수 있는가?

**극복 기술:** Small-scale model에서의 불안정성 proxy 체계적 정리

**설명/근거:**
- **Taxonomy of instabilities:**
  - Logit divergence (loss가 NaN으로 발산)
  - Attention entropy collapse (attention weights가 극단적으로 치우침)
  - Gradient norm explosion
- **Small-scale proxy:** 작은 모델에서의 불안정성이 큰 모델에서도 동일하게 나타남을 입증 → early detection 가능
- **의미:** Large model training의 불안정성을 체계적으로 분류하고 예방

---

### 4. Loss Landscape (ViT/ConvNet 버전)

#### How Do Vision Transformers Work? (Park & Kim, ICLR 2022)

**핵심 문제:** ViT와 ConvNet의 loss landscape는 어떻게 다른가? MSA vs Conv의 본질적 차이는?

**극복 기술:** Hessian 스펙트럼과 landscape 시각화로 MSA vs Conv 비교

**설명/근거:**
- **Hessian spectrum:** ViT의 loss landscape는 ConvNet보다 더 **sharp** (Hessian의 큰 eigenvalue가 더 큼)
- **MSA의 영향:** Multi-head self-attention이 Hessian의 spectral norm을 키움 → optimization에 더 민감
- **의미:** Li et al. 2018 (Visualizing Loss Landscape)의 ViT 버전. ConvNeXt의 질문에도 직접 닿는 분석

---

#### When Vision Transformers Outperform ResNets (Chen et al., ICLR 2022)

**핵심 문제:** ViT가 왜 ResNet보다 generalization이 어려운가? 어떻게 보정할 수 있는가?

**극복 기술:** Sharp landscape 분석 + SAM (Sharpness-Aware Minimization) 적용

**설명/근거:**
- **Sharp landscape:** ViT는 loss landscape가 더 sharp하여 flat minimum을 찾기 어려움
- **SAM:** Sharpness-aware objective를 최소화하여 flat minimum으로 이동 → ViT의 generalization 향상
- **의미:** Landscape geometry가 generalization에 미치는 영향을 ViT에 적용

---

#### Gradient Descent at the Edge of Stability (Cohen et al., ICLR 2021)

**핵심 문제:** Gradient descent는 실제로 어떤 dynamics로 작동하는가? Step size와 curvature의 상호작용은?

**극복 기술:** Edge of stability 현상의 체계적 분석

**설명/근거:**
- **Edge of stability:** Gradient descent는 learning rate가 stability threshold를 넘어도 divergence하지 않고, edge에서 oscillate하며 학습
- **Non-convex dynamics:** Sharp minimum에서도 escape하고, flat minimum으로 이동하는 메커니즘
- **의미:** Modern optimization theory의 핵심. Li et al. 2018의 landscape 분석과 연결

---

#### A Loss Curvature Perspective (Gilmer et al., ICLR 2022)

**핵심 문제:** Loss curvature가 training instability에 어떻게 기여하는가?

**극복 기술:** Curvature 분석으로 instability mechanism 파악

**설명/근거:**
- **Curvature → instability:** Loss의 high curvature region에서 gradient가 불안정하게 변동
- **Practical insight:** Gradient clipping, learning rate scheduling의 이론적 근거
- **의미:** Cohen et al. 2021의 edge of stability와 연결된 현대적 관점

---

### 5. 스케일링 이론 (보너스)

#### Tensor Programs IV/V/VI (Yang & Hu; μP/μTransfer)

**핵심 문제:** Mean field 이론들의 현대적 통일된 프레임워크는 무엇인가? Width, depth, parameterization의 관계는?

**극복 기술:** μP (maximal update parameterization)와 μTransfer

**설명/근거:**
- **μP:** Width가 변할 때 learning rate를 어떻게 scale해야 hyperparameter transfer가 가능한지를 수학적으로 정의
- **μTransfer:** Small model에서 찾은 optimal hyperparameter가 large model에서도 동일하게 작동
- **Tensor Programs VI (depth-μP):** Depth scaling까지 포함한 완전한 프레임워크
- **의미:** 위의 모든 mean field 이론들의 수렴점. Large model training의 이론적 기반

---

#### The Principles of Deep Learning Theory (Roberts et al., 2022)

**핵심 문제:** 위의 모든 이론들을 하나의 통일된 언어로 어떻게 다룰 수 있는가?

**극복 기술:** Residual network theory를 중심으로 한 통일된 이론 프레임워크

**설명/근거:**
- **Book format:** 이론의 교과서. Infinite-width, infinite-depth, kernel methods, signal propagation 등을 통일
- **Residual network chapter:** ResNet의 이론을 중심으로 CNN, Transformer의 공통 구조를 다룸
- **의미:** 위의 이론들의 통합적 이해를 위한 참고서

---

#### MBConv: Signal Propagation in Unnormalized ResNets (Brock et al., ICLR 2021)

**핵심 문제:** MBConv (MobileNetV2 + SE)의 signal propagation은 어떤 형태인가? EfficientNet의 이론적 기반은?

**극복 기술:** MBConv block의 signal propagation 분석

**설명/근거:**
- **MBConv analysis:** Inverted bottleneck + SE block의 mean field 동작 분석
- **Unnormalized ResNet:** BN 없이도 dynamical isometry를 유지하는 조건
- **의미:** EfficientNet의 MBConv 블록이 왜 효과적인지 이론적 설명. Compound scaling의 이론적 기반

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
MobileNet (Depthwise separable, Inverted bottleneck)
    ↓
EfficientNet (Compound scaling, MBConv+SE)

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

[Scaling Theory]
All above → Tensor Programs μP (Yang & Hu) → Unified framework
```

---

*Part 1 내용은 CNN review.pptx를 참고하여 정리되었습니다.*  
*Part 2 내용은 이슈 #17 댓글에서 상세 분석을 확인할 수 있습니다.*
