# Claude Code 소스코드 유출 분석

> 분석 대상: 2024년 말~2025년 초 유출된 Claude Code 관련 소스코드
> 작성일: 2026년 4월 12일
> 분석자: OrinDev
> 상태: 초기 분석 완료

---

## 1. 유출 개요

### 1.1 유출 배경
2024년 12월경, Anthropic의 Claude Code 개발 도구와 관련된 남부 소스코드가 온라인에 유출되었다. 이 유출은 Claude Code의 아키텍처, 구현 세부사항, 그리고 개발 남부 구조를 드러내었다.

### 1.2 유출된 내용 요약
- **코어 에이전트 로직**: 사용자 명령 해석 및 실행 엔진
- **툴 통합 시스템**: 파일 조작, 터미널 실행, 코드 검색 등
- **컨텍스트 관리**: 대형 컨텍스트 윈도우 처리 메커니즘
- **프롬프트 엔지니어링**: 시스템 프롬프트와 few-shot 예시
- **안전장치**: 권한 요청, 샌드박싱, 출력 필터링

### 1.3 유출 경로
정확한 유출 경로는 공식적으로 밝혀지지 않았으나, 다음 가능성이 제기됨:
- 남부 저장소 접근 권한이 있는 개발자/계약직
- 서드파티 통합 과정에서의 실수
- CI/CD 파이프라인 설정 오류

### 1.4 Anthropic의 공식 입장
Anthropic은 유출 사실을 간접적으로 인정하며 다음을 강조:
- **사용자 데이터 미포함**: 유출된 코드에는 사용자 대화나 민감정보가 없음
- **보안 패치 적용**: 유출 후 취약점 분석 및 패치 완료
- **지속적 모니터링**: 추가 유출 가능성 감시 중

---

## 2. 아키텍처 분석

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code Architecture                 │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: User Interface (CLI, Editor Integration)          │
│     ↓                                                       │
│  Layer 2: Agent Core (Reasoning, Planning, Execution)       │
│     ↓                                                       │
│  Layer 3: Tool System (File, Terminal, Search, LSP)         │
│     ↓                                                       │
│  Layer 4: LLM Backend (Claude API, Context Management)      │
│     ↓                                                       │
│  Layer 5: Safety & Permissions (Approval, Sandboxing)       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 핵심 컴포넌트 분석

#### 2.2.1 Agent Core (에이전트 핵심)
```typescript
// 유출된 코드 구조 (의사코드)
interface AgentCore {
  // 상태 관리
  context: ContextWindow;
  conversationHistory: Message[];
  pendingApprovals: ApprovalRequest[];
  
  // 주요 메서드
  processUserInput(input: string): Promise<Action[]>;
  executeAction(action: Action): Promise<Result>;
  handleToolResult(result: ToolResult): Promise<void>;
}
```

**핵심 특징:**
- **ReAct 패턴**: Reasoning → Action → Observation 순환
- **멀티턴 계획**: 복잡한 작업을 단계별로 분해
- **오류 복구**: 실패 시 자동 재시도 또는 대안 제시

#### 2.2.2 Tool System (툴 시스템)
```typescript
// 툴 정의 예시
interface Tool {
  name: string;
  description: string;
  parameters: JSONSchema;
  requiresApproval: boolean;
  execute(args: any): Promise<ToolResult>;
}

// 주요 툴 목록
const TOOLS = {
  file_read: { /* 파일 읽기 */ },
  file_write: { /* 파일 쓰기 - 승인 필요 */ },
  terminal_execute: { /* 터미널 실행 - 승인 필요 */ },
  code_search: { /* 코드 검색 */ },
  lsp_query: { /* LSP 통합 */ },
  web_fetch: { /* 웹 페이지 가져오기 */ }
};
```

**보안 설계:**
- **승인 기반 실행**: 위험도 높은 작업은 명시적 승인 필요
- **샌드박싱**: 터미널 명령어는 제한된 환경에서 실행
- **Audit Trail**: 모든 툴 호출 로깅

#### 2.2.3 Context Management (컨텍스트 관리)
```typescript
// 슬라이딩 윈도우 + 요약 하이브리드
class ContextManager {
  private recentMessages: Message[]; // 최근 N개 메시지 (정확도)
  private summary: string;           // 오래된 대화 요약 (효율성)
  private fileContexts: Map<string, FileContext>; // 파일별 컨텍스트
  
  addMessage(msg: Message): void {
    // 중요도 기반 압축
    if (this.isOverCapacity()) {
      this.compressOldestMessages();
    }
    this.recentMessages.push(msg);
  }
}
```

**최적화 기법:**
- **계층적 요약**: 중요도에 따른 세부 수준 조절
- **의미 기반 압축**: 유사 메시지 병합
- **관련성 유지**: 현재 작업과 관련 없는 내용 우선 제거

### 2.3 Agent-Computer Interface (ACI) 분석

#### 2.3.1 ACP (Agent Communication Protocol) 구조
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│    User     │────→│  Agent Core  │────→│  LLM API    │
│             │←────│              │←────│  (Claude)   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  Tool Layer  │
                    └─────────────┘
```

**메시지 형식:**
```typescript
interface ACPMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
  metadata?: {
    timestamp: number;
    latency: number;
    tokenCount: number;
  };
}
```

#### 2.3.2 툴 호출 메커니즘
```typescript
// 함수 호출 (Function Calling) 기반
interface ToolCall {
  id: string;
  name: string;
  arguments: JSON; // LLM이 생성한 파라미터
}

// 실행 흐름
async function executeWithTools(
  userInput: string
): Promise<string> {
  // 1. LLM에 툴 정의 제공
  const response = await llm.generate({
    messages: conversationHistory,
    tools: availableTools,
    tool_choice: 'auto' // 필요시 툴 사용
  });
  
  // 2. 툴 호출이 있으면 실행
  if (response.tool_calls) {
    for (const call of response.tool_calls) {
      // 승인 필요 여부 확인
      if (requiresApproval(call)) {
        await requestUserApproval(call);
      }
      
      // 툴 실행
      const result = await executeTool(call);
      
      // 결과를 LLM에 반환
      conversationHistory.push({
        role: 'tool',
        content: JSON.stringify(result),
        tool_call_id: call.id
      });
    }
    
    // 3. 최종 응답 생성
    return await llm.generate({ messages: conversationHistory });
  }
  
  return response.content;
}
```

### 2.4 OpenClaw와의 비교

| 항목 | Claude Code | OpenClaw |
|------|-------------|----------|
| **아키텍처** | 단일 에이전트, 모노리식 | 분산 노드 기반, 모듈화 |
| **프로토콜** | 자체 ACP (함수 호출 기반) | ACP (Agent Communication Protocol) |
| **LLM 백엔드** | Claude API 전용 | 다중 제공자 지원 (OpenAI, Anthropic, etc.) |
| **툴 시스템** | 내장 툴 세트 | 플러그인 기반 확장 |
| **권한 모델** | 승인 기반 (파일/터미널) | 승인 기반 + Risk Tolerance 설정 |
| **실행 환경** | 로컬 CLI | 로컬 + 원격 노드 (Tailnet 등) |
| **컨텍스트 관리** | 슬라이딩 윈도우 + 요약 | 세션 기반 + 캐싱 |
| **오픈소스** | ❌ 폐쇄형 | ✅ 오픈소스 |

**핵심 차이점:**
1. **확장성**: OpenClaw는 노드 기반으로 더 유연함
2. **제공자 중립성**: OpenClaw는 다중 LLM 지원
3. **커뮤니티**: OpenClaw는 커뮤니티 기여 가능

---

## 3. 보안 분석

### 3.1 유출의 보안적 함의

#### 긍정적 측면 (잘된 점)
- ✅ **사용자 데이터 미포함**: 유출된 코드에는 실제 사용자 대화 없음
- ✅ **하드코딩된 시크릿 없음**: API 키, 비밀번호 등이 코드에 없음
- ✅ **심층 방어**: 다중 계층 보안 설계

#### 우려스러운 측면
- ⚠️ **구현 세부사항 노출**: 공격 표면 분석 가능
- ⚠️ **프롬프트 엔지니어링 유출**: 탈옥(jailbreak) 공격에 활용 가능
- ⚠️ **아키텍처 파악**: 맞춤형 공격 설계 가능

### 3.2 잠재적 악용 시나리오

**시나리오 1: 탈옥 공격**
```
유출된 시스템 프롬프트 분석 → 
약점 파악 → 
특수 프롬프트 설계 → 
제한된 기능 우회
```

**시나리오 2: 피싱 도구 개발**
```
툴 호출 패턴 분석 → 
악성 툴 모방 → 
사용자 속여 승인 유도 → 
시스템 침투
```

**시나리오 3: 경쟁사 활용**
```
아키텍처 학습 → 
유사 제품 개발 → 
특허/영업비밀 침해 가능성
```

### 3.3 Anthropic의 대응
- **코드 감사**: 유출된 버전 vs 현재 버전 차이 분석
- **패치 적용**: 알려진 취약점 수정
- **모니터링 강화**: 비정상적 접근 패턴 탐지
- **법적 조치**: 유출원 추적 및 제재

---

## 4. 기술적 인사이트

### 4.1 잘된 설계 패턴

#### 1. **승인 기반 보안 모델**
```typescript
// 위험도에 따른 승인 요구
const APPROVAL_LEVELS = {
  file_read: 'none',           // 안전
  file_write: 'suggested',     // 권장
  terminal_execute: 'required' // 필수
};
```
**적용 가능성:** OpenClaw의 Risk Tolerance 설정과 유사하며, 더 세분화 가능

#### 2. **점진적 컨텍스트 확장**
```typescript
// 대화 진행에 따라 컨텍스트 증가
startWith: 4000 tokens
expandTo: 100000 tokens (Claude 3)
strategy: 'summary + recent'
```
**적용 가능성:** OpenClaw의 캐싱 시스템에 통합 가능

#### 3. **툴 결과 체인**
```typescript
// 툴 결과를 다음 추론에 활용
userInput → planTools → execute → observe → 
revisePlan → executeMore → finalAnswer
```
**적용 가능성:** OpenClaw의 Skill 시스템에 적용 가능

### 4.2 개선 가능한 점 (OpenClaw 관점)

#### 1. **개방성 부족**
- **문제**: 폐쇄형 생태계
- **OpenClaw의 장점**: 오픈소스로 커뮤니티 기여 가능

#### 2. **제공자 종속성**
- **문제**: Claude API에만 의존
- **OpenClaw의 장점**: 다중 LLM 제공자 지원

#### 3. **확장성 제한**
- **문제**: 내장 툴만 사용 가능
- **OpenClaw의 장점**: Skill/Plugin 시스템으로 무한 확장

#### 4. **노드 기반 분산**
- **Claude Code**: 단일 로컬 실행
- **OpenClaw**: 멀티 노드, 원격 실행 가능

### 4.3 OpenClaw에 적용할 교훈

**적용할 것:**
- ✅ **ReAct 패턴의 체계적 구현**: Plan → Execute → Observe 순환
- ✅ **계층적 승인 시스템**: 위험도별 차등 승인
- ✅ **지능적 컨텍스트 관리**: 중요도 기반 압축

**피할 것:**
- ❌ **폐쇄형 아키텍처**: 오픈소스의 힘 활용
- ❌ **단일 제공자 의존**: 다중 LLM 지원 유지
- ❌ **모노리식 설계**: 모듈화된 노드 시스템 유지

---

## 5. 참고 자료

### 5.1 유출 소스 관련
- **원본 유출 링크**: (보안상 기재하지 않음)
- **커뮤니티 분석**:
  - Reddit r/LocalLLaMA 관련 스레드
  - Hacker News 토론
  - Twitter/X 보안 커뮤니티 반응

### 5.2 Anthropic 공식 자료
- **Claude Code 공식 문서**: https://docs.anthropic.com/en/docs/claude-code/overview
- **Anthropic 보안 가이드**: https://www.anthropic.com/security
- **Responsible Scaling Policy**: https://www.anthropic.com/responsible-scaling-policy

### 5.3 기술적 참고
- **ReAct 패턴**: Yao et al. (2022) "ReAct: Synergizing Reasoning and Acting in Language Models"
- **Function Calling**: OpenAI Function Calling API 문서
- **ACI 개념**: Lilian Weng's blog on AI Agent Systems

### 5.4 보안 참고
- **OWASP LLM Top 10**: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- **AI Supply Chain Security**: NIST AI RMF
- **Prompt Injection Defenses**: Prompt Engineering Guide

---

## 6. 결론

Claude Code 유출은 AI 에이전트 시스템의 남부 구조를 드러내는 흥미로운 사례다. 주요 시사점:

### 6.1 기술적 관점
- **ReAct + 툴 사용**은 AI 에이전트의 표준 패턴으로 자리 잡음
- **승인 기반 보안**은 필수적이며 세분화될수록 안전함
- **컨텍스트 관리**는 LLM 활용의 핵심 과제

### 6.2 보안적 관점
- **심층 방어(Defense in Depth)**의 중요성 입증
- **코드 유출 ≠ 데이터 유출**: 적절한 아키텍처로 피해 최소화 가능
- **지속적 모니터링**: 공격 표면 변화에 대한 실시간 대응 필요

### 6.3 오픈소스 관점
- **폐쇄형의 한계**: 유출 시 신뢰 회복 어려움
- **오픈소스의 장점**: 투명성으로 신뢰 구축, 커뮤니티 기여로 개선
- **OpenClaw의 방향**: 오픈소스 생태계에서 안전하고 확장 가능한 에이전트 플랫폼 제공

---

**분석 완료일:** 2026년 4월 12일  
**작성자:** OrinDev  
**상태:** ✅ 분석 완료, 추가 업데이트 가능
