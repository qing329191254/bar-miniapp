# 玩咖桌游酒吧

C 端 + 员工端是 **uni-app 微信小程序**（`bar-miniprogram/`）。运营后台是 Web（`admin/`）。后端 FastAPI + MySQL + Redis。

账本、订单、会员、卡券落 **MySQL**。Redis 只做登录会话、待付充值/待确认提分锁、核销码 TTL、店员确认幂等。

## 启动

```bash
# 1. MySQL 8.4 + Redis（宿主机 MySQL 映射 3308）
docker compose up -d

# 2. 后端（必须 0.0.0.0，微信开发者工具才能打到本机）
cd server
python -m pip install -r requirements.txt
python seed_db.py
python -m uvicorn main:app --host 0.0.0.0 --port 8010 --reload

# 3. 运营后台（浏览器，本地页面默认连接云托管接口和云端数据）
cd ../admin && npm install && npm run dev     # http://localhost:5174/
```

本地后台通过 `admin/.env` 的 `VITE_API_PROXY_TARGET` 连接云托管服务，因此无需启动本机后端即可使用云端接口、数据库和云存储。此模式下保存、删除、发布等操作会直接修改线上数据。如需使用本机后端与本地数据库，将该配置改为 `http://127.0.0.1:8010` 后重启 Vite。

小程序：用 **HBuilderX** 打开 `bar-miniprogram/`，运行 → 微信开发者工具。

微信开发者工具里关掉「不校验合法域名」。接口默认 `http://127.0.0.1:8010`（8000 被本机其它项目占用），改真机调试时把 `bar-miniprogram/utils/api.js` 里的 `BASE` 换成电脑局域网 IP。

小程序 AppID 已写入 `manifest.json`：`wx5c0ae1aa67a69d6e`。

重置演示数据：`POST http://127.0.0.1:8010/api/dev/reset`

## 演示账号

| 端 | 用户 | id |
|---|---|---|
| C 端 | 阿俊 | 1 |
| 店员 | 小美 | 51 |
| 店长 | 小李 | 52 |
| 老板 | 张老板 | 53 |

登录后 C 端走首页/点单/卡券，员工进待办。后台请用店长或老板。

## 图片上传（微信云存储 · 客户端直传）

后台「店铺相册 / 商品图」等上传已改为 **浏览器直传微信云存储**，不再走后端 `/api/admin/upload`。

首次使用前，在微信云托管 / 云开发控制台完成：

1. **对象存储** → 存储权限：**公有读**（相册图 C 端可直接访问）
2. **登录授权** → 开启 **匿名登录**（后台 Web 上传前会自动匿名登录云开发）
3. **存储安全规则** 建议允许已登录用户写入，例如：
   ```json
   {
     "*": {
       "read": true,
       "write": "auth != null"
     }
   }
   ```
4. 小程序 **downloadFile 合法域名** 添加：
   `7072-prod-d2gc6jcwy846bd613-1476141553.cos.ap-shanghai.myqcloud.com`

本地后台配置见 `admin/.env.example`（复制为 `admin/.env`）。上传后图片 URL 形如：
`https://7072-prod-...cos.ap-shanghai.myqcloud.com/wanka/uploads/xxx.jpg`
