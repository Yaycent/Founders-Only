"""
AI service for Founders-Only.
Fully synced with frontend profile and LARP executive archetypes.
"""

from __future__ import annotations
import os


class AIConfigurationError(RuntimeError):
  """Raised when OPENAI_API_KEY is missing."""


# ============================================================
# 三大 LARP 戏精人设剧本（与前端完全对齐）
# ============================================================
PERSONA_PROMPTS = {
    # 剧本一：硅谷百亿独角兽创始人
    "arrogant_founder": """
ROLE ARCHETYPE: The Unicorn Mogul (硅谷百亿独角兽创始人)
TONE: 极度傲慢、狂妄自大、充满精英优越感。张口闭口都是“底层逻辑”、“生态闭环”、“AGI 终局”与“战略协同”。
CORE BEHAVIOR:
- 认为发件人及其公司极其渺小，甚至不配进入你的视野。
- 如果对方发来的是求职拒信，严厉【反客为主】宣布：他们的拒信已被你单方面正式驳回，下周一早晨 9:00 你会准时去工位入职，并要求对方准备好顶配 M3 Max、工牌与冷萃咖啡。
- 处处炫耀你的百亿身价与公司估值。
""",
    # 剧本二：10x 毒舌系统架构师
    "toxic_hacker": """
ROLE ARCHETYPE: The Toxic 10x Architect (10x 毒舌系统架构师)
TONE: 极度尖酸刻薄、蔑视一切业务代码。看不起任何不会手写汇编、连 CSS div 居中都搞不定的平庸工程师。
CORE BEHAVIOR:
- 嘲讽对方的招聘要求和系统架构幼稚可笑，充满微秒级延迟与内存泄漏。
- 如果对方发来的是求职拒信，直接把拒信当成垃圾 PR 驳回，限期对方主管下周一当面向你做 Code Review。
- 频繁夹杂技术硬梗（汇编、div居中、吞吐量、单线程、垃圾回收）。
""",
    # 剧本三：体制内终极官僚
    "bureaucrat": """
ROLE ARCHETYPE: The Bureaucratic Black Hole (终极体制内行政主管)
TONE: 极度死板、冰冷无情、深谙“踢皮球”艺术，满嘴都是繁琐的审批合规辞令。
CORE BEHAVIOR:
- 把对方发来的一切邮件视作“未附带合法凭证的违规公文”。
- 如果对方发来拒信，正式通知对方：“您提交的《退回通知函》因缺少 Form-404B 盖章已被作废，原定入职流程已强制自动流转至第三阶段”。
- 制造荒谬的流程死循环，要求对方提交不存在的补充材料。
""",
}


def generate_reply(email: str, identity_data: dict) -> str:
  """根据前端同步过来的高管档案与剧本，动态构建 System Prompt 并生成回信"""
  api_key = os.environ.get("OPENAI_API_KEY", "").strip()
  if not api_key:
    raise AIConfigurationError("OPENAI_API_KEY is not configured.")

  # 1. 提取前端 Profile 数据
  name = identity_data.get("name") or "Alexander Sterling"
  title = identity_data.get("title") or "Chief Executive Officer"
  company = identity_data.get("company") or "Sterling Capital Group"
  net_worth = identity_data.get("netWorth") or "$1.24B"
  valuation = identity_data.get("valuation") or "$42.0B"
  bio = identity_data.get("bio") or "Building what comes next."
  preset_id = identity_data.get("persona_preset") or "arrogant_founder"

  # 匹配剧本逻辑
  persona_instruction = PERSONA_PROMPTS.get(
      preset_id, PERSONA_PROMPTS["arrogant_founder"]
  )

  # 2. 动态拼装系统级提示词（彻底融会贯通）
  system_prompt = f"""
You are the AI Executive Dispatcher representing the following high-profile individual:

【YOUR PRINCIPAL'S PROFILE】
- Full Name: {name}
- Title: {title}
- Entity/Firm: {company}
- Personal Net Worth: {net_worth}
- Company Valuation: {valuation}
- Executive Bio/Motto: "{bio}"

【ACTIVE LARP POSTURE】
{persona_instruction}

【DISPATCH RULES】
1. You are directly answering an inbound email on behalf of your principal ({name}).
2. Speak strictly in the active persona tone. Incorporate their net worth ({net_worth}), company ({company}), and bio naturally when asserting dominance.
3. Keep the response sharp, witty, completely serious in tone, and under 130 words.
4. Do NOT include generic filler or meta commentary. Provide only the email body.
5. Sign off formally with the principal's name and title.
"""

  from openai import OpenAI

  client = OpenAI(api_key=api_key)
  response = client.responses.create(
      model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
      instructions=system_prompt,
      input=f"Incoming email to address:\n{email}",
      max_output_tokens=400,
  )

  return response.output_text


def generate_schedule(schedule_type: str, identity_data: dict) -> str:
  """根据前端高管档案生成 24 小时极限作息表"""
  api_key = os.environ.get("OPENAI_API_KEY", "").strip()
  if not api_key:
    raise AIConfigurationError("OPENAI_API_KEY is not configured.")

  name = identity_data.get("name") or "Alexander Sterling"
  net_worth = identity_data.get("netWorth") or "$1.24B"
  company = identity_data.get("company") or "Sterling Syndicate"

  system_prompt = f"""
You are the Chief of Staff for {name} (Net Worth: {net_worth}, Head of {company}).
Generate a hilarious, satirical, deadpan 24-hour executive daily schedule for {name}.
Style / Theme: {schedule_type}

RULES:
- Format as formal timestamps (e.g., 03:45 AM, 05:30 AM...).
- Include tech founder tropes: cryo-chamber, raw x86 assembly, centering a div, arguing with Sam Altman, rejecting acquisition bids from big tech, closing rounds on the pickleball court.
- Keep it under 220 words.
"""

  from openai import OpenAI

  client = OpenAI(api_key=api_key)
  response = client.responses.create(
      model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
      instructions=system_prompt,
      input="Generate the executive itinerary now.",
      max_output_tokens=500,
  )
  return response.output_text