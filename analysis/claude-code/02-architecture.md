# 2. Claude Code 아키텍처 심층 분석

> Claude Code의 내부 구조와 설계 패턴에 대한 상세 분석

---

## 2.1 전체 아키텍처 개요

### 레이어 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Layer 1: User Interface                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   CLI        │  │   VS Code    │  │   JetBrains  │              │
│  │   Interface  │  │   Extension  │  │   Plugin     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Layer 2: Agent Core                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Reasoning Engine → Planning Module → Execution Engine      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Layer 3: Tool System                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  File    │ │ Terminal │ │  Search  │ │   LSP    │ │   Web    │  │
│  │  Tools   │ │  Tools   │ │  Tools   │ │  Tools   │ │  Tools   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Layer 4: LLM Backend                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           Claude API Integration & Context Management       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Layer 5: Safety & Permissions                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Approval   │  │  Sandboxing  │  │   Audit      │              │
│  │   System     │  │   Engine     │  │   Logging    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2.2 Agent Core (에이전트 핵심) 상세 분석

### 2.2.1 ReAct 패턴 구현

Claude Code는 **ReAct (Reasoning + Acting)** 패턴을 핵심 설계 철학으로 채택했다.

```typescript
// ReAct 순환 구조
interface ReActLoop {
  // 1. Reasoning: 상황 분석 및 계획 수립
  reason(context: Context): Plan;
  
  // 2. Acting: 계획 실행 (툴 호출)
  act(plan: Plan): Action[];
  
  // 3. Observation: 결과 관찰 및 학습
  observe(results: Result[]): Observation;
  
  // 4. 반복 또는 종료
  shouldContinue(obs: Observation): boolean;
}

// 실제 구현 예시 (의사코드)
class AgentCore {
  async processUserInput(input: string): Promise<string> {
    const conversation: Message[] = [];
    
    while (true) {
      // Reasoning
      const reasoning = await this.llm.generate({
        messages: [...conversation, { role: 'user', content: input }],
        system: SYSTEM_PROMPT_REACT
      });
      
      // Acting
      if (reasoning.tool_calls) {
        const results = await this.executeTools(reasoning.tool_calls);
        conversation.push({
          role: 'assistant',
          content: reasoning.content,
          tool_calls: reasoning.tool_calls
        });
        
        // Observation
        for (const result of results) {
          conversation.push({
            role: 'tool',
            content: JSON.stringify(result),
            tool_call_id: result.call_id
          });
        }
      } else {
        // 종료 조건: 툴 호출 없음
        return reasoning.content;
      }
      
      // 안전장치: 최대 반복 횟수
      if (conversation.length > MAX_ITERATIONS * 2) {
        throw new Error('Max iterations exceeded');
      }
    }
  }
}
```

### 2.2.2 상태 관리 시스템

```typescript
// 전체 상태 구조
interface AgentState {
  // 대화 관련
  conversation: {
    history: Message[];
    currentTurn: number;
    pendingApprovals: ApprovalRequest[];
  };
  
  // 컨텍스트 관련
  context: {
    window: ContextWindow;
    fileCache: Map<string, FileContext>;
    userPreferences: UserPreferences;
  };
  
  // 실행 관련
  execution: {
    activeTools: Map<string, ToolExecution>;
    queuedActions: Action[];
    completedTasks: TaskResult[];
  };
  
  // 메타데이터
  meta: {
    sessionId: string;
    startTime: number;
    lastActivity: number;
  };
}

// 상태 전이 관리
class StateManager {
  private state: AgentState;
  private subscribers: Set<StateSubscriber>;
  
  transition(event: StateEvent): void {
    const newState = this.computeNextState(this.state, event);
    this.notifySubscribers(newState);
    this.state = newState;
  }
  
  private computeNextState(current: AgentState, event: StateEvent): AgentState {
    // 상태 전이 로직
    switch (event.type) {
      case 'USER_INPUT':
        return this.handleUserInput(current, event);
      case 'TOOL_COMPLETE':
        return this.handleToolComplete(current, event);
      case 'APPROVAL_GRANTED':
        return this.handleApproval(current, event);
      // ... 더 많은 이벤트 타입
    }
  }
}
```

### 2.2.3 오류 복구 메커니즘

```typescript
// 오류 처리 전략
interface ErrorRecovery {
  // 오류 분류
  classify(error: Error): ErrorType;
  
  // 복구 전략 선택
  selectStrategy(type: ErrorType): RecoveryStrategy;
  
  // 복구 실행
  execute(strategy: RecoveryStrategy): Promise<RecoveryResult>;
}

// 구현 예시
enum ErrorType {
  TRANSIENT = 'transient',      // 일시적 오류 (재시도 가능)
  PERMISSION = 'permission',    // 권한 오류 (승인 필요)
  SYNTAX = 'syntax',           // 구문 오류 (코드 수정 필요)
  TIMEOUT = 'timeout',         // 시간 초과
  FATAL = 'fatal'              // 치명적 오류
}

class ErrorRecoveryManager {
  async handleError(error: Error, context: ExecutionContext): Promise<RecoveryResult> {
    const errorType = this.classifyError(error);
    
    switch (errorType) {
      case ErrorType.TRANSIENT:
        // 지수 백오프 재시도
        return await this.retryWithBackoff(context);
        
      case ErrorType.PERMISSION:
        // 사용자 승인 요청
        return await this.requestApproval(context);
        
      case ErrorType.SYNTAX:
        // LLM에게 오류 설명 및 수정 요청
        return await this.requestFix(context, error);
        
      case ErrorType.TIMEOUT:
        // 작업 분할 및 재시도
        return await this.splitAndRetry(context);
        
      case ErrorType.FATAL:
        // 실행 중단 및 사용자 알림
        return await this.abortAndNotify(context, error);
    }
  }
}
```

---

## 2.3 Tool System (툴 시스템) 심층 분석

### 2.3.1 툴 아키텍처

```typescript
// 툴 정의 인터페이스
interface ToolDefinition {
  name: string;
  description: string;
  parameters: JSONSchema;
  
  // 보안 설정
  security: {
    requiresApproval: boolean | ApprovalCondition;
    sandboxLevel: SandboxLevel;
    auditLevel: AuditLevel;
  };
  
  // 실행 설정
  execution: {
    timeout: number;
    retryPolicy: RetryPolicy;
    maxConcurrency: number;
  };
}

// 툴 실행 컨텍스트
interface ToolContext {
  workingDirectory: string;
  environment: Map<string, string>;
  fileSystem: FileSystemAdapter;
  network: NetworkAdapter;
  userSession: UserSession;
}
```

### 2.3.2 주요 툴 상세 분석

#### File Tools (파일 조작)

```typescript
// 파일 읽기 툴
const fileReadTool: ToolDefinition = {
  name: 'file_read',
  description: 'Read contents of a file',
  parameters: {
    type: 'object',
    properties: {
      path: { type: 'string', description: 'File path' },
      offset: { type: 'number', description: 'Start line (1-indexed)' },
      limit: { type: 'number', description: 'Max lines to read' }
    },
    required: ['path']
  },
  security: {
    requiresApproval: false,
    sandboxLevel: 'readonly',
    auditLevel: 'low'
  },
  execution: {
    timeout: 5000,
    retryPolicy: { maxRetries: 2, backoff: 'exponential' },
    maxConcurrency: 10
  }
};

// 파일 쓰기 툴
const fileWriteTool: ToolDefinition = {
  name: 'file_write',
  description: 'Write content to a file',
  parameters: {
    type: 'object',
    properties: {
      path: { type: 'string' },
      content: { type: 'string' },
      createParents: { type: 'boolean' }
    },
    required: ['path', 'content']
  },
  security: {
    requiresApproval: true, // ⚠️ 항상 승인 필요
    sandboxLevel: 'standard',
    auditLevel: 'high'
  }
};
```

#### Terminal Tools (터미널 실행)

```typescript
const terminalExecuteTool: ToolDefinition = {
  name: 'terminal_execute',
  description: 'Execute shell commands',
  parameters: {
    type: 'object',
    properties: {
      command: { type: 'string' },
      workingDir: { type: 'string' },
      timeout: { type: 'number' }
    },
    required: ['command']
  },
  security: {
    requiresApproval: (args) => {
      // 위험한 명령어 자동 감지
      const dangerousPatterns = [
        /rm\s+-rf/i,
        />\s*\/dev\//,
        /curl.*\|.*sh/,
        /wget.*-O-\s*\|/
      ];
      return dangerousPatterns.some(p => p.test(args.command));
    },
    sandboxLevel: 'restricted',
    auditLevel: 'critical'
  }
};
```

#### Search Tools (코드 검색)

```typescript
const codeSearchTool: ToolDefinition = {
  name: 'code_search',
  description: 'Search code using various methods',
  parameters: {
    type: 'object',
    properties: {
      query: { type: 'string' },
      method: { 
        enum: ['grep', 'semantic', 'ast', 'symbol'],
        description: 'Search method'
      },
      path: { type: 'string' },
      filePattern: { type: 'string' }
    }
  }
};

// 검색 메서드별 구현
interface SearchImplementations {
  grep: GrepSearcher;      // 텍스트 기반 검색
  semantic: VectorSearcher; // 의미 기반 검색
  ast: ASTSearcher;        // AST 기반 검색
  symbol: SymbolSearcher;  // 심볼 기반 검색
}
```

### 2.3.3 툴 오케스트레이션

```typescript
// 툴 의존성 그래프
interface ToolDependencyGraph {
  nodes: Map<string, ToolNode>;
  edges: ToolEdge[];
}

// 병렬 실행 관리
class ToolOrchestrator {
  async executeTools(calls: ToolCall[]): Promise<ToolResult[]> {
    // 의존성 분석
    const graph = this.buildDependencyGraph(calls);
    
    // 토폴로지 정렬로 실행 순서 결정
    const executionOrder = this.topologicalSort(graph);
    
    // 병렬 실행 가능한 툴 그룹화
    const parallelGroups = this.groupByLevel(executionOrder);
    
    // 순차적 병렬 실행
    const results: ToolResult[] = [];
    for (const group of parallelGroups) {
      const groupResults = await Promise.all(
        group.map(call => this.executeSingleTool(call))
      );
      results.push(...groupResults);
    }
    
    return results;
  }
}
```

---

## 2.4 Context Management (컨텍스트 관리) 심층 분석

### 2.4.1 하이브리드 컨텍스트 구조

```typescript
// Claude Code의 컨텍스트 관리 전략
class HybridContextManager {
  // 레이어 1: 최근 메시지 (정확도 우선)
  private recentMessages: Message[];
  private readonly RECENT_COUNT = 20;
  
  // 레이어 2: 요약 (효율성 우선)
  private summary: ConversationSummary;
  private readonly SUMMARY_INTERVAL = 10;
  
  // 레이어 3: 파일 컨텍스트 (프로젝트 이해)
  private fileContexts: Map<string, FileContext>;
  
  // 레이어 4: 장기 기억 (중요 정보)
  private longTermMemory: LongTermMemory;

  addMessage(msg: Message): void {
    this.recentMessages.push(msg);
    
    // 토큰 예산 체크
    if (this.getTokenCount() > TOKEN_BUDGET) {
      this.compressContext();
    }
    
    // 주기적 요약 생성
    if (this.recentMessages.length % this.SUMMARY_INTERVAL === 0) {
      this.updateSummary();
    }
  }
}
```

### 2.4.2 중요도 기반 압축

```typescript
interface ImportanceScorer {
  // 메시지 중요도 계산
  score(message: Message): number;
}

class SemanticImportanceScorer implements ImportanceScorer {
  score(message: Message): number {
    let score = 0;
    
    // 1. 사용자意図 관련성
    if (this.isUserIntent(message)) score += 10;
    
    // 2. 작업 완료 여부
    if (this.isTaskCompletion(message)) score += 8;
    
    // 3. 오류/예외 정보
    if (this.isError(message)) score += 7;
    
    // 4. 파일 변경사항
    if (this.hasFileChanges(message)) score += 6;
    
    // 5. 툴 실행 결과
    if (this.hasToolResults(message)) score += 4;
    
    return score;
  }
}

// 압축 전략
class ContextCompressor {
  compress(context: ContextWindow, targetTokens: number): ContextWindow {
    // 1. 중요도 점수 계산
    const scoredMessages = context.messages.map(m => ({
      message: m,
      score: this.importanceScorer.score(m)
    }));
    
    // 2. 점수 기반 정렬
    scoredMessages.sort((a, b) => b.score - a.score);
    
    // 3. 하위 점수 메시지 요약
    const toSummarize = scoredMessages.slice(targetTokens / 2);
    const summary = this.summarize(toSummarize.map(s => s.message));
    
    // 4. 상위 점수 메시지 유지 + 요약 결합
    const keepMessages = scoredMessages
      .slice(0, targetTokens / 2)
      .map(s => s.message);
    
    return {
      messages: [...keepMessages, summary],
      tokenCount: this.countTokens([...keepMessages, summary])
    };
  }
}
```

### 2.4.3 파일 컨텍스트 캐싱

```typescript
interface FileContext {
  path: string;
  content: string;
  summary: string;
  symbols: Symbol[];
  lastAccessed: number;
  accessCount: number;
}

class FileContextCache {
  private cache: LRUCache<string, FileContext>;
  private readonly MAX_SIZE = 50; // 최대 50개 파일
  
  async getFileContext(path: string): Promise<FileContext> {
    // 캐시 히트
    if (this.cache.has(path)) {
      const context = this.cache.get(path)!;
      context.lastAccessed = Date.now();
      context.accessCount++;
      return context;
    }
    
    // 캐시 미스: 파일 읽기 및 분석
    const content = await this.readFile(path);
    const context = await this.analyzeFile(path, content);
    
    this.cache.set(path, context);
    return context;
  }
  
  private async analyzeFile(path: string, content: string): Promise<FileContext> {
    return {
      path,
      content: content.slice(0, 10000), // 처음 10000자만
      summary: await this.generateSummary(content),
      symbols: await this.extractSymbols(content),
      lastAccessed: Date.now(),
      accessCount: 1
    };
  }
}
```

---

## 2.5 Agent-Computer Interface (ACI) 프로토콜

### 2.5.1 ACP 메시지 형식

```typescript
// Claude Code Protocol (ACP) 메시지 구조
interface ACPMessage {
  // 메시지 식별
  id: string;
  role: 'system' | 'user' | 'assistant' | 'tool';
  
  // 핵심 내용
  content: string;
  
  // 툴 관련
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
  
  // 메타데이터
  metadata: {
    timestamp: number;
    latency: number;
    tokenCount: number;
    model: string;
    version: string;
  };
  
  // 확장 필드
  extensions?: {
    reasoning?: string;       // 사고 과정
    confidence?: number;      // 신뢰도
    alternatives?: string[];  // 대안 제안
  };
}

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  timestamp: number;
}

interface ToolResult {
  call_id: string;
  status: 'success' | 'error' | 'timeout';
  content: any;
  executionTime: number;
  metadata?: Record<string, any>;
}
```

### 2.5.2 툴 호출 메커니즘

```typescript
class ToolCallingEngine {
  async executeWithTools(
    userInput: string,
    availableTools: ToolDefinition[]
  ): Promise<ACPMessage> {
    const conversation: ACPMessage[] = [];
    let iterations = 0;
    const MAX_ITERATIONS = 10;
    
    while (iterations < MAX_ITERATIONS) {
      iterations++;
      
      // 1. LLM에 툴 정의 제공 및 응답 생성
      const response = await this.llm.generate({
        messages: conversation,
        tools: availableTools,
        tool_choice: 'auto'
      });
      
      // 2. 툴 호출 처리
      if (response.tool_calls && response.tool_calls.length > 0) {
        conversation.push({
          id: generateId(),
          role: 'assistant',
          content: response.content,
          tool_calls: response.tool_calls,
          metadata: { timestamp: Date.now() }
        });
        
        // 3. 각 툴 실행
        for (const call of response.tool_calls) {
          // 승인 필요 여부 확인
          if (await this.requiresApproval(call)) {
            const approved = await this.requestUserApproval(call);
            if (!approved) {
              conversation.push({
                id: generateId(),
                role: 'tool',
                tool_results: [{
                  call_id: call.id,
                  status: 'error',
                  content: 'User denied approval',
                  executionTime: 0
                }]
              });
              continue;
            }
          }
          
          // 툴 실행
          const startTime = performance.now();
          try {
            const result = await this.executeTool(call);
            conversation.push({
              id: generateId(),
              role: 'tool',
              tool_results: [{
                call_id: call.id,
                status: 'success',
                content: result,
                executionTime: performance.now() - startTime
              }]
            });
          } catch (error) {
            conversation.push({
              id: generateId(),
              role: 'tool',
              tool_results: [{
                call_id: call.id,
                status: 'error',
                content: error.message,
                executionTime: performance.now() - startTime
              }]
            });
          }
        }
      } else {
        // 툴 호출 없음: 최종 응답
        return {
          id: generateId(),
          role: 'assistant',
          content: response.content,
          metadata: { timestamp: Date.now() }
        };
      }
    }
    
    throw new Error('Max iterations exceeded');
  }
}
```

### 2.5.3 스트리밍 및 실시간 처리

```typescript
interface StreamingConfig {
  enabled: boolean;
  chunkSize: number;
  debounceMs: number;
}

class StreamingEngine {
  async *streamResponse(
    userInput: string,
    config: StreamingConfig
  ): AsyncGenerator<StreamChunk> {
    const stream = await this.llm.stream({
      messages: [{ role: 'user', content: userInput }]
    });
    
    let buffer = '';
    let lastEmit = Date.now();
    
    for await (const chunk of stream) {
      buffer += chunk.content;
      
      // 디바운싱: 너무 자주 업데이트하지 않음
      if (Date.now() - lastEmit > config.debounceMs) {
        yield {
          type: 'content',
          data: buffer
        };
        buffer = '';
        lastEmit = Date.now();
      }
    }
    
    // 남은 버퍼 방출
    if (buffer) {
      yield {
        type: 'content',
        data: buffer
      };
    }
    
    // 완료 신호
    yield { type: 'done' };
  }
}
```

---

## 2.6 OpenClaw와의 상세 비교

### 기능 비교 매트릭스

| 기능 | Claude Code | OpenClaw | 비고 |
|-----|-------------|----------|------|
| **아키텍처** | 모노리식 | 분산 노드 | OpenClaw가 더 유연 |
| **프로토콜** | 자체 ACP | 표준 ACP | 유사한 설계 철학 |
| **LLM 지원** | Claude 전용 | 다중 제공자 | OpenClaw가 유연 |
| **툴 시스템** | 내장 툴 | 플러그인 기반 | OpenClaw가 확장성 ↑ |
| **권한 모델** | 승인 기반 | 승인 + Risk Tolerance | OpenClaw가 세분화 |
| **실행 환경** | 로컬 CLI | 로컬 + 원격 | OpenClaw가 다양 |
| **컨텍스트 관리** | 슬라이딩 + 요약 | 세션 + 캐싱 | 유사한 접근 |
| **오픈소스** | ❌ | ✅ | 핵심 차이 |
| **커뮤니티** | 제한적 | 활발 | 오픈소스의 장점 |

### 아키텍처적 차이점 시각화

```
Claude Code (모노리식):
┌─────────────────────────────────────────┐
│           Claude Code Binary            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │   UI    │ │  Core   │ │  Tools  │  │
│  └─────────┘ └─────────┘ └─────────┘  │
│              ↓                          │
│         Claude API                      │
└─────────────────────────────────────────┘

OpenClaw (분산 노드):
┌─────────────────────────────────────────┐
│           Gateway (Coordination)        │
└─────────────────────────────────────────┘
           ↓           ↓           ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Node 1     │ │   Node 2     │ │   Node N     │
│ (Local)      │ │ (Remote)     │ │ (Cloud)      │
└──────────────┘ └──────────────┘ └──────────────┘
       ↓                ↓                ↓
  ┌─────────┐     ┌─────────┐      ┌─────────┐
  │OpenAI   │     │Claude   │      │Local LLM│
  └─────────┘     └─────────┘      └─────────┘
```

---

## 관련 페이지

- [← 메인 분석 페이지](../claude-code-leak-analysis.md)
- [1. 유출 개요](./01-overview.md)
- [→ 3. 보안 분석](./03-security.md)
- [4. 기술적 인사이트](./04-insights.md)
- [5. 결론](./05-conclusion.md)
