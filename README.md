# Claude 专用出口与国内分流模板

这是从个人 Clash Verge 配置中提取的**脱敏模板**，不是能直接连接的节点订阅。真实节点、用户名、密码、UUID、订阅链接、控制器密钥和个人路径均未包含。

## 路由设计

- Rule 模式 + TUN。
- Claude 指定域名：`Japan-Upstream → Dedicated-ISP → 目标`。
- 普通海外流量：`Proxy → Japan-Upstream`。
- 国内常用网站、局域网和共享地址空间按规则直连。
- 专用 SOCKS5 仅配置 TCP，因此指定 Claude 域名、入站 IP 网段和进程的 UDP 先拒绝，避免回落到普通代理或直连。
- Claude DNS 策略绑定 Claude-ISP；国内 DNS 使用直连 DoH。
- `127.0.0.1:17898` 是固定走 Claude-ISP 的 HTTP 代理端口，可供 Claude Code 使用。

## 文件

- `clash.example.yaml`：完整示例，所有节点参数都是占位符。
- `clash-verge-script.js`：订阅扩展脚本，集中生成域名规则、UDP 拒绝规则和 DNS 策略。
- `claude-rules.list`：域名规则；没有代理策略名称，也不包含 DNS 和 UDP 设置。
- `verify.py`：本地静态检查，不连接节点、不更改系统网络。

## 使用

1. 将示例复制为 `clash.local.yaml`，只在本地填写真实节点信息。前置示例使用 VLESS Reality；如果节点采用其他协议，请替换完整的前置节点段。
2. 保留节点名 `Japan-Upstream` 和 `Dedicated-ISP`，或同步修改脚本。专用 ISP 采用 SOCKS5 用户名密码认证；端口 443 不代表启用了 TLS。
3. 在 Clash Verge 中导入本地配置，保持 Rule 模式。也可以把脚本作为订阅扩展，但原配置必须已经存在两个节点以及 `Proxy`、`Claude-ISP` 组。
4. 该脚本会重建 `rules`、相关 DNS 策略和专用监听器。先备份并检查与你的其他分流是否冲突；不要无检查地叠加到其他订阅。
5. Claude Code 可在本地环境或用户 settings.json 的 env 中设置 `HTTP_PROXY`、`HTTPS_PROXY` 为 `http://127.0.0.1:17898`。这个设置不会自动覆盖工具启动的每一个子进程。
6. 本地验证：`python3 verify.py`，需要 Python PyYAML 和 Node.js。填写节点后，再用本机 Mihomo 的 `-t -f clash.local.yaml` 检查。

## Chrome WebRTC 隐私设置（macOS，可选）

网页的 WebRTC/STUN 请求可能访问不属于 Claude 的服务器，因此 Claude 域名规则不能保证这些请求使用专用出口。检测页显示另一个代理出口，只能说明出口不一致，不能单凭这一点认定真实公网 IP 已泄露。

Chrome 可通过 `WebRtcIPHandling = disable_non_proxied_udp` 限制 WebRTC 使用非代理 UDP。这是浏览器设置，导入本仓库的 Clash 配置不会自动启用，也不会改变国内 DIRECT 规则。它不等于彻底禁用 WebRTC，且可能影响网页通话的连通性或质量。

以下方法适用于个人 Mac 的本机验证；`defaults` 写入的是当前 macOS 用户的 **Recommended** 策略，不是强制策略。用户偏好、扩展或受管策略可能覆盖它，企业部署应使用正式的策略管理方式。参见 [Chromium macOS 策略说明](https://www.chromium.org/administrators/mac-quick-start/) 和 [Chrome WebRtcIPHandling 策略](https://chromeenterprise.google/policies/#WebRtcIPHandling)。

先读取并自行记录原值；提示键不存在时，也要记下“原先未设置”。只读取这个键，避免导出整个浏览器偏好：

```sh
defaults read com.google.Chrome WebRtcIPHandling
```

确认未与已有管理策略冲突后，设置：

```sh
defaults write com.google.Chrome WebRtcIPHandling -string disable_non_proxied_udp
```

在 `chrome://policy` 点击 **Reload policies**；若未生效，保存浏览器中的工作后完全退出并重新打开 Chrome。确认该键的值正确、状态为 **OK**，并查看实际策略级别。随后保持平时的 TUN、代理和分流设置，重新加载 WebRTC 检测页，等待检测完成，确认不再返回不期望的公网候选地址；同时测试常用网站及需要的网页音视频通话。对实际使用的每个 Chrome 个人资料分别验证。

撤销时，若原先未设置该键：

```sh
defaults delete com.google.Chrome WebRtcIPHandling
```

若原先已有值，应使用 `defaults write com.google.Chrome WebRtcIPHandling -string '原先记录的值'` 恢复，不能直接删除。撤销后同样重新加载策略或重启，并复测。

检测页的“WebRTC 已禁用或无泄露”仅说明该次探针未得到可展示的地址；不证明所有流量都经过专用出口，也不验证 DNS、断网或休眠唤醒保护。此设置不覆盖 Safari、其他应用或 Claude Code；普通代理与专用代理的出口不同，可以是分流设计的正常结果。

## 边界

- 不包含原电脑两个业务服务器的直连例外，迁移到原环境时要从本地配置保留。
- 进程规则面向 macOS；浏览器依靠域名规则，其他系统需调整进程路径。
- 第三方 CDN、可选遥测仅匹配脚本列出的精确域名；不使用整个平台域名或关键词兜底。同一遥测接收地址也可能供其他应用使用，这些请求会一起分流；不宣称覆盖 Claude 的所有外部资源。
- IP 兜底采用官方入站网段，不把 Anthropic 对外请求的源地址范围当作客户端必需目的地；IPv6 规则不代表节点具备 IPv6 连通能力。
- 仅对列出的 Claude UDP 目标拒绝，不是全局 WebRTC 防泄漏方案。
- TUN、IPv6 设置和分流规则不能等同于断网或休眠唤醒时的系统级 kill switch。
- 代理出口、IP 检测分数不能保证服务账号可用或改变服务地区资格。
- 模板不包含控制 API 监听端口和密钥；按需仅在本地配置。
- 不要上传 `*.local.*`、原始订阅、备份或日志；`.gitignore` 不能代替内容审查。

## 来源

- [Anthropic 官方入站与出站 IP 说明](https://platform.claude.com/docs/en/api/ip-addresses)
- [Claude 官方网络文档](https://code.claude.com/docs/en/network-config)
- [v2fly Anthropic 域名集](https://github.com/v2fly/domain-list-community/blob/master/data/anthropic)
- [Mihomo 规则文档](https://wiki.metacubex.one/config/rules/)

这份模板未整体导入第三方分流配置。真实电脑的验证结果不能代替其他设备填写参数后的验证。
