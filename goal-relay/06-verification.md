# 06 — 验证链设计

三层验证，逐层递进，任何一层出问题都能拦住。

## 第一层：自动验证（Agent 自测）

每个 Goal 内部，Agent 在完成代码后、写 handoff 前，执行验证步骤。验证结果写入 handoff Section 6。

| Goal 类型 | 典型验证命令 |
|----------|------------|
| 写代码 | `cargo check` / `npx tsc --noEmit` / `go build` |
| 创建文件 | `ls -la 目标目录/*.rs \| wc -l` 确认文件数量 |
| 删代码 | `grep -rn '旧函数名' src/` 确认无残留 |

## 第二层：交接验证（下游 Agent 复核）

Goal N+1 的 Agent 启动后第一步就是读 Goal N 的 handoff 文件 Section 6。如果发现验证没通过：

1. 先修问题
2. 再继续自己的任务
3. 如果问题太大修不了，在 handoff Section 4 中标注，并告知人

## 第三层：人工验证（人最终检查）

你在每个 Goal 结束后做两件事：

```bash
# 1. 看改动范围对不对
git diff --stat HEAD

# 2. 确认没有越界修改
# Goal 1 只应该碰 app/src-tauri/src/collectors/ 和 scanner/
# 不应该碰 app/src/（前端）或 contracts/
```

Goal 3（最后一个）完成后，额外做：

```bash
# 编译
cargo build         # Rust
npx tsc --noEmit    # TypeScript

# 检查旧代码已删除
grep -rn '旧模块名' src/   # 应该无匹配

# 如果能跑，启动 app 手动测试
```

## 验证失败怎么办

| 在哪层发现 | 怎么处理 |
|-----------|---------|
| 第一层（Agent 自测） | Agent 在 Goal 内修，修完再写 handoff |
| 第二层（下游复核） | 下游 Agent 修，handoff Section 4 标注 |
| 第三层（人检查） | 在当前 Goal 的对话中告诉 Agent 修，修完才 commit |
