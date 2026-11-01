# Task 4：Daily Executive Briefing 后端

## 已实现的流程

保存用户日程 → 读取最近 24 小时的真实邮件和用户当天日程 → OpenAI Responses API
生成结构化简报 → 保存预览和历史 → 在用户设定的本地时间通过 Agentboxd 投递。

简报包括商务摘要、重要邮件及建议行动、当天议程、待办、截止时间和明确的商务机会。
议程时间由后端直接从数据库渲染；AI 输出包含来源编号，未知来源会被拒绝。
没有日程、邮件或机会时明确返回空列表，不导入前端的虚构演示数据。

## 代码位置

- `briefing_models.py`：日程、设置、AI 输出的数据校验；时区和夏令时计算。
- `briefing_prompt.py`：Task 4 的完整 Prompt、Responses API 调用和来源校验。
- `briefing_service.py`：SQLite 存储、汇总、正文渲染、调度、发送状态和去重。
- `briefing_api.py`：登录鉴权后的前端接口。
- `agentboxd.py`：读取近 24 小时邮件、发送新邮件的 API 封装。
- `app.py`：启动/关闭调度器，兼容现有 `/api/account` 偏好保存。
- `tests/test_briefing.py`：隔离数据库和 API 替身测试，不发送真实邮件。

## 启动

在项目根目录执行：

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python backend/app.py
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe backend\app.py
```

已有后端进程需要先停止再启动，才能加载新代码和 `.env`。
通过原有 `http://localhost:3001` 前端代理调用 `/api`，沿用登录 Cookie。

配置在本地 `backend/.env`，不要提交密钥：

```dotenv
OPENAI_API_KEY=your_private_key
OPENAI_MODEL=your_existing_model
AGENTBOXD_API_KEY=your_private_key
AGENTBOXD_INBOX_ID=your_inbox_id
AGENTBOXD_ALLOWED_EMAIL=the_registered_inbox_owner_email
BRIEFING_SCHEDULER_ENABLED=true
BRIEFING_MODEL=
```

`BRIEFING_MODEL` 留空时沿用 `OPENAI_MODEL`。定时器默认启用，但只为数据库中明确保存了
`briefing: true` 的授权账户投递；没有保存设置的账号默认关闭。
项目目前只有一套共享邮箱凭证，因此只有 `AGENTBOXD_ALLOWED_EMAIL` 对应的注册账号能
读取真实邮箱、生成简报或投递；未来多用户邮箱接入需将凭证绑定至各自账号。
收件人固定为该登录账号邮箱，模型和请求内容都不能更改收件人。

`ENABLE_AUTO_REPLY` 是旧任务自动回复的独立开关，与每日简报无关。

## 接口约定

所有接口均需登录，使用已有的 HttpOnly Session Cookie。
前端请求示例：`fetch(path, { credentials: 'include', ...options })`。
错误响应沿用项目约定：`{ "error": "..." }`。

### 日程保存

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/calendar/events?day=2026-11-02` | 用户指定本地日期的日程；不传 day 默认今天 |
| POST | `/api/calendar/events` | 新增日程 |
| PUT | `/api/calendar/events/{id}` | 完整修改一条自己的日程 |
| DELETE | `/api/calendar/events/{id}` | 删除一条自己的日程，成功返回 204 |

POST / PUT 请求体：

```json
{
  "title": "Portfolio review",
  "startsAt": "2026-11-02T09:30:00-05:00",
  "endsAt": "2026-11-02T10:00:00-05:00",
  "location": "Boardroom",
  "notes": "Review the proposals received by email."
}
```

返回 `{ "event": { "id": "...", ... } }`；查询返回 `{ "events": [...] }`。
时间必须带 UTC 偏移或 `Z`，数据库统一存 UTC。前端本地日期时间输入可用
`new Date(value).toISOString()` 转换；展示时按用户选择的 IANA 时区格式化。
结束时间必须晚于开始时间；跨午夜事件会出现在两个相交日期中。
目前不支持重复事件、全天事件或外部 Google Calendar 同步。
前端现有 `src/data/briefing.js` 是演示数据，不会自动导入数据库。

### 定时设置

`GET /api/briefings/settings` 查看有效设置、收件人、调度开关、IANA 时区和下一次每日计划时间。

`PATCH /api/briefings/settings` 合并更新，可只提交部分字段：

```json
{
  "briefing": true,
  "delivery": "07:00 AM",
  "timezone": "Eastern Time (ET)",
  "briefingLanguage": "en"
}
```

- `briefing`：每日自动投递开关；测试预览无需打开。
- `delivery`：支持 `07:00 AM` 或 24 小时制 `07:00`。
- `timezone`：支持页面的五种显示名称，也支持 `America/Toronto` 等 IANA 时区。
- `briefingLanguage`：`en` 或 `zh`，默认 `en`。
- `nextRunAt` 是下一个未来每日计划时间；失败重试状态另查 delivery 接口。

现有前端保存偏好的 `PATCH /api/account` 仍然可用，会校验时间、时区和授权账号。
推荐新功能使用 `/api/briefings/settings`，该接口会保留其他偏好。

### 生成预览、读取与发送

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/briefings/generate` | 从真实来源生成并保存今天的预览；无请求体，不发送 |
| GET | `/api/briefings?limit=20` | 当前用户的历史，limit 为 1–100 |
| GET | `/api/briefings/{id}` | 当前用户的完整预览 |
| GET | `/api/briefings/delivery?day=2026-11-02` | 指定本地日期的发送状态 |
| POST | `/api/briefings/{id}/send` | 手动投递今天的预览，须提交 `{ "confirmed": true }` |

生成响应：

```json
{
  "briefing": {
    "id": "generated-uuid",
    "localDate": "2026-11-02",
    "timezone": "America/New_York",
    "subject": "Daily Executive Briefing — 2026-11-02",
    "content": {
      "summary": "A factual executive summary...",
      "priorityEmails": [
        { "emailId": "real-message-id", "summary": "...", "suggestedAction": "..." }
      ],
      "tasks": [{ "sourceId": "email:real-message-id", "detail": "..." }],
      "deadlines": [],
      "opportunities": []
    },
    "agenda": [],
    "coverage": {},
    "text": "Rendered email body...",
    "generatedAt": "2026-11-02T12:00:00+00:00"
  }
}
```

`agenda` 是真实保存事件的数组；`coverage` 包含邮件窗口、读取数量和截断信息。
最多查看 5 页、每页 100 封，最多纳入 40 封近 24 小时邮件，单封正文最多 2000 字符。
日程最多纳入 50 条，每条备注最多 500 字符。遗漏和截断会在数据和邮件正文中说明。
若邮件接口失败，不伪装为空收件箱生成简报；API 返回错误，定时任务记录失败。

手动发送响应的 `delivery.status: queued` 表示 Agentboxd 接受排队，**不是确认收件人已收到**。
`duplicatePrevented: true` 表示当天已有投递记录或任务正在处理，请查看返回的状态。
每天每个账号最多一次投递，手动投递也占用当天名额；允许多次生成预览。
改变时区或使用过去日期的预览时，需要重新生成今天的预览再发送。

### 前端接入清单

当前页面仍使用静态演示内容，本次只实现后端：

1. 日程编辑提交 `/api/calendar/events`；展示从 GET 接口读取，不从 mock 常量读取。
2. `Generate briefing` 调用 POST `/api/briefings/generate`。
3. 页面摘要显示 `briefing.content.summary`。
4. Agenda 显示 `briefing.agenda` 的开始/结束时间、标题和地点。
5. 待办和截止时间显示对应数组的 `detail`；机会同理。
6. 邮件预览可直接显示 `briefing.text`；来源字段可关联真实邮件/日程。
7. 时间、时区和开关保存至 `/api/briefings/settings`。
8. 如提供手动发送按钮，用户确认后调用 `/{id}/send`；按真实排队状态提示。

## 调度与运行边界

FastAPI 启动时启动后台线程，每 30 秒检查用户本地时间。后端必须持续运行，电脑休眠、
进程退出时无法定时执行；部署后可把后端作为常驻服务运行。

- 服务当天晚于设定时间启动，会补发当天一份；不追发过去多天。
- 夏令时春季不存在的时间顺延至第一个有效分钟；秋季重复时刻只使用第一次。
- SQLite 持久化用户/本地日期的唯一投递记录，同时使用 Agentboxd Idempotency-Key。
  多线程或进程竞争会通过事务领取任务，重复 tick 和重启不会重复发送当天简报。
- 生成失败在 5 分钟后重试，总计最多 3 次，次日重新开始。
- 生成进程中断后，10 分钟租约到期可恢复；发送中断或 API 回执丢失标记 `uncertain`，
  当天停止自动重试。应在 Agentboxd 后台核对，不能直接删除投递记录盲目重发。
- 凭证、邮件正文和原始提供方错误不会写入调度日志；来源数据隔离到登录账号。

## 验证

```bash
.venv/bin/python -m unittest discover -s backend/tests -v
```

测试使用临时 SQLite、模拟 AI 和模拟邮件请求，不写入实际账号日程，也不会发信。
实际验证过配置中的 Agentboxd 读取和 OpenAI 结构化简报生成；真实发送需由用户确认后测试。

## API 依据

- [OpenAI 官方文本生成文档](https://developers.openai.com/api/docs/guides/text?lang=python)
- [Agentboxd 官方 API 文档：新邮件发送、分页与幂等键](https://agentboxd.com/docs/api)
