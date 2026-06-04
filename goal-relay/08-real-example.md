# 08 — 真实案例

## AgentSense 扫描引擎 Rust 迁移

- **项目**：AgentSense（Tauri 2 + React/TypeScript + Python sidecar）
- **任务**：将扫描层（agent 检测 + skill/MCP 采集）从 Python 迁到 Rust，移除 Python 依赖
- **规模**：删 ~3,700 行 Python + Rust glue，增 ~3,100 行纯 Rust，跨 30+ 个文件
- **ADR**：`decisions/0008-rust-native-scan-engine.md`

### 拆解方案

| Goal | 内容 | 文件数 | 代码量 |
|------|------|-------|--------|
| Goal 1 | 骨架 + 5 个 Tier 1 collector | ~12 新建 | ~1,500 行 |
| Goal 2 | 8 个 Tier 2 collector + 扫描主逻辑 | ~15 新建 | ~1,400 行 |
| Goal 3 | 接 Tauri + 删 Python + 全量验证 | ~5 改 + ~6 删 | ~300 行 |

### 完整 Master Plan

见 `ai/docs/rust-native-scan-three-goals.md`（包含三个 Goal 的完整可粘贴提示词）。

### 关键决策

- **为什么拆成 3 个而不是 4 个**：Goal 1 和 2 各自有足够的同质性（都是写 collector），再拆就太碎了
- **为什么 Goal 3 代码量少但重要**：接入现有系统 + 删旧代码是最容易出问题的环节，值得独立对话
- **为什么不把推荐引擎也一起迁**：推荐算法仍在快速迭代，现在迁会导致频繁重编译。等稳定后再做
