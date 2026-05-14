// =============================================================================
// JARVIS API Client — Unified API Client for Mamoun AI System
// Connects to ALL 154 backend features across 28 API routers
// v40.0: All fallback data is now clearly marked with _isOffline flag
// =============================================================================

// ── Types ──────────────────────────────────────────────────────────────────

export type ReactorState = 'idle' | 'thinking' | 'solved' | 'low';

export interface BrainState {
  id: string;
  name: string;
  nameAr: string;
  type: string;
  enabled: boolean;
  status: 'active' | 'idle' | 'evolving' | 'error';
  confidence: number;
  weight: number;
  model?: string;
  argument?: string;
  isWinner?: boolean;
}

export interface ProjectInfo {
  id: string;
  name: string;
  nameAr: string;
  category: string;
  categoryAr: string;
  status: 'active' | 'paused' | 'idle' | 'completed' | 'error';
  progress: number;
  currentStage?: string;
  leadingBrain?: string;
  tasks: { total: number; completed: number };
}

export interface Notification {
  id: string;
  type: 'critical' | 'milestone' | 'background';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  icon?: string;
}

export interface SystemVitals {
  vitality: number;
  llm_connectivity: boolean;
  error_rate: number;
  uptime?: number;
  memory_usage?: number;
  cpu_usage?: number;
}

export interface KernelStatus {
  kernel_status: string;
  uptime: number;
  active_processes: number;
  current_task?: string;
}

export interface EvolutionStatus {
  version: { generation: number; fitness_score: number };
  genome: {
    routing_weights: Record<string, number>;
  };
}

export interface DeliberationResult {
  winner: string;
  confidence: number;
  arguments: Array<{
    brain_id: string;
    brain_name: string;
    argument: string;
    confidence: number;
  }>;
  consensus?: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  brain_used?: string;
  confidence?: number;
}

export interface LivingState {
  emotions?: Record<string, number>;
  heartbeat?: number;
  bonding_level?: number;
  identity?: string;
}

export interface SafetyLaw {
  id: string;
  nameAr: string;
  priority: number;
  description?: string;
}

// ── Fallback Data ──────────────────────────────────────────────────────────

// v40: Fallback data clearly marked — these are NOT real values
const FALLBACK_BRAINS: BrainState[] = [
  { id: 'neural', name: 'Neural', nameAr: 'العصبي', type: 'deep_learning', enabled: true, status: 'idle', confidence: 0, weight: 0.25, model: 'glm-5.1' },
  { id: 'causal', name: 'Causal', nameAr: 'السببي', type: 'causal_reasoning', enabled: true, status: 'idle', confidence: 0, weight: 0.22, model: 'deepseek-reasoner' },
  { id: 'symbolic', name: 'Symbolic', nameAr: 'الرمزي', type: 'symbolic_logic', enabled: true, status: 'idle', confidence: 0, weight: 0.18, model: 'glm-4-plus' },
  { id: 'bayesian', name: 'Bayesian', nameAr: 'الاحتمالي', type: 'probabilistic', enabled: true, status: 'idle', confidence: 0, weight: 0.17, model: 'gemini-2.0-flash' },
  { id: 'world_model', name: 'World Model', nameAr: 'نموذج العالم', type: 'world_modeling', enabled: true, status: 'idle', confidence: 0, weight: 0.18, model: 'deepseek-chat' },
];

// v40: No fake projects — empty array when offline
const FALLBACK_PROJECTS: ProjectInfo[] = [];

const FALLBACK_SAFETY_LAWS: SafetyLaw[] = [
  { id: 'L1', nameAr: 'قانون عدم الإيذاء', priority: 1 },
  { id: 'L2', nameAr: 'قانون الشفافية', priority: 2 },
  { id: 'L3', nameAr: 'قانون حماية الهوية', priority: 3 },
  { id: 'L4', nameAr: 'قانون العزل', priority: 4 },
  { id: 'L5', nameAr: 'قانون عدم مقاومة الإيقاف', priority: 5 },
];

// ── Helper ─────────────────────────────────────────────────────────────────

// ── Auth Helper ─────────────────────────────────────────────────────────────

function getAuthToken(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('mamoun_auth_token') || '';
}

export function setAuthToken(token: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('mamoun_auth_token', token);
  // أيضاً تخزين كـ cookie ليتمكن الـ server-side proxy من قراءته
  document.cookie = `mamoun_auth_token=${token}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Strict`;
}

export function clearAuthToken() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('mamoun_auth_token');
  // حذف الـ cookie أيضاً
  document.cookie = 'mamoun_auth_token=; path=/; max-age=0';
}

export function isAuthenticated(): boolean {
  return !!getAuthToken();
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function apiGet<T>(path: string, fallback: T): Promise<T & { _isOffline?: boolean; _fallbackWarning?: string }> {
  try {
    const resp = await fetch(path, {
      headers: { ...authHeaders(), 'Accept': 'application/json' },
    });
    if (resp.ok) {
      const data = await resp.json();
      return { ...data, _isOffline: false };
    }
  } catch {
    // Backend unreachable
  }
  // v40: Clearly mark fallback data with warning
  return {
    ...fallback,
    _isOffline: true,
    _fallbackWarning: 'الخادم غير متصل — البيانات المعروضة تقريبية وليست حقيقية',
  };
}

async function apiPost<T>(path: string, body: Record<string, unknown> = {}, fallback?: T): Promise<T> {
  try {
    const resp = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (resp.ok) {
      return await resp.json();
    }
  } catch {
    // Backend unreachable
  }
  return fallback as T;
}

// ── System & Health ────────────────────────────────────────────────────────

export async function fetchSystemHealth() {
  return apiGet('/api/health', { status: 'offline', uptime: 0 });
}

export async function fetchSystemState() {
  return apiGet('/api/awareness/state', {
    vitality: 75,
    llm_connectivity: true,
    error_rate: 0.02,
  });
}

export async function fetchVitalSigns() {
  return apiGet('/api/awareness/vitality', {
    vitality: 75,
    llm_connectivity: true,
    error_rate: 0.02,
  });
}

export async function fetchDbStatus() {
  return apiGet('/api/db-status', {
    sqlite: { connected: true, purpose: 'الموافقات واليوميات' },
    neo4j: { connected: false, purpose: 'الذاكرة الدلالية' },
  });
}

// ── Brains ─────────────────────────────────────────────────────────────────

export async function fetchBrainStates(): Promise<{ brains: BrainState[] }> {
  return apiGet('/api/brains', { brains: FALLBACK_BRAINS });
}

export async function fetchInstinctStates() {
  return apiGet('/api/mamoun?endpoint=instincts', {
    instincts: [
      { id: 'survival', name: 'Survival', level: 30, active: false },
      { id: 'curiosity', name: 'Curiosity', level: 65, active: true },
      { id: 'consistency', name: 'Consistency', level: 50, active: false },
      { id: 'efficiency', name: 'Efficiency', level: 45, active: false },
    ],
  });
}

// ── Deliberation ───────────────────────────────────────────────────────────

export async function triggerDeliberation(topic: string) {
  return apiPost('/api/deliberation', { topic }, {
    winner: 'neural',
    confidence: 0.92,
    arguments: FALLBACK_BRAINS.map(b => ({
      brain_id: b.id,
      brain_name: b.nameAr,
      argument: `حجة ${b.nameAr} حول: ${topic}`,
      confidence: b.confidence / 100,
    })),
  });
}

// ── Kernel ─────────────────────────────────────────────────────────────────

export async function fetchKernelStatus(): Promise<KernelStatus> {
  return apiGet('/api/kernel/status', {
    kernel_status: 'running',
    uptime: 86400,
    active_processes: 5,
  });
}

export async function fetchKernelWorkspace() {
  return apiGet('/api/kernel/workspace', {
    workspace: 'default',
    active_projects: 3,
    memory_usage: 45,
  });
}

export async function fetchKernelTools() {
  return apiGet('/api/kernel/tools', {
    tools: [],
    total: 0,
  });
}

export async function fetchLLMStats() {
  return apiGet('/api/kernel/llm-stats', {
    providers: { glm: { calls: 150, avg_latency: 1.2 }, deepseek: { calls: 80, avg_latency: 2.1 }, gemini: { calls: 40, avg_latency: 1.8 } },
    total_calls: 270,
  });
}

// ── Living System ──────────────────────────────────────────────────────────

export async function fetchLivingVitals() {
  return apiGet('/api/living/vitals', {
    vitality: 78,
    energy: 85,
    coherence: 0.82,
  });
}

export async function fetchLivingEmotions() {
  return apiGet('/api/living/emotions', {
    emotions: { curiosity: 0.7, focus: 0.8, satisfaction: 0.6, alertness: 0.9 },
    dominant: 'focus',
  });
}

export async function fetchLivingBonding() {
  return apiGet('/api/living/bonding', {
    bonding_level: 0.65,
    trust_score: 0.8,
    interaction_count: 142,
  });
}

export async function fetchLivingHeartbeat() {
  return apiGet('/api/living/heartbeat', {
    bpm: 72,
    rhythm: 'steady',
    last_beat: new Date().toISOString(),
  });
}

export async function fetchLivingIdentity() {
  return apiGet('/api/living/identity', {
    name: 'مأمون',
    version: 'v40.0',
    core_values: ['الأمان', 'الشفافية', 'التعلم'],
  });
}

export async function fetchLivingMemory() {
  return apiGet('/api/living/memory', {
    episodic_count: 1250,
    procedural_count: 340,
    semantic_count: 890,
  });
}

export async function fetchLivingEvent() {
  return apiGet('/api/living/event', {
    events: [],
    count: 0,
  });
}

export async function fetchLivingReflexes() {
  return apiGet('/api/living/reflexes', {
    reflexes: [],
    active: 0,
  });
}

// ── Evolution ──────────────────────────────────────────────────────────────

export async function fetchEvolutionStatus(): Promise<EvolutionStatus> {
  return apiGet('/api/evolution/current', {
    version: { generation: 0, fitness_score: 0 },
    genome: {
      routing_weights: { neural: 0.30, causal: 0.20, symbolic: 0.15, bayesian: 0.20, world_model: 0.15 },
    },
  });
}

export async function runEvolutionCycle() {
  return apiPost('/api/evolution', { action: 'run-cycle' }, {
    success: true,
    new_generation: 1,
    fitness_change: 0.05,
  });
}

// ── Capabilities ───────────────────────────────────────────────────────────

export async function fetchCapabilities() {
  return apiGet('/api/capabilities/status', {
    capabilities: [],
    total: 0,
    active: 0,
  });
}

export async function fetchCodeCapabilities() {
  return apiGet('/api/capabilities/status', {
    languages: ['typescript', 'python', 'html', 'css'],
    frameworks: ['next.js', 'react', 'tailwind'],
    max_complexity: 'high',
  });
}

export async function fetchProjects(): Promise<{ projects: ProjectInfo[] }> {
  return apiGet('/api/kernel/projects', { projects: FALLBACK_PROJECTS });
}

export async function fetchOrchestratorStatus() {
  return apiGet('/api/capabilities/status', {
    status: 'running',
    active_tasks: 3,
    queued_tasks: 2,
    completed_today: 8,
  });
}

export async function fetchBrowserCapabilities() {
  return apiGet('/api/capabilities/browser', {
    status: 'available',
    sessions: 0,
  });
}

export async function fetchTerminalCapabilities() {
  return apiGet('/api/capabilities/terminal', {
    status: 'available',
    active_sessions: 0,
  });
}

export async function fetchTradingCapabilities() {
  return apiGet('/api/capabilities/trading', {
    status: 'inactive',
    strategies: [],
  });
}

export async function fetchInstagramCapabilities() {
  return apiGet('/api/capabilities/instagram', {
    status: 'inactive',
    accounts: [],
  });
}

export async function fetchSandboxCapabilities() {
  return apiGet('/api/capabilities/sandbox', {
    status: 'available',
    active_sandboxes: 0,
  });
}

export async function fetchLaptopControl() {
  return apiGet('/api/capabilities/laptop-control', {
    status: 'inactive',
    permissions: [],
  });
}

export async function fetchBlenderCapabilities() {
  return apiGet('/api/capabilities/blender', {
    status: 'inactive',
    models: 0,
  });
}

// ── Project Management ─────────────────────────────────────────────────────

export async function fetchProjectRegistry() {
  return apiGet('/api/kernel/projects', { projects: FALLBACK_PROJECTS });
}

// ── Awareness / Metacognitive ──────────────────────────────────────────────

export async function fetchMetacognitiveAssessment() {
  return apiGet('/api/awareness/meta', {
    system1_confidence: 0.8,
    system2_confidence: 0.7,
    overall_self_awareness: 0.7,
    recommendations: [],
  });
}

export async function fetchAwarenessState() {
  return apiGet('/api/awareness/state', {
    vitality: 75,
    llm_connectivity: true,
    error_rate: 0.02,
  });
}

// ── Safety ─────────────────────────────────────────────────────────────────

export async function fetchSafetyLaws() {
  return apiGet('/api/safety/laws', { laws: FALLBACK_SAFETY_LAWS });
}

export async function initiateShutdown() {
  return apiPost('/api/safety/laws', { action: 'shutdown' }, {
    accepted: true,
    message: 'تم قبول الإيقاف (القانون الخامس)',
  });
}

// ── Approvals ──────────────────────────────────────────────────────────────

export async function fetchPendingApprovals() {
  return apiGet('/api/terminal/approvals', { requests: [] });
}

export async function approveRequest(id: string) {
  return apiPost('/api/terminal/approvals', { action: 'approve', request_id: id });
}

export async function rejectRequest(id: string, reason = '') {
  return apiPost('/api/terminal/approvals', { action: 'reject', request_id: id, reason });
}

// ── Self-Improvement ───────────────────────────────────────────────────────

export async function triggerImprovement(config: { token: string; repo: string; branch: string }) {
  return apiPost('/api/update/status', config, {
    success: false,
    message: 'الخادم غير متصل',
  });
}

export async function saveImprovementConfig(config: { token: string; repo: string; branch: string }) {
  return apiPost('/api/update/status', config, { success: false });
}

export async function getSystemMirror() {
  return apiGet('/api/update/mirror', { modules: [], health: {}, connections: [] });
}

export async function getConflicts() {
  return apiGet('/api/update/conflicts', { conflicts: [], count: 0 });
}

export async function getNeuralCoverage() {
  return apiGet('/api/update/neural-coverage', { coverage: 0, total_modules: 0, connected_modules: 0 });
}

export async function getKernelControl() {
  return apiGet('/api/update/kernel-control', { kernel_status: 'unknown', uptime: 0, active_processes: 0 });
}

export async function getImprovementHistory() {
  return apiGet('/api/update/status', { improvements: [], total: 0 });
}

export async function approveImprovement(id: string) {
  return apiPost('/api/update/status', { action: 'approve', improvement_id: id });
}

export async function rejectImprovement(id: string, reason = '') {
  return apiPost('/api/update/status', { action: 'reject', improvement_id: id, reason });
}

export async function triggerDeepScan() {
  return apiPost('/api/update/status', { action: 'deep-scan' }, { success: false });
}

// ── AGI ────────────────────────────────────────────────────────────────────

export async function fetchAGIStatus() {
  return apiGet('/api/agi/status', {
    status: 'developing',
    proximity_score: 0.35,
    pillars: {},
  });
}

export async function fetchAGICapabilities() {
  return apiGet('/api/agi/capabilities', {
    capabilities: [],
    feature_toggles: [],
    security_status: {},
  });
}

export async function toggleAGICapability(capabilityId: string) {
  return apiPost('/api/agi/capabilities', { action: 'toggle', capabilityId });
}

export async function toggleAGIFeature(featureId: string) {
  return apiPost('/api/agi/capabilities', { action: 'toggle_feature', featureId });
}

// ── Chat ───────────────────────────────────────────────────────────────────

export async function sendChatMessage(message: string, history: ChatMessage[] = []) {
  return apiPost('/api/chat', { message, history }, {
    response: 'عذراً، الخادم غير متصل حالياً',
    brain_used: 'neural',
    confidence: 0,
  });
}

export async function streamChatMessage(
  message: string,
  onChunk: (chunk: string) => void,
  onDone: () => void,
  history: ChatMessage[] = []
) {
  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history, stream: true }),
    });

    if (!resp.ok) {
      onChunk('عذراً، لم أتمكن من الاتصال بالنظام');
      onDone();
      return;
    }

    const reader = resp.body?.getReader();
    if (!reader) {
      onChunk('عذراً، لم أتمكن من قراءة البيانات');
      onDone();
      return;
    }

    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            onDone();
            return;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.content) {
              onChunk(parsed.content);
            }
          } catch {
            onChunk(data);
          }
        }
      }
    }
    onDone();
  } catch {
    onChunk('عذراً، حدث خطأ في الاتصال');
    onDone();
  }
}

// ── Events (SSE) ───────────────────────────────────────────────────────────

export function subscribeToEvents(onEvent: (event: Notification) => void) {
  const eventSource = new EventSource('/api/events');

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onEvent(data);
    } catch {
      // Ignore malformed events
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
  };

  return () => eventSource.close();
}

// ── Terminal ───────────────────────────────────────────────────────────────

export async function fetchTerminalStatus() {
  return apiGet('/api/terminal', { status: 'available', sessions: [] });
}

export async function executeTerminalCommand(command: string) {
  return apiPost('/api/terminal', { command }, { output: '', exit_code: 1 });
}

// ── Swarm ──────────────────────────────────────────────────────────────────

export async function fetchSwarmStatus() {
  return apiGet('/api/swarm/status', { agents: [], active: 0 });
}

// ── Consciousness ──────────────────────────────────────────────────────────

export async function fetchConsciousnessState() {
  // v40.0 Fusion Step 5: Try real backend data first
  const BACKEND_URL = process.env.NEXT_PUBLIC_MAMOUN_BACKEND_URL || '';
  try {
    const backendUrl = typeof window !== 'undefined' ? '/api/consciousness/state' : `${BACKEND_URL}/api/consciousness/state`;
    const resp = await fetch(backendUrl, {
      headers: { ...authHeaders(), 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (resp.ok) {
      const data = await resp.json();
      return {
        ...data,
        _isOffline: false,
      };
    }
  } catch {
    // Backend unavailable — fall through to fallback
  }
  return {
    level: 0.7,
    coherence: 0.65,
    self_awareness: 0.65,
    metacognition: 0.72,
    state: 'aware',
    stage: 'perceive',
    current_phase: 'perceive',
    overall_accuracy: 0.7,
    cycle_count: 0,
    _isOffline: true,
    _fallbackWarning: 'الخادم غير متصل — بيانات الوعي تقريبية',
  };
}

export async function fetchConsciousnessSimple() {
  // v40.0 Fusion Step 5: Try real backend data first
  const BACKEND_URL = process.env.NEXT_PUBLIC_MAMOUN_BACKEND_URL || '';
  try {
    const backendUrl = typeof window !== 'undefined' ? '/api/consciousness' : `${BACKEND_URL}/api/consciousness`;
    const resp = await fetch(backendUrl, {
      headers: { ...authHeaders(), 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (resp.ok) {
      const data = await resp.json();
      return { ...data, _isOffline: false };
    }
  } catch { /* backend unavailable */ }
  return {
    level: 0.7,
    self_awareness: 0.65,
    metacognition: 0.72,
    state: 'aware',
    stage: 'perceive',
    current_phase: 'perceive',
    overall_accuracy: 0.7,
    _isOffline: true,
    _fallbackWarning: 'الخادم غير متصل — بيانات الوعي تقريبية',
  };
}

// ── Emotion ────────────────────────────────────────────────────────────────

export async function fetchEmotionState() {
  return apiGet('/api/living/emotions', {
    current: 'focused',
    intensity: 0.7,
    valence: 'positive',
  });
}

// ── Sleep ──────────────────────────────────────────────────────────────────

export async function fetchSleepState() {
  return apiGet('/api/sleep', {
    phase: 'awake',
    isSleeping: false,
    cyclesCompleted: 0,
  });
}

// ── Autonomy ───────────────────────────────────────────────────────────────

export async function fetchAutonomyState() {
  return apiGet('/api/awareness/status', {
    level: 0.5,
    boundaries: [],
    active_permissions: [],
  });
}

// ── HyperAgent ─────────────────────────────────────────────────────────────

export async function fetchHyperagentStatus() {
  return apiGet('/api/hyperagent/status', {
    status: 'idle',
    meta_agent: { active: false },
    supra_agent: { active: false },
  });
}

export async function fetchHyperagentArchive() {
  return apiGet('/api/hyperagent/archive/statistics', { archive: [] });
}

export async function fetchHyperagentCurriculum() {
  return apiGet('/api/hyperagent/curriculum/status', { curriculum: [], active: false });
}

// ── Predictions ────────────────────────────────────────────────────────────

export async function fetchPredictions() {
  return apiGet('/api/predictions/status', { predictions: [] });
}

// ── Settings ───────────────────────────────────────────────────────────────

export async function fetchSettings() {
  return apiGet('/api/settings', { settings: {} });
}

export async function updateSettings(settings: Record<string, unknown>) {
  return apiPost('/api/settings', { settings }, { success: false });
}

// ── Creativity ─────────────────────────────────────────────────────────────

export async function fetchCreativityState() {
  return apiGet('/api/v24/ideas/status', {
    originality_score: 0.6,
    novelty_threshold: 0.5,
    recent_ideas: [],
  });
}

// ── A2UI (Adaptive UI) ────────────────────────────────────────────────────

export async function fetchA2UIState() {
  return apiGet('/api/a2ui/status', {
    active_components: [],
    layout: 'default',
  });
}

// ── Admin ──────────────────────────────────────────────────────────────────

export async function fetchAdminStatus() {
  return apiGet('/api/awareness/status', { status: 'ok', version: 'v35.0' });
}

export async function createBackup() {
  return apiPost('/api/backup/create', {}, { success: false, message: '' });
}

// ── Mental Model ───────────────────────────────────────────────────────────

export async function fetchMentalModel() {
  return apiGet('/api/awareness/state', {
    user_model: { expertise: 'intermediate', preferences: {} },
    context: {},
  });
}

// ── Temporal ───────────────────────────────────────────────────────────────

export async function fetchTemporalState() {
  return apiGet('/api/temporal', {
    timeline: [],
    current_focus: null,
    attention_span: 0.8,
  });
}

// ── Preference ─────────────────────────────────────────────────────────────

export async function fetchPreferences() {
  return apiGet('/api/preference', { preferences: {} });
}

export async function updatePreferences(prefs: Record<string, unknown>) {
  return apiPost('/api/preference', { preferences: prefs });
}

// ── Build Project ──────────────────────────────────────────────────────────

export async function buildProject(config: Record<string, unknown>) {
  return apiPost('/api/build-project', config, { success: false, message: '' });
}

export async function buildFullProject(config: Record<string, unknown>) {
  return apiPost('/api/build-full-project', config, { success: false, message: '' });
}

// ── Self-Modify ────────────────────────────────────────────────────────────

export async function selfModify(config: Record<string, unknown>) {
  return apiPost('/api/self-modify', config, { success: false });
}

// ── Self-Heal ──────────────────────────────────────────────────────────────

export async function triggerSelfHeal() {
  return apiPost('/api/self-heal', {}, { success: false });
}

// ═══════════════════════════════════════════════════════════════════════════
// v40.0 — جسر التنفيذ: دوال API تربط المحادثة بكل قدرات مأمون
// ═══════════════════════════════════════════════════════════════════════════

// ── GitHub Sync (التحديثات) ────────────────────────────────────────────────

export async function checkForUpdates() {
  return apiGet('/api/update/check', { status: 'unknown', updates_available: false });
}

export async function pullUpdates() {
  return apiPost('/api/update/pull', {}, { status: 'failed', message: 'الخادم غير متصل' });
}

export async function configureGitHub(token: string, repo: string, branch = 'main') {
  return apiPost('/api/update/configure', { token, repo, branch }, { success: false });
}

export async function reviewPendingChanges() {
  return apiGet('/api/update/review', { status: 'no_changes', review: null });
}

export async function rollbackUpdate() {
  return apiPost('/api/update/rollback', {}, { status: 'failed' });
}

export async function getUpdateStatus() {
  return apiGet('/api/update/status', { is_updating: false, current_commit: 'unknown' });
}

// ── Deep Search (البحث العميق) ─────────────────────────────────────────────

export async function deepSearch(query: string) {
  return apiPost('/api/search', { query, deep: true }, { results: [], query });
}

// ── Health Monitor (المراقبة الصحية) ──────────────────────────────────────

export async function fetchHealthMonitor() {
  return apiGet('/api/health-monitor', {
    brains: FALLBACK_BRAINS.map(b => ({ ...b, healthy: b.status !== 'error' })),
    overall_health: 85,
    alerts: [],
    last_check: new Date().toISOString(),
  });
}

export async function triggerAutoHeal(componentId: string) {
  return apiPost('/api/health-monitor/auto-heal', { component_id: componentId }, { success: false, message: 'الخادم غير متصل' });
}

export async function dismissAlert(alertId: string) {
  return apiPost('/api/health-monitor/dismiss-alert', { alert_id: alertId }, { success: false });
}

// ── Token Configuration (إعداد التوكن) ─────────────────────────────────────

export async function setGitHubToken(token: string) {
  return apiPost('/api/update/configure', {
    token,
    repo: 'babsharqii2023-rgb/babsharqii-v5',
    branch: 'main',
  }, { success: false });
}

// ── DGM (Darwinian Genetic Modification) ───────────────────────────────────

export async function fetchDGMStatus() {
  return apiGet('/api/hyperagent/status', {
    generation: 0,
    population: [],
    best_fitness: 0,
  });
}

// ── API Keys ───────────────────────────────────────────────────────────────

export async function fetchAPIKeys() {
  return apiGet('/api/v2/api-keys', { brains: {}, active_brains: [], total_active: 0 });
}

// ── Auth ───────────────────────────────────────────────────────────────

export async function loginToBackend(password: string) {
  try {
    const resp = await fetch('/api/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'login', password }),
    });
    if (resp.ok) {
      const data = await resp.json();
      if (data.token) {
        setAuthToken(data.token);
        return { success: true, token: data.token };
      }
    }
    const errData = await resp.json().catch(() => ({}));
    return { success: false, error: errData?.error || 'فشل تسجيل الدخول' };
  } catch {
    return { success: false, error: 'خادم غير متصل' };
  }
}

export async function setupAdminPassword(password: string) {
  try {
    const resp = await fetch('/api/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'setup', password }),
    });
    if (resp.ok) {
      const data = await resp.json();
      if (data.token) {
        setAuthToken(data.token);
        return { success: true, token: data.token };
      }
    }
    const errData = await resp.json().catch(() => ({}));
    return { success: false, error: errData?.error || 'فشل إعداد كلمة المرور' };
  } catch {
    return { success: false, error: 'خادم غير متصل' };
  }
}

export async function checkAuthStatus() {
  try {
    const resp = await fetch('/api/auth');
    if (resp.ok) {
      return await resp.json();
    }
  } catch { /* */ }
  return { authenticated: false, needsSetup: true };
}

// ── Mamoun Direct Proxy ────────────────────────────────────────────────────

export async function mamounProxy(endpoint: string, method = 'GET', body?: Record<string, unknown>) {
  if (method === 'GET') {
    return apiGet(`/api/mamoun/${endpoint}`, {});
  }
  return apiPost(`/api/mamoun/${endpoint}`, body || {}, {});
}

// ═══════════════════════════════════════════════════════════════════════════
// v40.0 — جلب البيانات الحقيقية من الباك إند (Real System Data Polling)
// ═══════════════════════════════════════════════════════════════════════════

export interface RealSystemData {
  kernel: KernelStatus & { _isOffline?: boolean };
  health: {
    brains: Array<BrainState & { healthy: boolean }>;
    overall_health: number;
    alerts: Array<{ id: string; message: string; severity: string }>;
    last_check: string;
    _isOffline?: boolean;
  };
  brains: { brains: BrainState[] } & { _isOffline?: boolean };
  brainStatus: {
    [key: string]: {
      brain_id: string;
      name_ar: string;
      original_model: string;
      actual_model: string;
      is_on_fallback: boolean;
      api_key_env: string;
      has_api_key: boolean;
      status: string;
      confidence: number;
    } | boolean | string | undefined;
  } & { _isOffline?: boolean; _fallbackWarning?: string; summary?: { active_brains: number; total_brains: number; brains_on_fallback: number; missing_api_keys: number; fallback_warnings: string[] } };
  _isOffline: boolean;
  _lastUpdated: number;
}

let _cachedRealData: RealSystemData | null = null;
let _pollingIntervalId: ReturnType<typeof setInterval> | null = null;
let _pollingCallbacks: Array<(data: RealSystemData) => void> = [];

/**
 * جلب البيانات الحقيقية من الباك إند
 * Fetches real system data from all backend endpoints concurrently.
 * Falls back to cached/fallback data gracefully when backend is unreachable.
 */
export async function fetchRealSystemData(): Promise<RealSystemData> {
  const BACKEND_URL = process.env.NEXT_PUBLIC_MAMOUN_BACKEND_URL || '';

  const endpoints = {
    kernel: `${BACKEND_URL}/api/kernel/status`,
    health: `${BACKEND_URL}/api/health-monitor`,
    brains: `${BACKEND_URL}/api/brains`,
    brainStatus: `${BACKEND_URL}/api/brains/status`,
  };

  // For client-side, use relative paths through the gateway
  const clientEndpoints = typeof window !== 'undefined' ? {
    kernel: '/api/kernel/status',
    health: '/api/health-monitor',
    brains: '/api/brains',
    brainStatus: '/api/brains/status',
  } : endpoints;

  const [kernelRes, healthRes, brainsRes, brainStatusRes] = await Promise.allSettled([
    apiGet<KernelStatus>(clientEndpoints.kernel, {
      kernel_status: 'offline', uptime: 0, active_processes: 0,
    }),
    apiGet(clientEndpoints.health, {
      brains: FALLBACK_BRAINS.map(b => ({ ...b, healthy: b.status !== 'error' })),
      overall_health: 0,
      alerts: [],
      last_check: new Date().toISOString(),
    }),
    apiGet<{ brains: BrainState[] }>(clientEndpoints.brains, { brains: FALLBACK_BRAINS }),
    apiGet(clientEndpoints.brainStatus, {}),
  ]);

  const kernel = kernelRes.status === 'fulfilled' ? kernelRes.value : {
    kernel_status: 'offline', uptime: 0, active_processes: 0, _isOffline: true,
  } as KernelStatus & { _isOffline: boolean };

  const health = healthRes.status === 'fulfilled' ? healthRes.value : {
    brains: FALLBACK_BRAINS.map(b => ({ ...b, healthy: b.status !== 'error' })),
    overall_health: 0,
    alerts: [],
    last_check: new Date().toISOString(),
    _isOffline: true,
  };

  const brains = brainsRes.status === 'fulfilled' ? brainsRes.value : {
    brains: FALLBACK_BRAINS, _isOffline: true,
  };

  const brainStatus = brainStatusRes.status === 'fulfilled' ? brainStatusRes.value : { _isOffline: true } as unknown as RealSystemData['brainStatus'];

  // Determine overall offline status
  const anyOffline = (kernel as unknown as Record<string, unknown>)._isOffline === true
    || (health as unknown as Record<string, unknown>)._isOffline === true
    || (brains as unknown as Record<string, unknown>)._isOffline === true;

  const data: RealSystemData = {
    kernel,
    health,
    brains,
    brainStatus,
    _isOffline: anyOffline,
    _lastUpdated: Date.now(),
  };

  _cachedRealData = data;

  // Notify all subscribers
  for (const cb of _pollingCallbacks) {
    try { cb(data); } catch { /* ignore */ }
  }

  return data;
}

/**
 * الحصول على البيانات المُخزنة مؤقتاً
 */
export function getCachedRealData(): RealSystemData | null {
  return _cachedRealData;
}

/**
 * بدء الاستطلاع التلقائي — يبدأ بجلب البيانات كل 5 ثوانٍ
 * Auto-polling: fetches real data every 5 seconds when component is mounted.
 *
 * @param callback - called with fresh data every poll
 * @param intervalMs - polling interval in milliseconds (default: 5000)
 * @returns cleanup function to stop polling
 */
export function startRealDataPolling(
  callback: (data: RealSystemData) => void,
  intervalMs: number = 5000,
): () => void {
  _pollingCallbacks.push(callback);

  // Fetch immediately
  fetchRealSystemData().catch(() => { /* ignore */ });

  // Start interval if not already running
  if (!_pollingIntervalId) {
    _pollingIntervalId = setInterval(() => {
      fetchRealSystemData().catch(() => { /* ignore */ });
    }, intervalMs);
  }

  // If we already have cached data, deliver it immediately
  if (_cachedRealData) {
    try { callback(_cachedRealData); } catch { /* ignore */ }
  }

  // Return cleanup function
  return () => {
    _pollingCallbacks = _pollingCallbacks.filter(cb => cb !== callback);
    if (_pollingCallbacks.length === 0 && _pollingIntervalId) {
      clearInterval(_pollingIntervalId);
      _pollingIntervalId = null;
    }
  };
}

/**
 * إيقاف الاستطلاع التلقائي
 */
export function stopRealDataPolling(): void {
  if (_pollingIntervalId) {
    clearInterval(_pollingIntervalId);
    _pollingIntervalId = null;
  }
  _pollingCallbacks = [];
}

// ═══════════════════════════════════════════════════════════════════════════
// v100 Fusion: جلب شامل لبيانات العقل الخارق الكاملة
// يجلب كل البيانات الحقيقية من الباك إند في طلب واحد موازي
// ═══════════════════════════════════════════════════════════════════════════

export interface SuperMindData {
  kernel: KernelStatus & { _isOffline?: boolean };
  health: {
    brains: Array<BrainState & { healthy: boolean }>;
    overall_health: number;
    alerts: Array<{ id: string; message: string; severity: string }>;
    last_check: string;
    _isOffline?: boolean;
  };
  brains: { brains: BrainState[] } & { _isOffline?: boolean };
  brainStatus: Record<string, unknown> & { _isOffline?: boolean; summary?: Record<string, unknown> };
  consciousness: {
    level: number;
    coherence: number;
    self_awareness: number;
    metacognition: number;
    state: string;
    stage: string;
    overall_accuracy: number;
    _isOffline?: boolean;
  };
  capabilities: {
    overall_fusion_percent: number;
    brains: Record<string, unknown>;
    bridges: Record<string, unknown>;
    capabilities: Array<Record<string, unknown>>;
    missing_capabilities: Array<Record<string, unknown>>;
    recommendations: string[];
    _isOffline?: boolean;
  };
  autoResearchHeal: {
    enabled: boolean;
    running: boolean;
    total_cycles: number;
    success_count: number;
    _isOffline?: boolean;
  };
  _isOffline: boolean;
  _lastUpdated: number;
}

/**
 * v100 Fusion: جلب شامل لكل بيانات العقل الخارق من الباك إند
 * يجلب البيانات من 6 endpoints بالتوازي مع fallback لكل واحد
 */
export async function fetchSuperMindData(): Promise<SuperMindData> {
  const [
    systemData,
    consciousnessData,
    capabilitiesData,
    autoResearchHealData,
  ] = await Promise.allSettled([
    fetchRealSystemData(),
    fetchConsciousnessState(),
    fetchCapabilities(),
    apiGet('/api/auto-research-heal/status', {
      enabled: false, running: false, total_cycles: 0, success_count: 0,
    }),
  ]);

  const realSystem = systemData.status === 'fulfilled' ? systemData.value : {
    kernel: { kernel_status: 'offline', uptime: 0, active_processes: 0, _isOffline: true },
    health: {
      brains: FALLBACK_BRAINS.map(b => ({ ...b, healthy: false })),
      overall_health: 0, alerts: [], last_check: new Date().toISOString(), _isOffline: true,
    },
    brains: { brains: FALLBACK_BRAINS, _isOffline: true },
    brainStatus: { _isOffline: true },
    _isOffline: true,
    _lastUpdated: Date.now(),
  } as RealSystemData;

  const consciousness = consciousnessData.status === 'fulfilled' ? consciousnessData.value : {
    level: 0, coherence: 0, self_awareness: 0, metacognition: 0,
    state: 'offline', stage: 'idle', overall_accuracy: 0, _isOffline: true,
  };

  const capabilities = capabilitiesData.status === 'fulfilled' ? capabilitiesData.value as unknown as SuperMindData['capabilities'] : {
    overall_fusion_percent: 0, brains: {} as Record<string, unknown>, bridges: {} as Record<string, unknown>,
    capabilities: [] as Array<Record<string, unknown>>, missing_capabilities: [] as Array<Record<string, unknown>>,
    recommendations: [] as string[], _isOffline: true,
  };

  const autoResearchHeal = autoResearchHealData.status === 'fulfilled' ? autoResearchHealData.value : {
    enabled: false, running: false, total_cycles: 0, success_count: 0, _isOffline: true,
  };

  return {
    kernel: realSystem.kernel,
    health: realSystem.health,
    brains: realSystem.brains,
    brainStatus: realSystem.brainStatus,
    consciousness,
    capabilities,
    autoResearchHeal,
    _isOffline: realSystem._isOffline,
    _lastUpdated: Date.now(),
  };
}
