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

# 3. 运营后台（浏览器）
cd ../admin && npm install && npm run dev     # http://localhost:5174/
```

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
