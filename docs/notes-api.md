# 爪爪文字笔记与体验数据 API

基路径 `/api/zhuazhua/`；沿用私人知行档案登录 cookie 或爪爪 device bearer。浏览器写入必须显式 `Origin: https://qiuyiwu.com`，跨源拒绝；无 Origin 仅 bearer 可写。图片接口兼容，新增同源 cookie 上传支持用于图文笔记。

## 笔记

- `GET notes?q=&day=YYYY-MM-DD&offset=0&limit=24`：返回 `{items,more}`；limit 最大 60；日期按上海时区的采集日筛选。列表每项有 kind=note,id,title,excerpt,tags,collectedAt,modifiedAt,version。搜索当前使用参数化 SQL 对存储数据进行子串搜索，暂未采用全文索引。
- `GET notes/<UUID>`：完整对象含 markdown、sourceURL、attachments（digest列表）、attachmentImages（digest,imageURL,displayURL,width,height）。displayURL短时签名，不能存入 Markdown。
- `POST notes`：JSON `{id,title,markdown,tags,sourceURL,collectedAt,modifiedAt,attachments,version}`。ID由客户端生成UUID，时间包含时区；title最大512、markdown最大500000、tags最大4000、sourceURL最大2048字符；正文不可空白。请求最多2MiB。attachments最多100项且必须已存在于图片表。
- Markdown 持久图片地址 `/api/zhuazhua/image/<digest>`；服务器自动合并正文内该形式图片引用到附件集合。原图仍由现有 captures API 上传至私人 COS。笔记插图上传须传 `attachmentOnly:true`（严格布尔），已有digest时保留原图的备注、OCR、标签与采集时间；新图正常创建。外部Markdown图片的获取/显示策略由客户端渲染器控制，服务器不自动下载远程URL。
- 新笔记 version=0，编辑使用上次服务器版本。成功 `{ok:true,note:<完整对象>}`，版本递增。相同内容、相同旧请求版本的重试幂等，返回原成功版本。
- 冲突409 `{code:'version_conflict',error,current:<服务器笔记>}`；客户端必须保留草稿，不能自动覆盖。服务器保留首次 collectedAt；modifiedAt由客户端提供，顺序判断只依据version。
- 原始Markdown为数据正本，渲染不替代原文；当前无历史版本快照、删除/回收站、分享或多用户隔离。

## 可选体验数据

客户端须提供默认关闭的明确开关，仅启用后发送。`POST events` JSON严格限制以下字段，正文、标签、URL、查询、异常原文及任何未知字段均拒绝。

- event：search_completed、inbox_list_loaded、note_opened、note_saved、note_save_failed、image_upload_completed、note_editor_opened、note_imported、note_sync_completed、note_sync_failed。
- source：web / desktop；outcome：success / failure / cancelled。
- durationMs：0..600000整数，默认0；count：0..1000整数，默认0。
- errorCode：none（默认）/ network / validation / conflict / unauthorized / unknown。

请求最大4096字节，每服务进程全局每分钟最多120条（429）；只存UTC日聚合计数和耗时总和，不存原始事件、IP、用户标识、设备标识或会话。日聚合保留最近30个UTC自然日，每次事件写入或指标读取清理过期行；无定时作业时休眠服务不触发物理清理。基础设施访问日志不在此模块范围内。

`GET metrics?days=7`（或30）需认证，返回 `{days,items:[{day,event,source,outcome,errorCode,samples,durationMs,count}]}`。durationMs为总和，均值为总和/samples。不会自行提供内容分析或第三方传输。

## 验证

`PYTHONPATH=src python -m unittest discover -s tests -p 'test_notes.py'` 校验输入、CSRF、冲突响应。

`ZHUA_TEST_DATABASE='dbname=agentvault' PYTHONPATH=src python -m unittest discover -s tests -p 'test_notes_postgres.py'` 在随机独立schema内创建/删除测试数据，检查版本幂等、冲突、搜索、附件存在性、事件聚合；不接触真实图像表或COS。
