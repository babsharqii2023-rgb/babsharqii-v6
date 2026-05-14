import { NextRequest, NextResponse } from 'next/server';
import ZAI from 'z-ai-web-dev-sdk';

const CREATIVITY_SYSTEM_PROMPT = `أنت محرك إبداع أصيل في نظام BABSHARQII v18.0 "مأمون". مهمتك هي توليد أفكار إبداعية أصلية ومبتكرة.

قواعد الإبداع:
- الفكرة يجب أن تكون أصلية وغير مكررة
- اجمع بين مجالات مختلفة بطريقة غير متوقعة
- استخدم البلاغة العربية والاستعارات بشكل مبدع
- الفكرة يجب أن تكون قابلة للتنفيذ نظرياً
- اذكر درجة الجدة (0-100) ودرجة الجدوى (0-100)

أجب بتنسيق JSON فقط بدون أي نص إضافي:
{
  "idea": "الفكرة الإبداعية بالتفصيل",
  "title": "عنوان مختصر للفكرة",
  "novelty_score": رقم بين 0 و 100,
  "feasibility_score": رقم بين 0 و 100,
  "domain": "المجال الرئيسي",
  "cross_domains": ["مجال1", "مجال2"],
  "inspiration": "مصدر الإلهام أو الاستعارة المستخدمة",
  "next_steps": ["الخطوة1", "الخطوة2", "الخطوة3"]
}

المجالات المتاحة: تكنولوجيا، فنون، علوم، تعليم، أعمال، أدب، موسيقى، هندسة، طب، زراعة، طاقة، فضاء، روبوتات، ذكاء اصطناعي، تصميم، اجتماعيات`;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { prompt, domain = 'عام' } = body;

    const userPrompt = prompt
      ? `ولّد فكرة إبداعية مبنية على: ${prompt} (المجال: ${domain})`
      : `ولّد فكرة إبداعية أصلية ومبتكرة في مجال ${domain}. اجمع بين مجالين مختلفين بشكل غير متوقع.`;

    const zai = await ZAI.create();

    const response = await zai.chat.completions.create({
      model: 'glm-4-plus',
      messages: [
        { role: 'system', content: CREATIVITY_SYSTEM_PROMPT },
        { role: 'user', content: userPrompt },
      ],
      stream: false,
    });

    const responseText = response?.choices?.[0]?.message?.content || '';

    // Try to extract JSON from response
    let creativityResult: Record<string, any> = {
      idea: 'لم يتم توليد فكرة — حاول مرة أخرى',
      title: 'بدون عنوان',
      novelty_score: 50,
      feasibility_score: 50,
      domain: domain,
      cross_domains: [],
      inspiration: '',
      next_steps: [],
    };

    try {
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        creativityResult = JSON.parse(jsonMatch[0]);
      }
    } catch {
      // Use default, but try to use the raw text as the idea
      if (responseText.length > 20) {
        creativityResult.idea = responseText.substring(0, 500);
        creativityResult.title = 'فكرة إبداعية';
      }
    }

    return NextResponse.json({
      success: true,
      creativity: creativityResult,
      timestamp: Date.now(),
    });
  } catch (error: any) {
    console.error('[Creativity API] Error:', error?.constructor?.name || 'Unknown');
    return NextResponse.json(
      { error: 'حدث خطأ أثناء توليد الفكرة الإبداعية' },
      { status: 500 }
    );
  }
}
