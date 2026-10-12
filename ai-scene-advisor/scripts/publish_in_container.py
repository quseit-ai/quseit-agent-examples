"""以创作者身份发布「AI 场景顾问」示例智能体（给平台运营用的脚本）。

普通创作者请按示例 README 在 QUSEIT 后台操作，不需要这个脚本；它依赖平台后端的内部函数，
只能在能 import 后端 `app` 包、并能连上平台数据库的环境里运行（例如后端服务运行的环境）。

用法（先把整个示例目录 ai-scene-advisor/ 放到该环境里，再在后端工作目录下运行）：

    python publish_in_container.py --email creator@example.com
    python publish_in_container.py --email creator@example.com --slug ai-advisor --fallback-slug ai-scene-advisor

参数：
    --email          必填。创作者账号邮箱，脚本按邮箱查出用户，再以该用户身份发布。
    --slug           可选。页面地址 /s/<slug>；缺省取 agent.json 里的 slug。
    --fallback-slug  可选。--slug 已被占用时改用它；不给则在 slug 被占用时直接报错退出。

前提：
    1. 该创作者账号已经配置了 agent.json 里 default_provider 对应供应商的模型凭据；
    2. 账号点数余额 > 0。

读取的文件（均在本脚本的上一级目录）：skill/（技能目录，整个打成 zip）、agent.json（页面与运行配置）、
record_schema.json（记录表定义）。

依次调用的平台函数：
    skills.upload_skill            上传技能包（把 skill/ 打成 zip）
    agents.publish_from_skills     由技能创建智能体（标题 / slug / 引擎 / 模型 / 收费 / 联网 / 温度）
    agents.update_page             补开场白、引导问题、输入框提示语、默认供应商、记录表
    agents.republish               「更新版本」，让上面的草稿改动生效

重复运行会再次上传技能；slug 被占用时按 --fallback-slug 另建一个智能体。
要更新已有智能体，请在后台改完后点「更新版本」，不要重跑本脚本。
"""
import argparse
import asyncio
import io
import json
import sys
import zipfile
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent.parent
SKILL_DIR = EXAMPLE_DIR / "skill"
# zip 内的顶层目录名，对应技能 SKILL.md 里的 name
SKILL_ZIP_ROOT = "ai-scene-advisor"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="发布「AI 场景顾问」示例智能体（需在后端运行环境内执行）")
    p.add_argument("--email", required=True, help="创作者账号邮箱")
    p.add_argument("--slug", default=None, help="页面 slug，缺省取 agent.json 里的 slug")
    p.add_argument("--fallback-slug", default=None, help="--slug 被占用时改用的 slug；不给则报错退出")
    return p.parse_args()


def load_json(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text(encoding="utf-8"))


def build_skill_zip() -> bytes:
    """把 skill/ 目录下的所有文件打成 zip，顶层目录为 SKILL_ZIP_ROOT。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SKILL_DIR.rglob("*")):
            if path.is_file() and path.name != ".DS_Store":
                zf.write(path, f"{SKILL_ZIP_ROOT}/{path.relative_to(SKILL_DIR).as_posix()}")
    return buf.getvalue()


async def main(args: argparse.Namespace) -> None:
    # 这些 import 依赖后端的 app 包，放在函数内以便本机也能 py_compile / --help
    import app.main  # noqa: F401  (tenancy guard)
    from sqlalchemy import select

    from app.core.db import get_sessionmaker
    from app.core.tenancy import read_bypass, user_context
    from app.domains.accounts.models import User
    from app.domains.agents import service as agents
    from app.domains.agents.models import AgentBundle, ServicePage
    from app.domains.agents.schemas import PublishFromSkillsRequest, ServicePageUpdate, StarterQuestion
    from app.domains.records.schemas import RecordSchema
    from app.domains.skills import service as skills

    cfg = load_json("agent.json")
    schema = RecordSchema.model_validate(load_json("record_schema.json"))  # 先校验，避免半途失败
    wanted_slug = args.slug or cfg["slug"]

    sm = get_sessionmaker()
    async with sm() as s:
        with read_bypass():
            me = (await s.execute(select(User).where(User.email == args.email))).scalar_one()
            taken = (await s.execute(select(ServicePage.id).where(ServicePage.slug == wanted_slug))).first()
    if taken:
        if not args.fallback_slug:
            sys.exit(f"slug 已被占用：{wanted_slug}（可用 --fallback-slug 指定备用 slug）")
        slug = args.fallback_slug
    else:
        slug = wanted_slug

    with user_context(me.id):
        async with sm() as s:
            sk = await skills.upload_skill(s, user_id=me.id, username=me.username, zip_bytes=build_skill_zip(),
                                           filename=f"{SKILL_ZIP_ROOT}.zip", category=None)
            await s.commit()
            print("skill", sk.id, sk.slug, sk.version, sk.name)
            skill_id = sk.id
        async with sm() as s:
            page = await agents.publish_from_skills(s, user_id=me.id, body=PublishFromSkillsRequest(
                skill_ids=[skill_id], title=cfg["title"], slug=slug,
                description=cfg["description"],
                is_service_page_enabled=cfg["is_service_page_enabled"], is_api_enabled=cfg["is_api_enabled"],
                model=cfg["model"], temperature=cfg["temperature"],
                engine=cfg["engine"], web_search_enabled=cfg["web_search_enabled"],
                pricing_mode=cfg["pricing_mode"], free_rounds=cfg["free_rounds"]))
            page_id = page.id
            print("published", page_id, page.slug)
        async with sm() as s:
            page = await agents.get_owned_page(s, page_id)
            await agents.update_page(s, page, ServicePageUpdate(
                greeting=cfg["greeting"],
                input_placeholder=cfg["input_placeholder"],
                starter_questions=[StarterQuestion(label=q["label"], prompt=q["prompt"])
                                   for q in cfg["starter_questions"]],
                default_provider=cfg["default_provider"],
                record_schema=schema,
            ))
            page = await agents.republish(s, page)
            print("republished status", page.status, "engine", page.engine, "model", page.model,
                  "dp", page.default_provider)
        async with sm() as s:
            for b in (await s.execute(select(AgentBundle).where(AgentBundle.service_page_id == page_id)
                                      .order_by(AgentBundle.version))).scalars():
                rs = (b.manifest or {}).get("record_schema")
                print("bundle", b.id, "v", b.version, b.status, "manifest_record_fields",
                      len(rs["fields"]) if rs else 0)


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
