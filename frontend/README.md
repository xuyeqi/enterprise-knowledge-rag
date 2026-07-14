# Frontend

企业知识库 RAG 项目的 Vue3 前端。当前阶段提供企业后台式应用骨架，并通过
Vite 开发代理请求 FastAPI `/health`，验证最小前后端连接。

## Requirements

- Node.js `20.19+` 或 `22.12+`
- npm
- 本地 FastAPI 运行在 `http://127.0.0.1:8000`

## Install

在 `frontend` 目录执行：

```powershell
npm install
```

该命令会安装 Vue、Vue Router、Pinia、Element Plus、Vite 和 TypeScript，
同时生成应提交到 Git 的 `package-lock.json`。

## Verify

执行类型检查和生产构建：

```powershell
npm run build
```

构建成功后，产物会写入已被 `.gitignore` 排除的 `dist/`。

## Run

先在 `backend` 目录启动 FastAPI，再在 `frontend` 目录执行：

```powershell
npm run dev
```

打开：

```text
http://127.0.0.1:5173
```

页面会请求 `/api/health`。Vite 将它转发为后端的 `/health`；状态卡显示
“FastAPI 服务连接正常”即表示浏览器、Vite 代理和后端三段链路已经连通。

## Troubleshooting

### Vite 显示已启动，但页面无法访问

本机曾出现 Vite 只监听 IPv6 环回地址 `::1`，而浏览器无法通过该地址连接，
导致访问 `localhost:5173` 时返回 `ERR_CONNECTION_REFUSED`。这不代表网卡没有开启
IPv6，而是本机 IPv6 环回连接存在异常。

停止 Vite 后，改为明确监听 IPv4：

```powershell
.\node_modules\.bin\vite.cmd --host=127.0.0.1 --port=5173 --strictPort
```

终端显示 `http://127.0.0.1:5173/` 后，使用该地址访问页面。
