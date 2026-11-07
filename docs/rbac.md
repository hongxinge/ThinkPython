# 权限控制（RBAC）

接口级权限，用于区分「普通用户」与「管理员 / 运营」等角色能访问哪些接口。

> 客户端视角的 403 / 1010 说明见 [客户端 API 契约](api-contract.md)。

---

## 1. 模型

```
用户 ──(持有)──> 角色 ──(声明)──> 权限集合
```

- **用户**：`user.role` 字段存角色名，默认 `user`；
- **角色**：字符串标识，如 `admin`、`user`、`operator`；
- **权限**：`资源:动作` 形式，如 `order:read`、`user:write`。

角色到权限的映射写在代码里（`config/permissions.py`），不占用数据表：

```python
ROLE_PERMISSIONS = {
    "admin": {"*"},                                  # 全部权限
    "user": {"profile:read", "profile:write"},       # 只能读写自己资料
    "operator": {"order:read", "order:*"},           # 订单全部动作
}
```

支持两种通配：

| 写法 | 含义 |
|---|---|
| `*` | 拥有全部权限（超级管理员） |
| `order:*` | order 资源下的所有动作 |

---

## 2. 给接口加权限

```python
from helpers.auth import require_permission

class OrderController(BaseController):
    def __init__(self):
        super().__init__()
        self._setup_routes()

    def _setup_routes(self):
        @self.router.get("/orders", summary="订单列表")
        @require_permission("order:read")
        async def list_orders():
            ...

        @self.router.delete("/orders/{order_id}", summary="删除订单")
        @require_permission("order:delete", mode="all")
        async def delete_order(order_id: int):
            ...
```

要点：

1. `@require_permission` 必须写在路由装饰器**内层**（与 `@skip_auth` 相同的写法）；
2. `mode="any"`（默认）：满足任一权限即可；`mode="all"`：必须全部满足；
3. 未声明权限的接口只要求「已登录」，不做权限判断——这是默认行为，向后兼容；
4. 权限校验在认证之后执行：未登录返回 401（1001 等），已登录但无权限返回 403（1010）。

---

## 3. 角色的权威来源与失效

角色写入 Token 的 `role` 字段，校验时直接读 Token，**不查库**（零额外开销）。
代价是：**改角色后旧 Token 仍带旧角色**，直到过期。

因此修改角色时必须让旧 Token 失效：

```python
from core.token_state import bump_token_version

user.role = "admin"
await bump_token_version(db, user.id)   # 该用户所有已签发 Token 立即失效
await db.flush()
```

用户会收到 401 / 1005（已吊销），重新登录后拿到新角色的 Token。

> 想让角色变更"立刻生效但不踢人"，可把角色改为从数据库读取（复用
> `core/token_state.py` 的缓存思路）。代价是每次请求多一次查询或缓存读，
> 属于性能与实时性的取舍，按业务需要决定。

---

## 4. 校验当前用户权限（业务代码内）

```python
from config.permissions import has_permission

if not has_permission(current_user.payload.get("role"), "order:delete"):
    raise ForbiddenException("无权删除该订单")
```

或者用 `has_any_permission` / `has_all_permissions` 处理多权限场景。

---

## 5. 与「数据级权限」的分界

RBAC 只回答「这个角色能不能调用这个接口」，**不回答**「能不能操作这一条数据」。

例如「用户只能看自己的订单」属于数据级权限，应在 Service 层用资源归属判断：

```python
order = await service.get_by_id(order_id)
if order.user_id != current_user.user_id:
    raise ForbiddenException("无权访问该订单")
```

不要把这类判断塞进权限表——权限会随数据量爆炸，维护成本极高。

---

## 6. 常见问题

**Q：需要更细的角色（如「财务只能看报表」）怎么办？**
直接往 `ROLE_PERMISSIONS` 里加一条即可，无需改表、无需迁移。

**Q：一个用户能有多个角色吗？**
当前是单角色设计（`user.role` 存一个字符串）。多角色需要改成关联表，
属于框架扩展范围；多数 To C 与中小后台单角色已够用。

**Q：改了权限映射要不要重启？**
`ROLE_PERMISSIONS` 在模块导入时求值，属于代码配置，修改后需重启进程。

**Q：如何给新注册用户默认角色？**
由 `user.role` 的默认值决定（`server_default="user"`），也可用环境变量
`DEFAULT_ROLE` 覆盖默认值。
