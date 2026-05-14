// =============================================================================
// MAMOUN AI v5 — Neural HUD Dashboard Data
// All 154 features organized into 25 sections
// =============================================================================

export type FeatureStatus = 'active' | 'idle' | 'evolving' | 'standby';

export interface DashboardFeature {
  id: number;
  nameEn: string;
  nameAr: string;
  category: string;
  status: FeatureStatus;
  apiEndpoint: string;
  backendFile: string;
}

export interface DashboardSection {
  id: number;
  nameAr: string;
  nameEn: string;
  features: DashboardFeature[];
}

export interface BrainDefinition {
  id: string;
  nameAr: string;
  nameEn: string;
  model: string;
  color: string;
  confidence: number;
  status: FeatureStatus;
}

// ── Brain Definitions ──────────────────────────────────────────────────────

export const BRAIN_DEFINITIONS: BrainDefinition[] = [
  { id: 'neural', nameAr: 'الدماغ العصبي', nameEn: 'Neural Brain', model: 'GLM-5.1', color: '#4A6FA5', confidence: 92, status: 'active' },
  { id: 'causal', nameAr: 'الدماغ السببي', nameEn: 'Causal Brain', model: 'DeepSeek-Reasoner', color: '#8A8A8A', confidence: 87, status: 'active' },
  { id: 'symbolic', nameAr: 'الدماغ الرمزي', nameEn: 'Symbolic Brain', model: 'GLM-4-Plus', color: '#4A6FA5', confidence: 79, status: 'idle' },
  { id: 'bayesian', nameAr: 'الدماغ الاحتمالي', nameEn: 'Bayesian Brain', model: 'Gemini-2.0-Flash', color: '#C0C0C0', confidence: 85, status: 'active' },
  { id: 'world_model', nameAr: 'دماغ النموذج العالمي', nameEn: 'World Model Brain', model: 'DeepSeek-Chat', color: '#8A8A8A', confidence: 81, status: 'idle' },
];

// ── All 154 Features in 25 Sections ────────────────────────────────────────

export const DASHBOARD_SECTIONS: DashboardSection[] = [
  {
    id: 1, nameAr: 'النواة الأساسية', nameEn: 'Core Kernel',
    features: [
      { id: 1, nameEn: 'MamounKernel', nameAr: 'نواة مأمون', category: 'core', status: 'active', apiEndpoint: '/api/kernel/status', backendFile: 'core/mamoun_kernel.py' },
      { id: 2, nameEn: 'NeuralBus', nameAr: 'الناقل العصبي', category: 'core', status: 'active', apiEndpoint: '/api/v23/neural-bus', backendFile: 'core/neural_bus.py' },
      { id: 3, nameEn: 'GlobalWorkspace', nameAr: 'مساحة العمل العالمية', category: 'core', status: 'active', apiEndpoint: '/api/kernel/workspace', backendFile: 'core/mamoun_kernel.py' },
      { id: 4, nameEn: 'ReflexionEngine', nameAr: 'محرك التأمل', category: 'core', status: 'evolving', apiEndpoint: '/api/v24/self-modify', backendFile: 'core/reflexion_engine.py' },
      { id: 5, nameEn: 'EscalationLadder', nameAr: 'سلم التصعيد', category: 'core', status: 'active', apiEndpoint: '/api/kernel/status', backendFile: 'core/mamoun_kernel.py' },
      { id: 6, nameEn: 'LLMClient', nameAr: 'عميل النماذج اللغوية', category: 'core', status: 'active', apiEndpoint: '/api/kernel/llm-stats', backendFile: 'core/llm_client.py' },
    ],
  },
  {
    id: 2, nameAr: 'الأدمغة الخمسة', nameEn: 'Five Brains',
    features: [
      { id: 7, nameEn: 'NeuralBrain', nameAr: 'الدماغ العصبي', category: 'brains', status: 'active', apiEndpoint: '/api/brains', backendFile: 'brains/living_brains.py' },
      { id: 8, nameEn: 'CausalBrain', nameAr: 'الدماغ السببي', category: 'brains', status: 'active', apiEndpoint: '/api/brains', backendFile: 'brains/living_brains.py' },
      { id: 9, nameEn: 'SymbolicBrain', nameAr: 'الدماغ الرمزي', category: 'brains', status: 'idle', apiEndpoint: '/api/brains', backendFile: 'brains/living_brains.py' },
      { id: 10, nameEn: 'BayesianBrain', nameAr: 'الدماغ الاحتمالي', category: 'brains', status: 'active', apiEndpoint: '/api/brains', backendFile: 'brains/living_brains.py' },
      { id: 11, nameEn: 'WorldModelBrain', nameAr: 'دماغ النموذج العالمي', category: 'brains', status: 'idle', apiEndpoint: '/api/brains', backendFile: 'brains/world_model_brain.py' },
      { id: 12, nameEn: 'BrainRouter', nameAr: 'موجّه الأدمغة', category: 'brains', status: 'active', apiEndpoint: '/api/brains', backendFile: 'brains/brain_router.py' },
      { id: 13, nameEn: 'DeliberationRoom', nameAr: 'غرفة المداولة', category: 'brains', status: 'active', apiEndpoint: '/api/deliberation', backendFile: 'deliberation/room.py' },
    ],
  },
  {
    id: 3, nameAr: 'نظام الوعي', nameEn: 'Consciousness System',
    features: [
      { id: 14, nameEn: 'ConsciousnessLoop', nameAr: 'حلقة الوعي', category: 'consciousness', status: 'active', apiEndpoint: '/api/consciousness', backendFile: 'core/consciousness_loop.py' },
      { id: 15, nameEn: 'InnerMonologue', nameAr: 'الحوار الداخلي', category: 'consciousness', status: 'active', apiEndpoint: '/api/v24/monologue', backendFile: 'core/inner_monologue.py' },
    ],
  },
  {
    id: 4, nameAr: 'التحسين الذاتي', nameEn: 'Self-Improvement',
    features: [
      { id: 16, nameEn: 'SelfImprovementEngine', nameAr: 'محرك التحسين الذاتي', category: 'improvement', status: 'evolving', apiEndpoint: '/api/auto-improve', backendFile: 'core/self_improvement_engine.py' },
      { id: 17, nameEn: 'CodeGenerationEngine', nameAr: 'محرك توليد الأكواد', category: 'improvement', status: 'active', apiEndpoint: '/api/capabilities/code', backendFile: 'core/code_generation_engine.py' },
      { id: 18, nameEn: 'VersionArchive', nameAr: 'أرشيف الإصدارات', category: 'improvement', status: 'active', apiEndpoint: '/api/evolution/current', backendFile: 'core/version_archive.py' },
      { id: 19, nameEn: 'LiveSelfModifier', nameAr: 'المعدّل الذاتي الحي', category: 'improvement', status: 'evolving', apiEndpoint: '/api/self-modify', backendFile: 'evolution/live_self_modifier.py' },
    ],
  },
  {
    id: 5, nameAr: 'الشفافية الذاتية', nameEn: 'Self-Transparency',
    features: [
      { id: 20, nameEn: 'SelfHealingEngine', nameAr: 'محرك الشفاء الذاتي', category: 'healing', status: 'active', apiEndpoint: '/api/self-heal', backendFile: 'core/self_healing.py' },
      { id: 21, nameEn: 'HealthChecks', nameAr: 'فحوصات الصحة', category: 'healing', status: 'active', apiEndpoint: '/api/self-heal', backendFile: 'core/self_healing.py' },
      { id: 22, nameEn: 'RepairStrategies', nameAr: 'استراتيجيات الإصلاح', category: 'healing', status: 'active', apiEndpoint: '/api/self-heal/patch', backendFile: 'core/self_healing.py' },
      { id: 23, nameEn: 'GitHubSelfUpdate', nameAr: 'التحديث الذاتي من GitHub', category: 'healing', status: 'standby', apiEndpoint: '/api/v23/healing/autonomous-update', backendFile: 'core/self_healing.py' },
    ],
  },
  {
    id: 6, nameAr: 'الأمان والضمير', nameEn: 'Safety & Conscience',
    features: [
      { id: 24, nameEn: 'ConscienceLayer', nameAr: 'طبقة الضمير', category: 'safety', status: 'active', apiEndpoint: '/api/security', backendFile: 'safety/conscience_layer.py' },
      { id: 25, nameEn: 'ReflexionEngineSafety', nameAr: 'محرك التأمل الأمني', category: 'safety', status: 'active', apiEndpoint: '/api/security', backendFile: 'core/reflexion_engine.py' },
      { id: 26, nameEn: 'AutonomyEngine', nameAr: 'محرك الاستقلالية', category: 'safety', status: 'active', apiEndpoint: '/api/autonomy', backendFile: 'core/autonomy_engine.py' },
      { id: 27, nameEn: 'SafetyGate', nameAr: 'بوابة الأمان', category: 'safety', status: 'active', apiEndpoint: '/api/security', backendFile: 'safety_gate/main.py' },
      { id: 28, nameEn: 'TimeBoundedPolicy', nameAr: 'سياسة الوقت المحدود', category: 'safety', status: 'active', apiEndpoint: '/api/security', backendFile: 'safety_gate/time_bounded_policy.py' },
      { id: 29, nameEn: 'LawsL1L8', nameAr: 'القوانين L1-L8', category: 'safety', status: 'active', apiEndpoint: '/api/security', backendFile: 'config.py' },
    ],
  },
  {
    id: 7, nameAr: 'أركان AGI السبعة', nameEn: '7 AGI Pillars',
    features: [
      { id: 30, nameEn: 'CausalGraph', nameAr: 'الرسم البياني السببي', category: 'agi', status: 'active', apiEndpoint: '/api/agi/causal', backendFile: 'core/causal_graph.py' },
      { id: 31, nameEn: 'EpisodicMemoryV2', nameAr: 'الذاكرة الحلقاتية V2', category: 'agi', status: 'active', apiEndpoint: '/api/agi/memory', backendFile: 'memory/episodic_memory_v2.py' },
      { id: 32, nameEn: 'MetacognitiveEngine', nameAr: 'محرك ما وراء المعرفة', category: 'agi', status: 'active', apiEndpoint: '/api/agi/meta', backendFile: 'core/metacognitive_engine.py' },
      { id: 33, nameEn: 'HierarchicalPlanner', nameAr: 'المخطط الهرمي', category: 'agi', status: 'active', apiEndpoint: '/api/agi/plan', backendFile: 'core/hierarchical_planner.py' },
      { id: 34, nameEn: 'WorldKnowledgeGraph', nameAr: 'رسم المعرفة العالمي', category: 'agi', status: 'idle', apiEndpoint: '/api/agi/world', backendFile: 'awareness/world_knowledge_graph.py' },
      { id: 35, nameEn: 'ConsequenceLearning', nameAr: 'تعلم العواقب', category: 'agi', status: 'evolving', apiEndpoint: '/api/agi/learn', backendFile: 'core/consequence_learning.py' },
      { id: 36, nameEn: 'SelectiveAttention', nameAr: 'الانتباه الانتقائي', category: 'agi', status: 'active', apiEndpoint: '/api/agi/attention', backendFile: 'core/selective_attention.py' },
    ],
  },
  {
    id: 8, nameAr: 'نظام التطور', nameEn: 'Evolution System',
    features: [
      { id: 37, nameEn: 'EvolutionLoop', nameAr: 'حلقة التطور', category: 'evolution', status: 'evolving', apiEndpoint: '/api/evolution', backendFile: 'evolution/evolution_loop.py' },
      { id: 38, nameEn: 'MutationEngine', nameAr: 'محرك الطفرات', category: 'evolution', status: 'evolving', apiEndpoint: '/api/evolution', backendFile: 'evolution/mutation_engine.py' },
      { id: 39, nameEn: 'FitnessEvaluator', nameAr: 'مقياس اللياقة', category: 'evolution', status: 'active', apiEndpoint: '/api/evolution/current', backendFile: 'evolution/fitness_evaluator.py' },
      { id: 40, nameEn: 'AgentCreator', nameAr: 'خالق الوكلاء', category: 'evolution', status: 'standby', apiEndpoint: '/api/evolution', backendFile: 'evolution/agent_creator.py' },
      { id: 41, nameEn: 'ImprovementProposer', nameAr: 'مقترح التحسينات', category: 'evolution', status: 'evolving', apiEndpoint: '/api/evolution', backendFile: 'evolution/improvement_proposer.py' },
      { id: 42, nameEn: 'SelfEvolutionScheduler', nameAr: 'جدول التطور الذاتي', category: 'evolution', status: 'active', apiEndpoint: '/api/evolution', backendFile: 'evolution/self_evolution_scheduler.py' },
      { id: 43, nameEn: 'ProceduralMemory', nameAr: 'الذاكرة الإجرائية', category: 'evolution', status: 'active', apiEndpoint: '/api/evolution', backendFile: 'evolution/procedural_memory.py' },
      { id: 44, nameEn: 'TrustedResearchFetcher', nameAr: 'جالب الأبحاث الموثوقة', category: 'evolution', status: 'standby', apiEndpoint: '/api/evolution', backendFile: 'evolution/trusted_research_fetcher.py' },
      { id: 45, nameEn: 'AutoEvolutionLoop', nameAr: 'حلقة التطور التلقائي', category: 'evolution', status: 'evolving', apiEndpoint: '/api/evolution-v19', backendFile: 'evolution/evolution_loop_auto.py' },
      { id: 46, nameEn: 'FluidReasoner', nameAr: 'المستدمر السائب', category: 'evolution', status: 'active', apiEndpoint: '/api/agi/fluid-reasoner', backendFile: 'agi/fluid_reasoner.py' },
    ],
  },
  {
    id: 9, nameAr: 'قدرات AGI', nameEn: 'AGI Capabilities',
    features: [
      { id: 47, nameEn: 'TheoryOfMind', nameAr: 'نظرية العقل', category: 'agi', status: 'active', apiEndpoint: '/api/agi/theory-of-mind', backendFile: 'agi/theory_of_mind.py' },
      { id: 48, nameEn: 'CommonSense', nameAr: 'الحس السليم', category: 'agi', status: 'active', apiEndpoint: '/api/agi/common-sense', backendFile: 'agi/common_sense.py' },
      { id: 49, nameEn: 'SwarmIntelligence', nameAr: 'ذكاء السرب', category: 'agi', status: 'idle', apiEndpoint: '/api/swarm', backendFile: 'agi/swarm_intelligence.py' },
      { id: 50, nameEn: 'ContinualLearning', nameAr: 'التعلم المستمر', category: 'agi', status: 'evolving', apiEndpoint: '/api/agi/continual-learning', backendFile: 'agi/continual_learning.py' },
      { id: 51, nameEn: 'SkillDiscovery', nameAr: 'اكتشاف المهارات', category: 'agi', status: 'active', apiEndpoint: '/api/agi/skill-discovery', backendFile: 'agi/skill_discovery.py' },
      { id: 52, nameEn: 'PrivacyGuard', nameAr: 'حارس الخصوصية', category: 'agi', status: 'active', apiEndpoint: '/api/agi/privacy', backendFile: 'agi/privacy_guard.py' },
      { id: 53, nameEn: 'CulturalAlignment', nameAr: 'المحاذاة الثقافية', category: 'agi', status: 'active', apiEndpoint: '/api/agi', backendFile: 'agi/cultural_alignment.py' },
      { id: 54, nameEn: 'HallucinationDetector', nameAr: 'كاشف الهلوسة', category: 'agi', status: 'active', apiEndpoint: '/api/agi/hallucination', backendFile: 'agi/hallucination_detector.py' },
      { id: 55, nameEn: 'IntentDrift', nameAr: 'انحراف النية', category: 'agi', status: 'active', apiEndpoint: '/api/agi/intent-drift', backendFile: 'agi/intent_drift.py' },
    ],
  },
  {
    id: 10, nameAr: 'قدرات الـ 12', nameEn: '12 Capabilities',
    features: [
      { id: 56, nameEn: 'LaptopControl', nameAr: 'التحكم بالحاسوب', category: 'capabilities', status: 'active', apiEndpoint: '/api/capabilities/laptop-control', backendFile: 'core/desktop_controller.py' },
      { id: 57, nameEn: 'Terminal', nameAr: 'الطرفية', category: 'capabilities', status: 'active', apiEndpoint: '/api/terminal', backendFile: 'terminal/agentic_terminal.py' },
      { id: 58, nameEn: 'ProfessionalCoding', nameAr: 'البرمجة الاحترافية', category: 'capabilities', status: 'active', apiEndpoint: '/api/capabilities/code', backendFile: 'core/code_generation_engine.py' },
      { id: 59, nameEn: 'SkillLearning', nameAr: 'تعلم المهارات', category: 'capabilities', status: 'active', apiEndpoint: '/api/agi/skill-discovery', backendFile: 'core/skill_executor.py' },
      { id: 60, nameEn: 'DeepResearch', nameAr: 'البحث العميق', category: 'capabilities', status: 'active', apiEndpoint: '/api/mamoun/kernel/capabilities', backendFile: 'core/deep_research_engine.py' },
      { id: 61, nameEn: 'ProjectBuilding', nameAr: 'بناء المشاريع', category: 'capabilities', status: 'active', apiEndpoint: '/api/build-project', backendFile: 'core/project_orchestrator.py' },
      { id: 62, nameEn: 'InstagramAnalysis', nameAr: 'تحليل إنستغرام', category: 'capabilities', status: 'idle', apiEndpoint: '/api/capabilities/instagram', backendFile: 'agents/social/instagram_manager.py' },
      { id: 63, nameEn: 'BlenderControl', nameAr: 'التحكم ببلندر', category: 'capabilities', status: 'standby', apiEndpoint: '/api/capabilities/blender', backendFile: 'physical/blender_controller.py' },
      { id: 64, nameEn: 'ProjectOrchestrator', nameAr: 'منسق المشاريع', category: 'capabilities', status: 'active', apiEndpoint: '/api/capabilities/projects', backendFile: 'core/project_orchestrator.py' },
      { id: 65, nameEn: 'AgentBrowser', nameAr: 'متصفح الوكيل', category: 'capabilities', status: 'active', apiEndpoint: '/api/capabilities/browser', backendFile: 'agents/browser/agent_browser.py' },
      { id: 66, nameEn: 'TestingSandbox', nameAr: 'بيئة الاختبار', category: 'capabilities', status: 'active', apiEndpoint: '/api/capabilities/sandbox', backendFile: 'core/sandbox_runner.py' },
      { id: 67, nameEn: 'TradingRoom', nameAr: 'غرفة التداول', category: 'capabilities', status: 'idle', apiEndpoint: '/api/capabilities/trading', backendFile: 'agents/trading/trading_engine.py' },
    ],
  },
  {
    id: 11, nameAr: 'الأنظمة الحية', nameEn: 'Living Systems',
    features: [
      { id: 68, nameEn: 'LivingState', nameAr: 'الحالة الحية', category: 'living', status: 'active', apiEndpoint: '/api/living/vitals', backendFile: 'core/living_state.py' },
      { id: 69, nameEn: 'EmotionalMemory', nameAr: 'الذاكرة العاطفية', category: 'living', status: 'active', apiEndpoint: '/api/living/emotions', backendFile: 'core/emotional_memory.py' },
      { id: 70, nameEn: 'DeepBonding', nameAr: 'الربط العميق', category: 'living', status: 'active', apiEndpoint: '/api/living/bonding', backendFile: 'core/deep_bonding.py' },
      { id: 71, nameEn: 'Reflexes', nameAr: 'المنعكسات', category: 'living', status: 'active', apiEndpoint: '/api/living/reflexes', backendFile: 'core/reflexes.py' },
      { id: 72, nameEn: 'AutonomicSystem', nameAr: 'الجهاز المستقل', category: 'living', status: 'active', apiEndpoint: '/api/living/heartbeat', backendFile: 'core/autonomic_system.py' },
      { id: 73, nameEn: 'SleepCycle', nameAr: 'دورة النوم', category: 'living', status: 'idle', apiEndpoint: '/api/sleep', backendFile: 'api/sleep_cycle.py' },
      { id: 74, nameEn: 'BehavioralMemory', nameAr: 'الذاكرة السلوكية', category: 'living', status: 'active', apiEndpoint: '/api/living/memory', backendFile: 'memory/behavioral_memory.py' },
      { id: 75, nameEn: 'NarrativeIdentity', nameAr: 'الهوية السردية', category: 'living', status: 'active', apiEndpoint: '/api/living/identity', backendFile: 'core/emotional_memory.py' },
      { id: 76, nameEn: 'EpisodicMemoryStore', nameAr: 'مخزن الذاكرة الحلقاتية', category: 'living', status: 'active', apiEndpoint: '/api/agi/memory', backendFile: 'memory/episodic_memory_store.py' },
      { id: 77, nameEn: 'StrategicForgetting', nameAr: 'النسيان الاستراتيجي', category: 'living', status: 'active', apiEndpoint: '/api/agi/memory', backendFile: 'memory/strategic_forgetting.py' },
    ],
  },
  {
    id: 12, nameAr: 'أنظمة الذاكرة', nameEn: 'Memory Systems',
    features: [
      { id: 78, nameEn: 'PredictiveMemory', nameAr: 'الذاكرة التنبؤية', category: 'memory', status: 'active', apiEndpoint: '/api/predictions', backendFile: 'core/predictive_memory.py' },
      { id: 79, nameEn: 'TripleMemory', nameAr: 'الذاكرة الثلاثية', category: 'memory', status: 'active', apiEndpoint: '/api/agi/memory', backendFile: 'core/triple_memory.py' },
      { id: 80, nameEn: 'WorkingMemory', nameAr: 'ذاكرة العمل', category: 'memory', status: 'active', apiEndpoint: '/api/mamoun/kernel/working-memory', backendFile: 'core/working_memory.py' },
      { id: 81, nameEn: 'ElasticWeightConsolidation', nameAr: 'تجميع الأوزان المرن', category: 'memory', status: 'evolving', apiEndpoint: '/api/agi/continual-learning', backendFile: 'learning/elastic_weight_consolidation.py' },
    ],
  },
  {
    id: 13, nameAr: 'أنظمة التعلم', nameEn: 'Learning Systems',
    features: [
      { id: 82, nameEn: 'SkillGeneralizer', nameAr: 'معمّم المهارات', category: 'learning', status: 'active', apiEndpoint: '/api/agi/skill-discovery', backendFile: 'learning/skill_generalizer.py' },
      { id: 83, nameEn: 'OneShotLearner', nameAr: 'المتعلم من طلقة واحدة', category: 'learning', status: 'evolving', apiEndpoint: '/api/agi/learn', backendFile: 'learning/one_shot_learner.py' },
      { id: 84, nameEn: 'ExperientialRLHF', nameAr: 'التعلم بالتجربة RLHF', category: 'learning', status: 'evolving', apiEndpoint: '/api/agi/learn', backendFile: 'core/experiential_rlhf.py' },
    ],
  },
  {
    id: 14, nameAr: 'الغرائز', nameEn: 'Instincts',
    features: [
      { id: 85, nameEn: 'SurvivalInstinct', nameAr: 'غريزة البقاء', category: 'instincts', status: 'idle', apiEndpoint: '/api/mamoun/instincts', backendFile: 'instincts/survival.py' },
      { id: 86, nameEn: 'CuriosityInstinct', nameAr: 'غريزة الفضول', category: 'instincts', status: 'active', apiEndpoint: '/api/mamoun/instincts', backendFile: 'instincts/curiosity.py' },
      { id: 87, nameEn: 'ConsistencyInstinct', nameAr: 'غريزة الاتساق', category: 'instincts', status: 'idle', apiEndpoint: '/api/mamoun/instincts', backendFile: 'instincts/consistency.py' },
      { id: 88, nameEn: 'EfficiencyInstinct', nameAr: 'غريزة الكفاءة', category: 'instincts', status: 'idle', apiEndpoint: '/api/mamoun/instincts', backendFile: 'instincts/efficiency.py' },
    ],
  },
  {
    id: 15, nameAr: 'الوعي الخارجي', nameEn: 'External Awareness',
    features: [
      { id: 89, nameEn: 'WorldMonitor', nameAr: 'مراقب العالم', category: 'awareness', status: 'active', apiEndpoint: '/api/awareness', backendFile: 'awareness/world_monitor.py' },
      { id: 90, nameEn: 'ImmuneSystem', nameAr: 'الجهاز المناعي', category: 'awareness', status: 'active', apiEndpoint: '/api/awareness', backendFile: 'awareness/immune_system.py' },
      { id: 91, nameEn: 'Mirror', nameAr: 'المرآة', category: 'awareness', status: 'active', apiEndpoint: '/api/awareness/state', backendFile: 'awareness/mirror.py' },
      { id: 92, nameEn: 'CausalWorldModel', nameAr: 'النموذج السببي للعالم', category: 'awareness', status: 'active', apiEndpoint: '/api/awareness', backendFile: 'awareness/causal_world_model.py' },
    ],
  },
  {
    id: 16, nameAr: 'الاستدلال', nameEn: 'Reasoning',
    features: [
      { id: 93, nameEn: 'SymbolicReasoner', nameAr: 'المستدل الرمزي', category: 'reasoning', status: 'active', apiEndpoint: '/api/agi', backendFile: 'reasoning/symbolic_reasoner.py' },
      { id: 94, nameEn: 'BayesianInference', nameAr: 'الاستدلال البايزي', category: 'reasoning', status: 'active', apiEndpoint: '/api/agi', backendFile: 'reasoning/bayesian_inference.py' },
      { id: 95, nameEn: 'ReinforcementLearning', nameAr: 'التعلم بالتعزيز', category: 'reasoning', status: 'evolving', apiEndpoint: '/api/agi/learn', backendFile: 'reasoning/reinforcement_learning.py' },
      { id: 96, nameEn: 'AbstractGeneralization', nameAr: 'التعميم المجرد', category: 'reasoning', status: 'active', apiEndpoint: '/api/agi', backendFile: 'reasoning/abstract_generalization.py' },
      { id: 97, nameEn: 'System2Reasoner', nameAr: 'مستدل النظام 2', category: 'reasoning', status: 'active', apiEndpoint: '/api/agi/system2', backendFile: 'core/system2_reasoner.py' },
    ],
  },
  {
    id: 17, nameAr: 'الوكيل الفائق', nameEn: 'Hyperagent',
    features: [
      { id: 98, nameEn: 'CausalReasoner', nameAr: 'المستدل السببي', category: 'hyperagent', status: 'active', apiEndpoint: '/api/agi/causal', backendFile: 'core/causal_reasoner.py' },
      { id: 99, nameEn: 'MetaAgent', nameAr: 'الوكيل الفوقي', category: 'hyperagent', status: 'active', apiEndpoint: '/api/hyperagent/meta', backendFile: 'hyperagent/meta_agent.py' },
      { id: 100, nameEn: 'SupraMetaAgent', nameAr: 'الوكيل الفوقي الأعلى', category: 'hyperagent', status: 'active', apiEndpoint: '/api/hyperagent/supra', backendFile: 'hyperagent/supra_meta_agent.py' },
      { id: 101, nameEn: 'HyperagentLoop', nameAr: 'حلقة الوكيل الفائق', category: 'hyperagent', status: 'active', apiEndpoint: '/api/hyperagent/status', backendFile: 'hyperagent/hyperagent_loop.py' },
      { id: 102, nameEn: 'CurriculumController', nameAr: 'متحكم المنهج', category: 'hyperagent', status: 'active', apiEndpoint: '/api/hyperagent/curriculum', backendFile: 'hyperagent/curriculum_controller.py' },
      { id: 103, nameEn: 'FutureSimulator', nameAr: 'محاكي المستقبل', category: 'hyperagent', status: 'active', apiEndpoint: '/api/hyperagent/status', backendFile: 'hyperagent/future_simulator.py' },
      { id: 104, nameEn: 'EvolutionArchive', nameAr: 'أرشيف التطور', category: 'hyperagent', status: 'active', apiEndpoint: '/api/hyperagent/archive', backendFile: 'hyperagent/evolution_archive.py' },
      { id: 105, nameEn: 'SynapticIntelligence', nameAr: 'الذكاء المشبكي', category: 'hyperagent', status: 'evolving', apiEndpoint: '/api/v25/transfer', backendFile: 'transfer/synaptic_intelligence.py' },
      { id: 106, nameEn: 'KnowledgeBridge', nameAr: 'جسر المعرفة', category: 'hyperagent', status: 'active', apiEndpoint: '/api/v25/bridge', backendFile: 'transfer/knowledge_bridge.py' },
      { id: 107, nameEn: 'DomainAdapter', nameAr: 'مكيّف النطاق', category: 'hyperagent', status: 'active', apiEndpoint: '/api/v25/transfer', backendFile: 'transfer/domain_adapter.py' },
    ],
  },
  {
    id: 18, nameAr: 'الشبكة العصبية', nameEn: 'Neural Network',
    features: [
      { id: 108, nameEn: 'NeuralMesh', nameAr: 'الشبكة العصبية', category: 'neural', status: 'active', apiEndpoint: '/api/v25/neural', backendFile: 'neural/neural_mesh.py' },
      { id: 109, nameEn: 'HebbianLearner', nameAr: 'المتعلم الهيبي', category: 'neural', status: 'active', apiEndpoint: '/api/v25/neural', backendFile: 'neural/hebbian_learner.py' },
      { id: 110, nameEn: 'STDPSynapse', nameAr: 'المشبك STDP', category: 'neural', status: 'active', apiEndpoint: '/api/v25/neural', backendFile: 'neural/stdp_synapse.py' },
    ],
  },
  {
    id: 19, nameAr: 'التخطيط', nameEn: 'Planning',
    features: [
      { id: 111, nameEn: 'HierarchicalGoalManager', nameAr: 'مدير الأهداف الهرمي', category: 'planning', status: 'active', apiEndpoint: '/api/agi/plan', backendFile: 'planning/hierarchical_goal_manager.py' },
      { id: 112, nameEn: 'BudgetMonitor', nameAr: 'مراقب الميزانية', category: 'planning', status: 'active', apiEndpoint: '/api/agi/plan', backendFile: 'planning/budget_monitor.py' },
      { id: 113, nameEn: 'ConstraintEngine', nameAr: 'محرك القيود', category: 'planning', status: 'active', apiEndpoint: '/api/agi/plan', backendFile: 'planning/constraint_engine.py' },
    ],
  },
  {
    id: 20, nameAr: 'المشاعر', nameEn: 'Emotions',
    features: [
      { id: 114, nameEn: 'MultimodalEmotionEngine', nameAr: 'محرك المشاعر متعدد الوسائط', category: 'emotion', status: 'active', apiEndpoint: '/api/emotion', backendFile: 'emotion/multimodal_emotion_engine.py' },
    ],
  },
  {
    id: 21, nameAr: 'الإبداع', nameEn: 'Creativity',
    features: [
      { id: 115, nameEn: 'NoveltyScorer', nameAr: 'مقياس الجدة', category: 'creativity', status: 'active', apiEndpoint: '/api/creativity', backendFile: 'creative/novelty_scorer.py' },
      { id: 116, nameEn: 'OriginalityEngine', nameAr: 'محرك الأصالة', category: 'creativity', status: 'active', apiEndpoint: '/api/creativity', backendFile: 'creative/originality_engine.py' },
      { id: 117, nameEn: 'IdeaGenerator', nameAr: 'مولّد الأفكار', category: 'creativity', status: 'active', apiEndpoint: '/api/creativity', backendFile: 'creative/idea_generator.py' },
    ],
  },
  {
    id: 22, nameAr: 'الجسد الرقمي', nameEn: 'Digital Body',
    features: [
      { id: 118, nameEn: 'IoTGateway', nameAr: 'بوابة إنترنت الأشياء', category: 'embodiment', status: 'standby', apiEndpoint: '/api/embodiment', backendFile: 'physical/iot_gateway.py' },
      { id: 119, nameEn: 'EmbodimentService', nameAr: 'خدمة التجسيد', category: 'embodiment', status: 'standby', apiEndpoint: '/api/embodiment', backendFile: 'physical/embodiment_service.py' },
      { id: 120, nameEn: 'BlenderController', nameAr: 'متحكم بلندر', category: 'embodiment', status: 'standby', apiEndpoint: '/api/capabilities/blender', backendFile: 'physical/blender_controller.py' },
      { id: 121, nameEn: 'RobotController', nameAr: 'متحكم الروبوت', category: 'embodiment', status: 'standby', apiEndpoint: '/api/embodiment', backendFile: 'physical/robot_controller.py' },
    ],
  },
  {
    id: 23, nameAr: 'الوكلاء', nameEn: 'Agents',
    features: [
      { id: 122, nameEn: 'OmniAgent', nameAr: 'الوكيل الشامل', category: 'agents', status: 'active', apiEndpoint: '/api/capabilities/orchestrator', backendFile: 'agents/omni_agent.py' },
      { id: 123, nameEn: 'VisionAgent', nameAr: 'وكيل الرؤية', category: 'agents', status: 'active', apiEndpoint: '/api/capabilities', backendFile: 'agents/vision_agent.py' },
      { id: 124, nameEn: 'VoiceAgent', nameAr: 'وكيل الصوت', category: 'agents', status: 'active', apiEndpoint: '/api/capabilities', backendFile: 'agents/voice_agent.py' },
      { id: 125, nameEn: 'ScreenAgent', nameAr: 'وكيل الشاشة', category: 'agents', status: 'active', apiEndpoint: '/api/capabilities', backendFile: 'agents/screen_agent.py' },
      { id: 126, nameEn: 'SiteBuilderAgent', nameAr: 'وكيل بناء المواقع', category: 'agents', status: 'active', apiEndpoint: '/api/capabilities', backendFile: 'agents/site_builder_agent.py' },
      { id: 127, nameEn: 'AgentBrowser', nameAr: 'متصفح الوكيل', category: 'agents', status: 'active', apiEndpoint: '/api/capabilities/browser', backendFile: 'agents/browser/agent_browser.py' },
      { id: 128, nameEn: 'TradingEngine', nameAr: 'محرك التداول', category: 'agents', status: 'idle', apiEndpoint: '/api/capabilities/trading', backendFile: 'agents/trading/trading_engine.py' },
      { id: 129, nameEn: 'InstagramManager', nameAr: 'مدير إنستغرام', category: 'agents', status: 'idle', apiEndpoint: '/api/capabilities/instagram', backendFile: 'agents/social/instagram_manager.py' },
      { id: 130, nameEn: 'MobileAppBuilder', nameAr: 'باني التطبيقات', category: 'agents', status: 'standby', apiEndpoint: '/api/capabilities', backendFile: 'agents/mobile/mobile_app_builder.py' },
      { id: 131, nameEn: 'SelfDeployment', nameAr: 'النشر الذاتي', category: 'agents', status: 'standby', apiEndpoint: '/api/capabilities', backendFile: 'agents/mobile/self_deployment.py' },
      { id: 132, nameEn: 'SupplierConnector', nameAr: 'رابط الموردين', category: 'agents', status: 'standby', apiEndpoint: '/api/capabilities', backendFile: 'agents/ecommerce/supplier_connector.py' },
      { id: 133, nameEn: 'AgenticStoreBuilder', nameAr: 'باني المتجر الذكي', category: 'agents', status: 'standby', apiEndpoint: '/api/capabilities', backendFile: 'agents/ecommerce/agentic_store_builder.py' },
      { id: 134, nameEn: 'DynamicUI', nameAr: 'واجهة ديناميكية', category: 'agents', status: 'active', apiEndpoint: '/api/a2ui', backendFile: 'a2ui/dynamic_ui.py' },
      { id: 135, nameEn: 'AgenticTerminal', nameAr: 'الطرفية الذكية', category: 'agents', status: 'active', apiEndpoint: '/api/terminal', backendFile: 'terminal/agentic_terminal.py' },
    ],
  },
  {
    id: 24, nameAr: 'أنظمة المساعدة', nameEn: 'Support Systems',
    features: [
      { id: 136, nameEn: 'FileSystemTool', nameAr: 'أداة نظام الملفات', category: 'tools', status: 'active', apiEndpoint: '/api/terminal', backendFile: 'tools/filesystem_tool.py' },
      { id: 137, nameEn: 'ShellExecutor', nameAr: 'منفذ الأوامر', category: 'tools', status: 'active', apiEndpoint: '/api/terminal', backendFile: 'tools/shell_executor.py' },
      { id: 138, nameEn: 'AbsoluteExecutor', nameAr: 'المنفذ المطلق', category: 'tools', status: 'active', apiEndpoint: '/api/terminal/approvals', backendFile: 'core/absolute_executor.py' },
      { id: 139, nameEn: 'ResearchAgent', nameAr: 'وكيل البحث', category: 'tools', status: 'active', apiEndpoint: '/api/mamoun/kernel/capabilities', backendFile: 'core/research_agent.py' },
      { id: 140, nameEn: 'ResearchMonitor', nameAr: 'مراقب الأبحاث', category: 'tools', status: 'active', apiEndpoint: '/api/mamoun/kernel/capabilities', backendFile: 'research_monitor/monitor.py' },
    ],
  },
  {
    id: 25, nameAr: 'التواصل و API', nameEn: 'Communication & API',
    features: [
      { id: 141, nameEn: 'TemporalAwareness', nameAr: 'الوعي الزمني', category: 'api', status: 'active', apiEndpoint: '/api/temporal', backendFile: 'core/temporal_awareness.py' },
      { id: 142, nameEn: 'MetaAnalyzer', nameAr: 'المحلل الفوقي', category: 'api', status: 'active', apiEndpoint: '/api/awareness/meta', backendFile: 'core/meta_analyzer.py' },
      { id: 143, nameEn: 'DataManager', nameAr: 'مدير البيانات', category: 'api', status: 'active', apiEndpoint: '/api/mamoun', backendFile: 'core/data_manager.py' },
      { id: 144, nameEn: 'BackupManager', nameAr: 'مدير النسخ الاحتياطي', category: 'api', status: 'active', apiEndpoint: '/api/admin/backup', backendFile: 'core/backup_manager.py' },
      { id: 145, nameEn: 'WebSocket', nameAr: 'ويب سوكيت', category: 'api', status: 'active', apiEndpoint: '/api/events', backendFile: 'api/ws.py' },
      { id: 146, nameEn: 'SSE', nameAr: 'الأحداث المباشرة', category: 'api', status: 'active', apiEndpoint: '/api/events', backendFile: 'api/events.py' },
      { id: 147, nameEn: 'AuthSystem', nameAr: 'نظام المصادقة', category: 'api', status: 'active', apiEndpoint: '/api/auth', backendFile: 'core/auth.py' },
      { id: 148, nameEn: 'AllAPIRoutes', nameAr: 'جميع مسارات API', category: 'api', status: 'active', apiEndpoint: '/api/mamoun', backendFile: 'api/routes.py' },
    ],
  },
];

export function getAllFeatures(): DashboardFeature[] {
  return DASHBOARD_SECTIONS.flatMap(s => s.features);
}

export function getStatusCounts(categoryPrefixes: string[]) {
  const all = getAllFeatures();
  const filtered = all.filter(f => categoryPrefixes.includes(f.category));
  const active = filtered.filter(f => f.status === 'active').length;
  return { active, total: filtered.length };
}

export const SUBSYSTEMS = [
  { id: 'core', labelAr: 'النواة', prefixes: ['core'] },
  { id: 'brains', labelAr: 'الأدمغة', prefixes: ['brains'] },
  { id: 'agi', labelAr: 'AGI', prefixes: ['agi'] },
  { id: 'evolution', labelAr: 'التطور', prefixes: ['evolution'] },
  { id: 'living', labelAr: 'الحياة', prefixes: ['living', 'emotion'] },
  { id: 'memory', labelAr: 'الذاكرة', prefixes: ['memory', 'learning'] },
  { id: 'safety', labelAr: 'الأمان', prefixes: ['safety', 'healing'] },
] as const;
