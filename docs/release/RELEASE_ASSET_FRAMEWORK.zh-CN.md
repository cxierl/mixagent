# 发布资源框架（中文）

## 目标

为 MixAgent 建立一个稳定、可持续、可自动更新的桌面版发布结构。

## GitHub 仓库建议结构

```text
mixagent/
  electron/
  docs/
    release/
      RELEASE_ASSET_FRAMEWORK.zh-CN.md
      RELEASE_ASSET_FRAMEWORK.en.md
      v0.1.2.zh-CN.md
      v0.1.2.en.md
  index.html
  package.json
  package-lock.json
  README.md
  CHANGELOG.md
  ISSUE_LOG.md
```

## GitHub Release 资产分类

每个版本推荐发布这三类资产：

### 1. 安装资产

- `MixAgent Setup x.y.z.exe`

用途：

- 给最终用户双击安装
- NSIS 一键安装

### 2. 增量更新资产

- `MixAgent Setup x.y.z.exe.blockmap`

用途：

- 给桌面端自动更新做差分下载
- 降低更新时的下载体积

### 3. 更新元数据

- `latest.yml`

用途：

- 告诉桌面应用“最新版本是什么”
- 告诉应用应该下载哪些文件

## 发布说明

每个版本建议同时准备：

- 中文发布说明
- 英文发布说明

建议命名：

- `docs/release/v0.1.2.zh-CN.md`
- `docs/release/v0.1.2.en.md`

## 推荐发布流程

1. 更新版本号
2. 运行打包
3. 检查生成物
4. 提交代码
5. 打 tag
6. 推送到 GitHub
7. 创建 GitHub Release
8. 上传 `.exe`、`.blockmap`、`latest.yml`
9. 粘贴中英文发布说明

## 自动更新工作前提

只有满足以下条件，自动更新才会真正可用：

1. 版本号大于已安装版本
2. 发布资产上传到正确的 GitHub Release
3. `latest.yml` 与安装包版本一致
4. 仓库的 `owner/repo` 配置正确

## 当前版本

当前桌面发布版本为 `v0.1.2`。
