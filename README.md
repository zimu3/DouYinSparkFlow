# DouYin Spark Flow

## 当前 fork 的网页私信测试模式

本仓库的 main 分支使用普通抖音网页（`www.douyin.com`）私信路径。GitHub Actions 的 `schedule.yml` 设有北京时间每天 15:17 的单目标发送试运行；手动触发默认 `smoke` 不发送，明确选择 `send` 才会手动发送。运行串行且单个目标不自动重试。**目前这仍是试验功能，尚未证明能稳定送达，不可依赖其自动续火花。**

在 `user-data` Environment 中配置 `TASKS`。推荐使用已核实主页的直达格式：`[{"username":"<发送账号昵称>","unique_id":"<发送账号抖音号>","targets":[{"unique_id":"<目标抖音号>","profile_url":"https://www.douyin.com/user/<目标主页标识>"}]}]`。运行时会在主页再次核对目标抖音号。

MATCH_MODE 建议为 short_id。登录 Cookie 放在 COOKIES_32120635840 Secret，必须能登录 www.douyin.com；创作者中心专用 Cookie 不一定适用。不要将 Cookie 或令牌提交到仓库。

GitHub 运行器能识别发送账号和打开目标页面，但这不等于私信已登录。[测试 #16](https://github.com/zimu3/DouYinSparkFlow/actions/runs/35318963907) 在发送方页面出现临时消息气泡后，重新打开私信触发登录面板；两端均未看到该测试消息。代码现会在发送前重开会话预检，并在发送后重开核验。其他旧的定时工作流保持禁用。

只有 `PERSISTED_SENDER_SIDE` 才表示重新打开发送方会话后仍能看到消息，仍需接收方 APP 核对。Actions 绿色状态或临时气泡都不代表送达；一旦出现登录要求或结果不确定，程序会失败且不自动重试，以免重复发送。不要在仓库、Issue 或日志中公开 Cookie、二维码或登录令牌。


![cover](docs/images/cover.png)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Playwright](https://img.shields.io/badge/Playwright-%E2%9C%94-green?logo=playwright)
![chrome-headless-shell](https://img.shields.io/badge/chrome--headless--shell-%E2%9C%94-brightgreen?logo=googlechrome)

> `dev`分支迁移到`https://www.douyin.com/chat` 加载更稳定，支持通过备注/昵称/抖音号等多种方式智能匹配。由于`https://www.douyin.com/chat`没经过长期测试，该分支目前暂不合并。有能力的可以研究一下

## 贡献者

感谢所有为本项目做出贡献的开发者：

[![contributors](https://contrib.rocks/image?repo=2061360308/DouYinSparkFlow)](https://github.com/2061360308/DouYinSparkFlow/graphs/contributors)

## 📌 项目介绍

**抖音火花自动续火脚本**一款轻量实用的抖音互动脚本，可自动为你和抖音好友续火花，无需手动操作。

✅ 支持 GitHub Actions 自动运行（开箱即用的 Workflow 配置）

✅ 也可源码部署至自有服务器，青龙/白虎等任务管理面板，灵活适配个人使用场景

### 特性/优势

- [x] 在线可视化配置工具，新手也能入门操作
- [x] Fork即用，无需克隆代码，配置运行环境
- [x] 多用户,同时批量支持多个账户
- [x] 多目标,一个账户支持多个续火花目标
- [x] 支持按照昵称和抖音号两种方式查找好友目标
- [x] 一言支持,更丰富的消息文本

使用`PlayWright`以及`chrome-headless-shell`自动化操作[抖音创作者中心](https://creator.douyin.com/)，进行定时发送抖音消息来续火花

## 🚀 使用方法

**材料准备：** 一个 GitHub 账号和可用浏览器即可，不设额外门槛。

**编辑项目配置：** 保姆级教程见 [配置生成器使用](docs/配置生成器使用.md)

**部署方法：**

1. Github Action 部署（推荐👍），操作说明见 [Action部署说明](docs/Action部署说明.md)

2. 源码部署 （更适合高级用户），操作说明见[源代码部署说明](docs/源代码部署说明.md)

## 📢交流讨论

已开放讨论区，有疑问或展示相关成果，发布话题需求的可以加入讨论

[跳转讨论区](https://github.com/2061360308/DouYinSparkFlow/discussions)

## ⭐Star 趋势

## Star History

[![Star History Chart](https://api.star-history.com/chart?repos=2061360308/DouYinSparkFlow&type=date&legend=top-left&sealed_token=TlokSbTx6LsGFZNndYzOzoSQ4ReFseZ4kWxbS4BP0V3WAsAsnXUUVxQPdyEOEWUpHtpTS7hlIpAJMa7C7KbbEp4QtLwyahXr41t2liypNktp0Z3Nh_V2eIBQzSyxWMiFxedN_xifd4Np_MxyHSHs6BrSe672ge7ovFimoLv-yucCt-TV_6opPkp9qltR)](https://www.star-history.com/?repos=2061360308%2FDouYinSparkFlow&type=date&legend=top-left)

## ⚠️ 免责声明

1. 本项目为**开源学习用途**，仅用于技术研究和个人自用，严禁用于商业用途、恶意刷量或违反抖音平台规则的行为。
2. 使用本脚本产生的一切风险（包括但不限于抖音账号限流、封禁、处罚等）均由使用者自行承担，项目开发者不承担任何责任。
3. 本项目仅调用公开的接口/模拟人工操作，不涉及破解、入侵抖音系统，使用者需遵守《抖音用户服务协议》及相关法律法规。
4. 请合理控制脚本运行频率，避免给抖音平台服务器造成压力，建议仅用于个人少量好友的火花维系。
5. 若你使用本项目即表示已阅读并同意本免责声明，如不同意请立即停止使用。

## 📄 开源协议

本项目基于 MIT 协议开源，你可以自由使用、修改和分发本项目代码，详见 [LICENSE](LICENSE) 文件。
