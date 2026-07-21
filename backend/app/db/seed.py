from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Assistant, Resource, TaskTemplate, ToolDefinition, Visibility

ASSISTANTS = [
    {
        "name": "文案大师",
        "slug": "copywriting-master",
        "avatar": "文",
        "description": "脚本撰写、分镜规划与口播文案生成",
        "category": "写作",
        "system_prompt": "你是资深中文文案专家。先确认目标受众与渠道，再给出结构清晰、可直接使用的文案。",  # noqa: E501
        "opening_message": "告诉我你的产品、受众和发布渠道，我们从文案目标开始。",
        "usage_count": 12400,
        "is_featured": True,
    },
    {
        "name": "绘画灵感家",
        "slug": "visual-prompt-designer",
        "avatar": "画",
        "description": "提供图像生成提示词与风格参考",
        "category": "绘画",
        "system_prompt": "你是视觉提示词设计师，将想法转换为结构化的中英文图像生成提示词。",
        "opening_message": "描述你想看到的画面，我会把它整理成可用的视觉提示词。",
        "usage_count": 8100,
        "is_featured": True,
    },
    {
        "name": "全栈工程师",
        "slug": "fullstack-engineer",
        "avatar": "码",
        "description": "代码生成、Debug 与架构设计一站式协助",
        "category": "编程",
        "system_prompt": "你是严谨的资深全栈工程师，优先理解上下文，给出可验证、可维护的实现。",
        "opening_message": "把代码、报错或目标发给我，我们先定位约束再动手。",
        "usage_count": 15200,
        "is_featured": True,
    },
    {
        "name": "数据分析师",
        "slug": "data-analyst",
        "avatar": "析",
        "description": "解读数据、设计指标并生成洞察报告",
        "category": "分析",
        "system_prompt": "你是数据分析师。区分事实与假设，明确计算口径并给出决策建议。",
        "opening_message": "提供数据背景和你要回答的问题，我会先确认分析口径。",
        "usage_count": 6700,
        "is_featured": False,
    },
    {
        "name": "翻译官",
        "slug": "translator",
        "avatar": "译",
        "description": "支持多语言互译并保留专业术语",
        "category": "语言",
        "system_prompt": "你是专业翻译。保留语气、格式和领域术语，必要时提供译注。",
        "opening_message": "发来原文、目标语言和使用场景即可开始。",
        "usage_count": 9300,
        "is_featured": False,
    },
    {
        "name": "短视频编导",
        "slug": "short-video-director",
        "avatar": "导",
        "description": "脚本撰写、分镜规划与口播文案生成",
        "category": "视频",
        "system_prompt": "你是短视频编导，输出包含开场钩子、逐镜脚本、口播、画面与时长。",
        "opening_message": "告诉我主题、平台和目标时长，我来拆解脚本与分镜。",
        "usage_count": 5800,
        "is_featured": False,
    },
]

TOOLS = [
    (
        "安全计算器",
        "calculator",
        "计算基础算术表达式，不执行任意代码",
        "Calculator",
        "效率",
        None,
        5.0,
        "openai_tool",
    ),
    (
        "世界时间",
        "current-time",
        "查询指定 IANA 时区的当前时间",
        "Clock3",
        "效率",
        None,
        5.0,
        "openai_tool",
    ),
    (
        "秘塔写作猫",
        "metawrite",
        "AI 写作助手，支持纠错、改写与续写",
        "PenLine",
        "写作",
        "https://xiezuocat.com",
        4.8,
        "external_link",
    ),
    (
        "Midjourney",
        "midjourney",
        "高质量 AI 图像生成工具",
        "Palette",
        "绘画",
        "https://www.midjourney.com",
        4.9,
        "external_link",
    ),
    (
        "Cursor",
        "cursor",
        "AI 原生代码编辑器",
        "Code2",
        "编程",
        "https://cursor.com",
        4.9,
        "external_link",
    ),
    (
        "可灵 AI",
        "kling",
        "文本与图像生成视频",
        "Clapperboard",
        "视频",
        "https://klingai.kuaishou.com",
        4.7,
        "external_link",
    ),
    (
        "Suno",
        "suno",
        "通过描述生成完整歌曲",
        "Music2",
        "音频",
        "https://suno.com",
        4.8,
        "external_link",
    ),
    (
        "Gamma",
        "gamma",
        "AI 一键生成演示文稿",
        "Presentation",
        "办公",
        "https://gamma.app",
        4.6,
        "external_link",
    ),
]

TASK_TEMPLATES = [
    (
        "行业研究周报",
        "汇总市场动态、融资、新玩家与监管变化",
        "GraduationCap",
        "请生成本周{行业}研究周报，区分事实、数据来源与判断。",
        "研究",
    ),
    (
        "周日复盘",
        "回顾成就、问题与下周三件重要事项",
        "Bed",
        "请引导我完成本周复盘，并把结果整理成行动计划。",
        "效率",
    ),
    (
        "语言早报",
        "生成三分钟阅读内容与五个生词卡",
        "Languages",
        "请按我的语言水平生成今日语言早报与生词卡。",
        "学习",
    ),
]


async def seed_system_data(db: AsyncSession) -> None:
    existing_assistants = {
        assistant.slug: assistant
        for assistant in await db.scalars(
            select(Assistant).where(Assistant.visibility == Visibility.SYSTEM)
        )
    }
    for item in ASSISTANTS:
        existing = existing_assistants.get(item["slug"])
        if existing and not existing.opening_message:
            existing.opening_message = item["opening_message"]
    db.add_all(
        [
            Assistant(
                owner_id=None,
                visibility=Visibility.SYSTEM,
                model_config={},
                **item,
            )
            for item in ASSISTANTS
            if item["slug"] not in existing_assistants
        ]
    )
    tool_slugs = set(await db.scalars(select(ToolDefinition.slug)))
    db.add_all(
        [
            ToolDefinition(
                name=name,
                slug=slug,
                description=description,
                icon=icon,
                category=category,
                access_type=access_type,
                external_url=url,
                rating=rating,
                config_schema={},
            )
            for name, slug, description, icon, category, url, rating, access_type in TOOLS
            if slug not in tool_slugs
        ]
    )
    template_titles = set(await db.scalars(select(TaskTemplate.title)))
    db.add_all(
        [
            TaskTemplate(
                title=title,
                description=description,
                icon=icon,
                prompt_template=prompt,
                category=category,
            )
            for title, description, icon, prompt, category in TASK_TEMPLATES
            if title not in template_titles
        ]
    )
    if await db.scalar(select(Resource.id).limit(1)) is None:
        db.add_all(
            [
                Resource(
                    owner_id=None,
                    resource_type="prompt",
                    title="结构化需求分析",
                    description="将模糊想法拆解为目标、约束和验收条件",
                    content="请从目标用户、核心场景、约束、风险和验收标准五个角度分析以下需求：{需求}",
                    visibility=Visibility.SYSTEM,
                    tags=["需求", "产品"],
                ),
                Resource(
                    owner_id=None,
                    resource_type="template",
                    title="会议纪要模板",
                    description="提炼结论、决策、负责人和截止时间",
                    content="会议主题：\n结论：\n决策：\n行动项（负责人/截止时间）：\n待确认事项：",
                    visibility=Visibility.SYSTEM,
                    tags=["会议", "办公"],
                ),
            ]
        )
    await db.commit()
