"""独立自动回复守护脚本：基准同步模式（零文件依赖，启动即忽略历史邮件）"""

import os
from pathlib import Path
import time
from dotenv import load_dotenv

# 显式加载 backend/.env 环境变量
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from agentboxd import get_emails, reply_to_email
from ai_service import generate_reply

# 测试高管身份人设
DEFAULT_IDENTITY = """
Name: Alexander Sterling
Title: Managing Partner & Chief Architect
Company: Sterling Capital Group
Net Worth: $1.24B
Bio: My time is denominated in millions per second. Rejections are formally overruled.
"""

CURRENT_MODE = "unicorn_gatekeeper"


def run_auto_reply_loop():
  print("=" * 60)
  print("🚀 Agentboxd 自动回复监听器启动中...")
  print(f"🎭 当前回复姿态: [{CURRENT_MODE}]")
  print("=" * 60)

  # 纯内存存储已处理的邮件 ID（不产生任何本地文件）
  processed_ids = set()

  # 1. 基准同步（Baseline Sync）：启动时记录所有存量邮件
  print("🔍 正在扫描现有收件箱，同步基准状态...")
  try:
    initial_emails = get_emails()
    for mail in initial_emails:
      msg_id = mail.get("id")
      if msg_id:
        processed_ids.add(msg_id)
    print(
        f"✅ 基准同步完毕！已自动跳过现存的 {len(processed_ids)} 封历史旧邮件。"
    )
    print("👂 监听已就绪，当前只等待【未来刚刚发进来的新邮件】...\n")
  except Exception as e:
    print(f"⚠️ 基准扫描失败（请检查网络或凭证）: {e}\n")

  # 2. 正式轮询循环：只处理未来到达的新邮件
  while True:
    try:
      emails = get_emails()

      for mail in emails:
        msg_id = mail.get("id")

        # 只要没有 ID，或者属于历史基准邮件，直接跳过
        if not msg_id or msg_id in processed_ids:
          continue

        # 立即记录该新邮件 ID，防止下次循环重复回复
        processed_ids.add(msg_id)

        sender_name = mail.get("name")
        sender_email = mail.get("email")
        subject = mail.get("subject", "(无主题)")
        body = mail.get("body", "")

        print(
            f"\n📩 [🔥 捕捉到现场新邮件] 来自: {sender_name} <{sender_email}>"
        )
        print(f"   主题: {subject}")
        print(f"   正文: {body[:100]}...")

        # 调用 AI 生成傲慢反击
        print("🤖 [AI 正在组织措辞生成回怼内容...]")
        reply_content = generate_reply(
            email=f"Subject: {subject}\n\n{body}",
            identity=DEFAULT_IDENTITY,
            mode=CURRENT_MODE,
        )

        print("\n📝 [生成的回信]:")
        print("-" * 30)
        print(reply_content)
        print("-" * 30)

        # 通过 Agentboxd 发送回信
        print("📤 正在通过 Agentboxd 回执...")
        reply_to_email(msg_id, reply_content)
        print(f"✅ 成功回复邮件给 {sender_email}！")

    except Exception as err:
      print(f"⚠️ 轮询处理时发生异常: {err}")

    # 每 4 秒拉取一次
    time.sleep(4)


if __name__ == "__main__":
  run_auto_reply_loop()