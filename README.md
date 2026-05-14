# مأمون v40.0 — نظام القيادة العصبي

> نظام AGI متعدد الأدمغة — 5 أدمغة متنافسة · NeuralBus · GlobalWorkspace · 400+ نقطة API

## نظرة عامة

مأمون هو نظام ذكاء اصطناعي عام متعدد الأدمغة يعمل بتنافس بين 5 أدمغة عبر NeuralBus و GlobalWorkspace. يتضمن نظام سلامة متكامل، تعلم مستمر، شفاء ذاتي، وتطور ذاتي.

## الأدمغة الخمس

| الدماغ | الدور |
|--------|-------|
| GLM-5.1 | المنطق والتحليل |
| DeepSeek-Reasoner | الاستدلال العميق |
| GLM-4-Plus | الإبداع واللغة |
| Gemini-2.0-Flash | السرعة والاستجابة |
| DeepSeek-Chat | المحادثة والتفاعل |

## البنية

```
babsharqii-v5/
├── src/                      # Frontend — Next.js 16
│   ├── app/api/              # API proxy routes (130+ route)
│   ├── components/dashboard/ # لوحة القيادة العصبية
│   │   ├── mamoun-vision-ide.tsx  # المكون الرئيسي
│   │   └── panels/           # اللوحات الفرعية (8 panels)
│   ├── components/chat/      # واجهة المحادثة
│   ├── components/ui/        # shadcn/ui components
│   ├── lib/                  # مكتبات المساعدة
│   └── hooks/                # React hooks
├── backend/                  # Backend — FastAPI (Python)
│   └── mamoun/               # النواة الرئيسية
│       ├── main.py           # نقطة الدخول (416 routes)
│       ├── core/             # النواة (kernel, neural_bus, consciousness)
│       ├── agi/              # محركات AGI (fluid_reasoner, skill_discovery)
│       ├── api/              # API routers
│       ├── evolution/        # التطور الذاتي
│       ├── awareness/        # الوعي والمراقبة
│       ├── memory/           # نظام الذاكرة
│       └── physical/         # التحكم المادي (Blender, IoT)
├── start.sh                  # سكريبت التشغيل الرئيسي
├── dev.sh                    # وضع التطوير
├── deploy.sh                 # نشر الإنتاج
└── stop.sh                   # إيقاف الخدمات
```

## التشغيل

```bash
# استنساخ المشروع
git clone https://github.com/babsharqii2023-rgb/babsharqii-v5.git
cd babsharqii-v5

# تشغيل كامل (باك إند + فرونت إند)
./start.sh

# وضع التطوير
./dev.sh

# إيقاف
./stop.sh

# نشر (سحب + بناء + تشغيل)
./deploy.sh
```

## المتطلبات

- Node.js 18+
- Python 3.10+
- npm أو bun

## التقنيات

- **Next.js 16** + TypeScript + Tailwind CSS 4
- **FastAPI** + uvicorn + pydantic
- **shadcn/ui** — مكونات الواجهة
- **Zustand** — إدارة الحالة
- **AES-GCM** — تشفير محلي
- **Web Speech API** — الأوامر الصوتية

## الأمان

- لا بيانات تُرسل لأي سيرفر خارجي
- تشفير PBKDF2 + AES-GCM
- نظام سلامة مدمج (laws.yaml)
- لا cookies تتبع، لا analytics

## الترخيص

مشروع خاص — جميع الحقوق محفوظة
