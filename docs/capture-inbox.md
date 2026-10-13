# 爪爪收件箱

桌面爪爪把原图以 Base64 JSON 提交到 `POST /api/zhuazhua/captures`。服务校验 SHA-256、图片格式、体积、时间字段；原始字节进入私有 COS `zhuazhua/raw/`，缩略图进入 `zhuazhua/thumbnails/`，PostgreSQL `zhuazhua_captures` 保存元数据。仅 COS 写入与校验成功后提交数据库事务。相同 SHA-256 使用事务锁和主键去重，重试不新增记录。

`GET /vault/inbox/` 使用原网站登录；`GET /api/zhuazhua/captures` 搜索与分页，图片和缩略图路由同样鉴权。网页不接收设备 token，不把私有图片加入公开 catalog。设备 Bearer 仅在新采集命名空间生效，不获得管理站权限。

服务器环境变量：`CAPTURE_COS_REGION`、`CAPTURE_COS_BUCKET`、`CAPTURE_COS_SECRET_ID`、`CAPTURE_COS_SECRET_KEY`、`CAPTURE_DEVICE_SHA256`。值只由部署环境提供；禁止放入仓库。依赖 Pillow、psycopg2、cos-python-sdk-v5（本次运行版本 1.9.44）。Nginx 新采集路由请求上限 90 MB，服务原图上限 64 MB / 6000 万像素。支持 PNG/JPEG/GIF/WebP/TIFF；不支持 HEIC/PDF/视频。

当前是单人私人收件箱：复用现有个人站点身份，不作为多租户权限系统。中文 OCR 在 Mac 端用 Vision 完成；服务搜索使用数据库子串查询，未实现语义检索或视觉相似去重。图片只有字节完全相同才合并。网站提供预览、下载、OCR 复制、名称/标签/备注/OCR 搜索和采集日期过滤；整理编辑在桌面进行。

部署时以线上 production.py/channel.py 为基础应用入口改动，不能用本地旧文件覆盖线上其他模块。新增 routes 接入 `captures.handle`，启动调用 `captures.init`，channel 导航增加收件箱。入口图片读取仍代理 COS；大原图打开速度受服务器出口影响，列表使用约 640px 的缩略图。

运行 `PYTHONPATH=src python3 -m unittest discover -s tests -p test_captures.py` 验证字段、图片校验与设备鉴权。部署后需验证真实 COS 回读 SHA、重复 POST 单条记录、匿名 401 / COS 403，以及已登录网页实际显示。
