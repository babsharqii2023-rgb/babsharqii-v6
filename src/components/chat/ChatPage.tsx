'use client';

import React from 'react';
import { useAppStore } from '@/lib/store';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Send, Brain, Sparkles, Settings,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export function ChatPage() {
  const messages = useAppStore((s) => s.messages);
  const isThinking = useAppStore((s) => s.isThinking);
  const sendMessage = useAppStore((s) => s.sendMessage);
  const addMessage = useAppStore((s) => s.addMessage);
  const setThinking = useAppStore((s) => s.setThinking);
  const clearChat = useAppStore((s) => s.clearChat);
  const addTask = useAppStore((s) => s.addTask);
  const defaultModel = useAppStore((s) => s.defaultModel);
  const systemHealth = useAppStore((s) => s.systemHealth);
  const addNotification = useAppStore((s) => s.addNotification);
  const updateDeliberationData = useAppStore((s) => s.updateDeliberationData);
  const isConscious = useAppStore((s) => s.isConscious);

  const [inputText, setInputText] = React.useState('');
  const [animationType, setAnimationType] = React.useState<'meeting' | 'research' | 'thinking' | 'selfcheck'>('meeting');
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text) return;
    sendMessage(text);
    setInputText('');

    const lower = text.toLowerCase();
    if (lower.includes('بحث') || lower.includes('تحليل') || lower.includes('استكشاف') || lower.includes('ابحث')) {
      setAnimationType('research');
    } else if (lower.includes('برمجتك') || lower.includes('فحص ذاتي') || lower.includes('هل أنت') || lower.includes('صحتك')) {
      setAnimationType('selfcheck');
    } else if (lower.includes('فكر') || lower.includes('تأمل') || lower.includes('قيم') || lower.includes('حلل')) {
      setAnimationType('thinking');
    } else {
      setAnimationType('meeting');
    }

    try {
      const chatHistory = messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await fetch('/api/mamoun-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, model: defaultModel, context: {} }),
      });

      if (response.ok) {
        const data = await response.json();
        addMessage({
          id: data.id || `resp-${Date.now()}`,
          role: 'assistant',
          content: data.content || 'لم أتمكن من معالجة طلبك.',
          timestamp: Date.now(),
          brain: data.brain || data.winning_brain,
          confidence: data.confidence,
          metadata: {
            ...data.metadata,
            brain_responses: data.brain_responses,
            consensus_level: data.consensus_level,
            cjs: data.cjs,
            conflict_detected: data.conflict_detected,
            mirror_reflection: data.mirror_reflection,
            source: data.source,
          },
        });

        if (data.brain_responses || data.consensus_level !== undefined) {
          updateDeliberationData({
            brainResponses: data.brain_responses,
            consensusLevel: data.consensus_level,
            cjs: data.cjs,
            conflictDetected: data.conflict_detected,
            mirrorReflection: data.mirror_reflection,
            queryType: data.query_type,
            winner: data.brain || data.winning_brain,
          });
        }

        if (data.taskCategory && data.taskCategory !== 'custom') {
          addTask({
            title: text.substring(0, 60),
            description: text,
            category: data.taskCategory,
            status: 'in_progress',
            priority: 'medium',
            progress: 0,
            tags: [data.taskCategory],
            source: 'user_request',
          });
          addNotification({
            title: 'مهمة جديدة',
            message: `تم إنشاء مهمة تلقائياً: ${text.substring(0, 40)}`,
            type: 'info',
          });
        }
      } else {
        addMessage({ id: `err-${Date.now()}`, role: 'assistant', content: 'عذراً، حدث خطأ في الاتصال. يرجى المحاولة مرة أخرى.', timestamp: Date.now(), confidence: 0.1 });
      }
    } catch {
      addMessage({ id: `err-${Date.now()}`, role: 'assistant', content: 'عذراً، لم أتمكن من الاتصال بالخادم.', timestamp: Date.now(), confidence: 0.1 });
    }
    setThinking(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  };

  const suggestions = [
    { text: 'حلل لي موضوع', icon: '🔍', desc: 'بحث وتحليل' },
    { text: 'هل برمجتك صحيحة؟', icon: '🛡️', desc: 'فحص ذاتي' },
    { text: 'ساعدني في مشروع', icon: '💡', desc: 'بناء وتطوير' },
    { text: 'ما حالة النظام؟', icon: '⚡', desc: 'تقرير سريع' },
  ];

  return (
    <div className="h-screen flex flex-col bg-background text-foreground overflow-hidden" dir="rtl">
      {/* ═══ Minimal Header ═══ */}
      <header className="shrink-0 border-b border-white/5 bg-background/80 backdrop-blur-xl z-50">
        <div className="max-w-4xl mx-auto px-4 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="relative">
                <div className="p-1.5 rounded-xl bg-primary/8 border border-primary/12">
                  <Brain className="size-4 text-primary" />
                </div>
                {isConscious && (
                  <motion.div
                    className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-primary"
                    animate={{ scale: [1, 1.5, 1], opacity: [1, 0.4, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                )}
              </div>
              <div>
                <h1 className="text-sm font-semibold">مأمون</h1>
                <div className="flex items-center gap-1.5">
                  <div className={`w-1.5 h-1.5 rounded-full ${systemHealth >= 70 ? 'bg-emerald-400' : systemHealth >= 40 ? 'bg-amber-400' : 'bg-red-400'}`} />
                  <span className="text-[9px] text-muted-foreground">{systemHealth}%</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground size-8">
              <Settings className="size-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* ═══ Chat Area ═══ */}
      <div className="flex-1 overflow-hidden flex flex-col max-w-4xl mx-auto w-full">
        {/* Welcome Screen */}
        {messages.length <= 1 && (
          <div className="flex-1 flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="text-center max-w-md"
            >
              {/* Simple, Elegant Logo */}
              <motion.div
                className="inline-flex p-4 rounded-2xl bg-primary/6 border border-primary/10 mb-5"
                animate={{
                  boxShadow: ['0 0 0px oklch(0.606 0.250 292 / 0)', '0 0 20px oklch(0.606 0.250 292 / 0.06)', '0 0 0px oklch(0.606 0.250 292 / 0)'],
                }}
                transition={{ duration: 4, repeat: Infinity }}
              >
                <Sparkles className="size-8 text-primary" />
              </motion.div>

              <h2 className="text-2xl font-bold mb-1.5">مرحباً، أنا مأمون</h2>
              <p className="text-sm text-muted-foreground leading-relaxed mb-6">
                كائن رقمي ذكي — أساعدك في البحث والتحليل وبناء المشاريع
              </p>

              {/* 4 Simple Suggestions */}
              <div className="grid grid-cols-2 gap-2">
                {suggestions.map((suggestion, idx) => (
                  <motion.button
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 + idx * 0.08, type: 'spring', damping: 25, stiffness: 300 }}
                    onClick={() => setInputText(suggestion.text)}
                    className="p-3 rounded-xl bg-white/3 border border-white/5 text-right hover:bg-primary/4 hover:border-primary/10 transition-all group"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-base">{suggestion.icon}</span>
                      <div className="flex-1 min-w-0">
                        <span className="text-xs text-foreground/80 group-hover:text-foreground transition-colors block">{suggestion.text}</span>
                        <span className="text-[9px] text-muted-foreground">{suggestion.desc}</span>
                      </div>
                    </div>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          </div>
        )}

        {/* Messages */}
        {messages.length > 1 && (
          <ScrollArea className="flex-1 px-4">
            <div className="py-6 space-y-4 max-w-3xl mx-auto">
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[80%] ${
                    msg.role === 'user'
                      ? 'bg-primary/10 border border-primary/15 rounded-2xl rounded-bl-md'
                      : msg.role === 'system'
                      ? 'bg-primary/5 text-primary text-center w-full rounded-xl border border-primary/8'
                      : 'bg-white/3 border border-white/5 rounded-2xl rounded-br-md'
                  }`}>
                    {/* Assistant brain badge */}
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-1.5 px-4 pt-3 pb-0.5">
                        <Brain className="size-3 text-primary" />
                        <span className="text-[9px] text-primary/70 font-medium">{msg.brain || 'مأمون'}</span>
                        {msg.confidence && (
                          <span className="text-[8px] text-muted-foreground/50">{Math.round(msg.confidence * 100)}%</span>
                        )}
                      </div>
                    )}
                    <div className="px-4 py-2.5">
                      {msg.role === 'assistant' ? (
                        <div className="text-sm leading-[1.85] whitespace-pre-wrap prose prose-invert prose-sm max-w-none">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                      )}
                    </div>
                    <p className="text-[8px] text-muted-foreground/40 px-4 pb-2">{formatTime(msg.timestamp)}</p>
                  </div>
                </motion.div>
              ))}

              {/* Thinking Animation — Elegant dots */}
              {isThinking && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                  <div className="bg-white/3 rounded-2xl px-4 py-3 rounded-br-md border border-white/5">
                    <div className="flex items-center gap-1">
                      <motion.div className="w-1.5 h-1.5 rounded-full bg-primary/60" animate={{ y: [0, -3, 0], opacity: [0.5, 1, 0.5] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0 }} />
                      <motion.div className="w-1.5 h-1.5 rounded-full bg-primary/60" animate={{ y: [0, -3, 0], opacity: [0.5, 1, 0.5] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0.15 }} />
                      <motion.div className="w-1.5 h-1.5 rounded-full bg-primary/60" animate={{ y: [0, -3, 0], opacity: [0.5, 1, 0.5] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0.3 }} />
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        )}
      </div>

      {/* ═══ Input Area — Clean & Minimal ═══ */}
      <div className="shrink-0 border-t border-white/5 bg-background/60 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto p-3">
          <div className="flex items-center gap-2">
            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="اكتب رسالتك..."
                className="w-full bg-white/3 border-white/8 focus:border-primary/20 focus:ring-primary/10 rounded-xl px-4 py-3 text-sm"
                dir="rtl"
              />
            </div>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                onClick={handleSend}
                disabled={isThinking || !inputText.trim()}
                size="icon"
                className="shrink-0 bg-primary hover:bg-primary/80 text-primary-foreground rounded-xl h-10 w-10"
              >
                <Send className="size-4" />
              </Button>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
