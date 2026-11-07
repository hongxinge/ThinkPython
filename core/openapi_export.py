"""OpenAPI 契约导出与质量体检

这个模块回答两个问题：

1. 我的接口契约长什么样？（导出 openapi.json，供 SDK 生成、Apifox/Postman 导入）
2. 我的契约够不够好？（体检出缺少 summary、响应类型不精确等会拖累客户端对接的地方）

设计原则：
- 不依赖 HTTP 端点。直接调用 ``app.openapi()``，因此生产环境即使关闭
  ``/openapi.json`` 也能导出，不会因为「要生成 SDK 就得放开 schema」而牺牲安全。
- 体检结论要能直接指导修改。每条问题都带方法、路径和修复建议，而不是只给一个分数。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# HTTP 方法在 OpenAPI 中的合法取值（排除已废弃的 trace）
_HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

# 体检问题级别
LEVEL_ERROR = "error"
LEVEL_WARN = "warn"
LEVEL_INFO = "info"


def build_schema(app: Any = None) -> Dict[str, Any]:
    """构建 OpenAPI schema

    Args:
        app: FastAPI 实例；为 None 时延迟导入 ``main.app``，避免 CLI 启动即加载全部业务模块

    Returns:
        Dict: OpenAPI 3.1 文档
    """
    if app is None:
        from main import app as default_app

        app = default_app

    # FastAPI 会缓存 openapi_schema，重复调用开销可忽略
    return app.openapi()


def export_schema(
    output: Path | str,
    app: Any = None,
    indent: int = 2,
) -> Tuple[Path, int]:
    """把 schema 导出为 JSON 文件

    Args:
        output: 输出文件路径，父目录不存在时自动创建
        app: FastAPI 实例
        indent: JSON 缩进，便于人工阅读与 diff

    Returns:
        Tuple[Path, int]: (实际写入路径, 字节数)
    """
    schema = build_schema(app)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(schema, ensure_ascii=False, indent=indent)
    path.write_text(content, encoding="utf-8")
    return path.resolve(), len(content.encode("utf-8"))


def _iter_operations(schema: Dict[str, Any]) -> Iterable[Tuple[str, str, Dict[str, Any]]]:
    """遍历所有操作，产出 (方法大写, 路径, 操作定义)"""
    for path, item in (schema.get("paths") or {}).items():
        for method in _HTTP_METHODS:
            operation = item.get(method)
            if isinstance(operation, dict):
                yield method.upper(), path, operation


def _is_loose_object(schema: Optional[Dict[str, Any]]) -> bool:
    """判断响应 schema 是否是「任意对象」

    ``response_model=dict`` 或完全未声明时，FastAPI 会生成
    ``{"type": "object", "additionalProperties": true}``，客户端拿不到字段信息。
    """
    if not schema:
        return True
    if "$ref" in schema:
        return False
    if schema.get("type") != "object":
        return False
    extra = schema.get("additionalProperties")
    props = schema.get("properties")
    return bool(extra) and not props


def _success_schema(operation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """取成功响应的 JSON schema（200 / 201 / 2XX）"""
    responses = operation.get("responses") or {}
    for code in ("200", "201", "202", "2XX"):
        if code in responses:
            content = (responses[code] or {}).get("content") or {}
            media = content.get("application/json") or {}
            return media.get("schema")
    return None


def inspect_schema(schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """对契约做质量体检

    检查项与影响：

    ==========================  ==============================================
    检查项                      对客户端的影响
    ==========================  ==============================================
    缺少 summary                生成的 SDK 方法没有注释，调用方靠猜
    响应类型为「任意对象」      生成的 TS 类型退化成 Record<string, any>，失去类型安全
    写操作缺少请求体 schema     客户端不知道要传什么字段
    缺少 tags                   SDK 无法按业务分组，接口一多就乱
    路径未带前缀                版本化困难，日后改版需要客户端全量改地址
    ==========================  ==============================================
    """
    if schema is None:
        schema = build_schema()

    issues: List[Dict[str, str]] = []
    operations = list(_iter_operations(schema))

    loose_responses: List[str] = []
    missing_summary: List[str] = []
    missing_tags: List[str] = []
    missing_body: List[str] = []
    unprefixed: List[str] = []

    for method, path, operation in operations:
        label = f"{method} {path}"

        if not (operation.get("summary") or "").strip():
            missing_summary.append(label)

        if not operation.get("tags"):
            missing_tags.append(label)

        if _is_loose_object(_success_schema(operation)):
            loose_responses.append(label)

        if method in ("POST", "PUT", "PATCH") and not operation.get("requestBody"):
            # 允许无请求体的动作型接口（如 logout / refresh 用 body，login 用 body）
            missing_body.append(label)

        segments = [s for s in path.split("/") if s]
        # 单段路径（如 /health）属于基础设施接口，不算问题
        if len(segments) <= 1:
            continue
        unprefixed.append(label)

    if loose_responses:
        issues.append(
            {
                "level": LEVEL_WARN,
                "code": "LOOSE_RESPONSE",
                "message": f"{len(loose_responses)} 个接口的成功响应是「任意对象」，客户端只能拿到 Record<string, any>",
                "fix": "给路由加 response_model=<Pydantic 模型>，或让统一响应包继承泛型模型",
                "samples": loose_responses[:8],
            }
        )
    if missing_summary:
        issues.append(
            {
                "level": LEVEL_WARN,
                "code": "MISSING_SUMMARY",
                "message": f"{len(missing_summary)} 个接口缺少 summary，生成的 SDK 方法没有注释",
                "fix": "在路由装饰器上补 summary=\"中文动作描述\"",
                "samples": missing_summary[:8],
            }
        )
    if missing_tags:
        issues.append(
            {
                "level": LEVEL_INFO,
                "code": "MISSING_TAGS",
                "message": f"{len(missing_tags)} 个接口没有 tags，SDK 无法按业务分组",
                "fix": "在控制器内统一加 tags=[\"业务名\"]",
                "samples": missing_tags[:8],
            }
        )
    if missing_body:
        issues.append(
            {
                "level": LEVEL_WARN,
                "code": "MISSING_BODY",
                "message": f"{len(missing_body)} 个写操作没有声明请求体",
                "fix": "为 POST/PUT/PATCH 声明 Pydantic 请求模型作为参数",
                "samples": missing_body[:8],
            }
        )

    schemas = (schema.get("components") or {}).get("schemas") or {}

    return {
        "total_operations": len(operations),
        "total_schemas": len(schemas),
        "schemas": sorted(schemas.keys()),
        "issues": issues,
        "counts": {
            "loose_response": len(loose_responses),
            "missing_summary": len(missing_summary),
            "missing_tags": len(missing_tags),
            "missing_body": len(missing_body),
            "unprefixed_path": len(unprefixed),
        },
    }


def format_report(report: Dict[str, Any], color: bool = True) -> str:
    """把体检结果格式化为可直接打印的文本"""
    bold = "\033[1m" if color else ""
    dim = "\033[2m" if color else ""
    yellow = "\033[33m" if color else ""
    cyan = "\033[36m" if color else ""
    reset = "\033[0m" if color else ""

    lines: List[str] = []
    lines.append(
        f"{bold}契约规模{reset}  接口 {report['total_operations']} 个 · "
        f"数据模型 {report['total_schemas']} 个"
    )

    counts = report["counts"]
    healthy = sum(
        counts[k]
        for k in ("loose_response", "missing_summary", "missing_tags", "missing_body")
    )
    if healthy == 0:
        lines.append(f"{cyan}✅ 契约质量良好，可以直接生成 SDK{reset}")
        return "\n".join(lines)

    lines.append("")
    lines.append(f"{bold}待改进{reset}")
    for issue in report["issues"]:
        mark = "⚠️ " if issue["level"] == LEVEL_WARN else "ℹ️ "
        lines.append(f"  {yellow}{mark}{issue['message']}{reset}")
        lines.append(f"     {dim}修复：{issue['fix']}{reset}")
        for sample in issue["samples"]:
            lines.append(f"     {dim}  · {sample}{reset}")
        if len(issue["samples"]) >= 8:
            lines.append(f"     {dim}  …{reset}")

    return "\n".join(lines)
