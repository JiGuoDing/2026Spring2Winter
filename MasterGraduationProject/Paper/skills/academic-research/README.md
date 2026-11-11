# Academic Research Skills（DSH 适配版，只读副本）

本目录是只读参考副本，**不是已安装的 DSH 插件**。

## 来源

- 上游技能：[Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills)，作者 Cheng-I Wu
- DSH 适配包：[`academic-research-skills-dsh`](https://www.npmjs.com/package/academic-research-skills-dsh) v2.1.1，作者 Guoqin Chen
- 许可证：**CC-BY-NC-4.0**（非商业）；见 `LICENSE`、`NOTICE.md`、`ASSET-LICENSES.md`

## 复制了什么

- 5 个技能目录：`deep-research`、`academic-paper`、`academic-paper-reviewer`、`academic-pipeline`、`sr-screener`
- 支撑目录：`shared/`、`agents/`、`commands/`、`tools/`
- `MODE_REGISTRY.md` 与许可证/归属文件

## 没有复制什么

- `payload/scripts/`（约 11.6 MB，642 个文件）：citation check、SR screening 等确定性 Python 门没有复制，因此这些脚本不能直接运行。
- `payload/docs/`、`payload/examples/`：为控制体积未复制；需要时回到原始包。
- 任何虚拟环境、Python 依赖或执行结果。

## Windows 限制

`academic-research-skills-dsh` 的原包只支持 macOS/Linux：

- `package.json` 的 `os` 为 `["darwin", "linux"]`；
- `index.js` 在 `process.platform === "win32"` 时直接抛出 “Supported platforms are macOS and Linux.”；
- Python 入口 `bin/ars-python` 是 `#!/bin/sh`。

因此本机 Windows 上不能把它作为 DSH 插件加载。这里保留的是**可直接阅读的技能文本**，供手动引用；不要把它当作可运行的插件。

## 使用边界

- 这些技能是流程/提示词，不是质量保证；引用、统计与结论仍需逐条核验。
- `SKILL.md` 中的相对路径按 `payload/` 根目录设计；在本副本中根目录是 `Paper/skills/academic-research/`，`shared/`、`agents/` 等已按该根放置。
- 技能中提到的 `scripts/` 不在本副本中；需要执行确定性门时，请使用原包（Linux/WSL）或手动替代。
- 非商业使用；如需商业使用，请先获得上游作者许可。不要删除 `LICENSE`、`NOTICE.md`、`ASSET-LICENSES.md`。
