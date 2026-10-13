# 爪爪收件箱

桌面爪爪把原图以 Base64 JSON 提交到 `POST /api/zhuazhua/captures`。服务校验 SHA-256、图片格式、体积、时间字段；原始字节进入私有 COS `zhuazhua/raw/`，缩略图进入 `zhuazhua/thumbnails/`，PostgreSQL `zhuazhua_captures` 保存元数据。仅 COS 写入与校验成功后提交数据库事务。相同 SHA-256 使用事务锁和主键去重，重试不新增记录。

`GET /vault/inbox/` 使用原网站登录；`GET /api/zhuazhua/captures` 搜索与分页，图片和缩略图路由同样鉴权。网页不接收设备 token，不把私有图片加入公开 catalog。设备 Bearer 仅在新采集命名空间生效，不获得管理站权限。

服务器环境变量：`CAPTURE_COS_REGION`、`CAPTURE_COS_BUCKET`、`CAPTURE_COS_SECRET_ID`、`CAPTURE_COS_SECRET_KEY`、`CAPTURE_DEVICE_SHA256`。值只由部署环境提供；禁止放入仓库。依赖 Pillow、psycopg2、cos-python-sdk-v5（本次运行版本 1.9.44）。Nginx 新采集路由请求上限 90 MB，服务原图上限 64 MB / 6000 万像素。支持 PNG/JPEG/GIF/WebP/TIFF；不支持 HEIC/PDF/视频。

当前是单人私人收件箱：复用现有个人站点身份，不作为多租户权限系统。中文 OCR 在 Mac 端用 Vision 完成；服务搜索使用数据库子串查询，未实现语义检索或视觉相似去重。图片只有字节完全相同才合并。网站提供预览、下载、OCR 复制、名称/标签/备注/OCR 搜索和采集日期过滤；整理编辑在桌面进行。

部署时以线上 production.py/channel.py 为基础应用入口改动，不能用本地旧文件覆盖线上其他模块。新增 routes 接入 `captures.handle`，启动调用 `captures.init`，channel 导航增加收件箱。入口图片读取仍代理 COS；大原图打开速度受服务器出口影响，列表使用约 640px 的缩略图。

运行 `PYTHONPATH=src python3 -m unittest discover -s tests -p test_captures.py` 验证字段、图片校验与设备鉴权。部署后需验证真实 COS 回读 SHA、重复 POST 单条记录、匿名 401 / COS 403，以及已登录网页实际显示。

## 2026-10-13 图片瀑布流加载优化

首页卡片只含图片，名称仍作为无障碍标签；标题、采集时间、备注和 OCR 进入点击详情。以原始宽高预计算最短列位置，加载图片不改变卡片高度；窗口尺寸变化时重新布局。列表每批 24 条，接近底部自动续载，保留手动加载按钮。搜索取消前次请求，并通过 generation 丢弃过期结果。

`GET captures?summary=1&limit=24` 只选择名称等列表字段，不回传 OCR 正文；`GET captures/<digest>` 按需获取完整元数据和原图展示 URL。旧列表响应与图片代理接口兼容保留。列表缩略图与详情原图通过 COS 900 秒签名地址直读，签名每 300 秒复用，响应 private max-age=600；过期/失败的卡片提供点击重试，经原鉴权代理恢复。地址是短时访问能力，不应分享或写入公开日志。COS ACL 保持私有，列表与详情仍要求现有登录或设备认证。

验证：7 项后端单元测试、JavaScript 语法、真实分页顺序与匿名 401 通过。Chrome 实际图片墙确认无可见标题/时间。一次 17 条记录测量：旧完整响应 37143 B / 1005 ms，轻量响应 13074 B / 120 ms；同一缩略图 COS 270 ms、代理 1200 ms；原图 COS 510 ms。此为单次当前网络观察，不作为稳定延迟保证。
