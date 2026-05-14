import { NextRequest, NextResponse } from 'next/server';
import ZAI from 'z-ai-web-dev-sdk';

const EMOTION_SYSTEM_PROMPT = `أنت محلل عواطف متقدم في نظام BABSHARQII v18.0. مهمتك هي تحليل النص العربي أو الإنجليزي وتحديد العاطفة الأساسية والعواطف الفرعية.

أجب بتنسيق JSON فقط بدون أي نص إضافي:
{
  "primary_emotion": "اسم العاطفة الأساسية بالعربية",
  "primary_emotion_en": "primary emotion in English",
  "confidence": رقم بين 0 و 1 يمثل مستوى الثقة,
  "valence": رقم بين -1 و 1 (سلبي إلى إيجابي),
  "arousal": رقم بين 0 و 1 (هادئ إلى منفعل),
  "secondary_emotions": ["عاطفة فرعية 1", "عاطفة فرعية 2"],
  "sarcasm_detected": true أو false,
  "frustration_detected": true أو false,
  "explanation": "شرح مختصر بالعربية لسبب هذا التحليل"
}

العواطف الممكنة: سعادة، حزن، غضب، خوف، مفاجأة، اشمئزاز، حب، فضول، حيرة، أمل، إحباط، فخر، حنين، قلق، حماس، رضا، سخرية، ملل، امتنان، استياء`;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { text, language = 'ar' } = body;

    if (!text || typeof text !== 'string') {
      return NextResponse.json(
        { error: 'النص مطلوب للتحليل' },
        { status: 400 }
      );
    }

    const sanitizedText = text.substring(0, 5000);

    const zai = await ZAI.create();

    const response = await zai.chat.completions.create({
      model: 'glm-4-plus',
      messages: [
        { role: 'system', content: EMOTION_SYSTEM_PROMPT },
        { role: 'user', content: `حلل العاطفة في هذا النص:\n\n${sanitizedText}` },
      ],
      stream: false,
    });

    const responseText = response?.choices?.[0]?.message?.content || '';

    // Try to extract JSON from response
    let emotionResult: Record<string, any> = {
      primary_emotion: 'حياد',
      primary_emotion_en: 'neutral',
      confidence: 0.5,
      valence: 0,
      arousal: 0.3,
      secondary_emotions: [],
      sarcasm_detected: false,
      frustration_detected: false,
      explanation: 'لم يتمكن من تحليل العاطفة بدقة',
    };

    try {
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        emotionResult = JSON.parse(jsonMatch[0]);
      }
    } catch {
      // Use default result
    }

    return NextResponse.json({
      success: true,
      emotion: emotionResult,
      timestamp: Date.now(),
    });
  } catch (error: any) {
    console.error('[Emotion API] Error:', error?.constructor?.name || 'Unknown');
    return NextResponse.json(
      { error: 'حدث خطأ أثناء تحليل العواطف' },
      { status: 500 }
    );
  }
}
