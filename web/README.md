# 前端 (web)

Vue 3 + Vite + Naive UI + Tailwind CSS。

## 本地开发

```bash
cd web

# 1. 安装依赖
pnpm install

# 2. 配置后端地址
cp .env.example .env
# VITE_SERVICE_BASE_URL=http://localhost:8000

# 3. 启动开发服务器
pnpm dev
```

Vite 自动将 `/api/v1/*` 代理到后端（`VITE_SERVICE_BASE_URL`），不需要 nginx。

## 生产构建

```bash
pnpm build-only    # 输出到 dist/
```

产物通过 nginx 部署，nginx 配置见 `../docker/cuda/volumes/nginx/nginx.conf`。

## 开发工具

```bash
pnpm lint          # ESLint + Oxlint
pnpm format        # Prettier
pnpm type-check    # TypeScript 类型检查
pnpm test:unit     # Vitest 单元测试
```

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
pnpm install
```

### Compile and Hot-Reload for Development

```sh
pnpm dev
```

### Type-Check, Compile and Minify for Production

```sh
pnpm build
```

### Run Unit Tests with [Vitest](https://vitest.dev/)

```sh
pnpm test:unit
```

### Lint with [ESLint](https://eslint.org/)

```sh
pnpm lint
```
