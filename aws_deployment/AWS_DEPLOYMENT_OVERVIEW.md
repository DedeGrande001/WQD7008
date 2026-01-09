# 🚀 AWS 部署总览

欢迎！这个文件夹包含了将推荐系统部署到 AWS 的所有资源。

---

## 📁 文件说明

| 文件名 | 用途 | 何时使用 |
|--------|------|---------|
| **README.md** | 完整部署指南（详细版） | 需要了解每个步骤的详细说明时 |
| **QUICKSTART.md** | 快速开始指南（精简版） | 想要快速上手，一步步跟着做 |
| **REPORT_TEMPLATE.md** | 技术报告模板 | 编写作业报告时 |
| **spark_emr.py** | EMR Spark 处理脚本 | EMR 集群上运行的主程序 |
| **ec2_setup.sh** | EC2 自动化安装脚本 | 在 EC2 上初始化环境 |
| **bootstrap.sh** | EMR 引导脚本 | EMR 启动时自动执行 |
| **submit_emr_job.sh** | EMR 作业提交脚本 | 提交 Spark 任务到 EMR |
| **.env.aws** | AWS 环境变量模板 | 配置数据库连接等信息 |
| **requirements_ec2.txt** | EC2 Python 依赖 | EC2 上安装 Python 包 |
| **AWS_DEPLOYMENT_OVERVIEW.md** | 本文件 | 了解文件夹结构 |

---

## 🎯 我应该从哪里开始？

### 情况 1：第一次部署，需要详细指导
👉 **阅读顺序**：
1. 先看 `QUICKSTART.md`（快速上手）
2. 遇到问题时参考 `README.md`（详细说明）
3. 按步骤执行脚本

### 情况 2：有经验，想快速部署
👉 **执行步骤**：
1. 创建 S3 bucket，上传数据
2. 创建 RDS MySQL 实例
3. 启动 EC2，运行 `ec2_setup.sh`
4. 创建 EMR 集群（使用 `bootstrap.sh`）
5. 运行 `submit_emr_job.sh`

### 情况 3：部署完成，要写报告
👉 **使用模板**：
1. 打开 `REPORT_TEMPLATE.md`
2. 填写实际数据和截图
3. 按模板结构编写报告

---

## 📊 部署架构一览

```
┌─────────────────────────────────────────────────┐
│                  用户浏览器                       │
└─────────────┬───────────────────────────────────┘
              │ HTTP/HTTPS
              ↓
┌─────────────────────────────────────────────────┐
│  EC2 Instance (Web Server)                      │
│  ┌─────────────────────────────────────┐        │
│  │  Django Application (Port 8000)     │        │
│  │  - 用户认证                          │        │
│  │  - 推荐展示                          │        │
│  │  - 数据管理                          │        │
│  └─────────────────────────────────────┘        │
└─────────────┬───────────────────────────────────┘
              │ MySQL Queries
              ↓
┌─────────────────────────────────────────────────┐
│  RDS MySQL (Database)                           │
│  - app_movie (电影信息)                         │
│  - app_recommendationdata (推荐结果)            │
└─────────────┬───────────────────────────────────┘
              ↑ JDBC Write
              │
┌─────────────────────────────────────────────────┐
│  EMR Cluster (Spark Processing)                 │
│  ┌──────────────────┐  ┌──────────────────┐    │
│  │  Master Node     │  │  Core Node 1     │    │
│  │  (Resource Mgr)  │  │  (Executor)      │    │
│  └──────────────────┘  └──────────────────┘    │
│                        ┌──────────────────┐    │
│                        │  Core Node 2     │    │
│                        │  (Executor)      │    │
│                        └──────────────────┘    │
└─────────────┬───────────────────────────────────┘
              ↑ Read CSV
              │
┌─────────────────────────────────────────────────┐
│  S3 Bucket (Data Lake)                          │
│  - input/movies.csv                             │
│  - input/ratings.csv                            │
│  - scripts/spark_emr.py                         │
│  - scripts/bootstrap.sh                         │
└─────────────────────────────────────────────────┘
```

---

## ⏱️ 时间估算

| 步骤 | 时间 | 难度 |
|------|------|------|
| 1. 准备数据（下载 MovieLens） | 15 分钟 | ⭐ |
| 2. 创建 S3 bucket 并上传 | 10 分钟 | ⭐ |
| 3. 创建 RDS 数据库 | 20 分钟 | ⭐⭐ |
| 4. 启动和配置 EC2 | 30 分钟 | ⭐⭐⭐ |
| 5. 创建 EMR 集群 | 20 分钟 | ⭐⭐ |
| 6. 运行 Spark 作业 | 15 分钟 | ⭐⭐ |
| 7. 验证和测试 | 15 分钟 | ⭐ |
| **总计** | **~2-3 小时** | |

---

## 💰 成本估算

**测试期间（1周）预计成本**：

| 服务 | 配置 | 成本/天 | 7天成本 |
|------|------|---------|---------|
| S3 | 1GB 存储 + 请求 | $0.03 | $0.21 |
| RDS | db.t3.micro (持续运行) | $0.41 | $2.86 |
| EC2 | t2.small (持续运行) | $0.55 | $3.86 |
| EMR | m5.xlarge × 3 (3小时) | - | $1.73 |
| 数据传输 | ~2GB | - | $0.18 |
| **总计** | | | **~$8.84** |

✅ **远低于 $50 预算！**

---

## 🔧 快速命令参考

### AWS CLI 常用命令

```bash
# 配置 AWS CLI
aws configure

# S3 操作
aws s3 ls                                    # 列出所有 bucket
aws s3 mb s3://bucket-name                   # 创建 bucket
aws s3 cp file.csv s3://bucket-name/path/    # 上传文件
aws s3 ls s3://bucket-name/                  # 列出文件

# EC2 操作
aws ec2 describe-instances                   # 列出实例
aws ec2 start-instances --instance-ids i-xxx # 启动实例
aws ec2 stop-instances --instance-ids i-xxx  # 停止实例

# EMR 操作
aws emr list-clusters                        # 列出集群
aws emr describe-cluster --cluster-id j-xxx  # 查看详情
aws emr terminate-clusters --cluster-ids j-xxx # 终止集群

# RDS 操作
aws rds describe-db-instances                # 列出数据库
```

### SSH 连接

```bash
# 设置密钥权限
chmod 400 key.pem

# 连接 EC2
ssh -i key.pem ubuntu@<EC2-Public-IP>

# 连接 EMR Master
ssh -i key.pem hadoop@<EMR-Master-Public-DNS>
```

### 文件传输

```bash
# 上传文件到 EC2
scp -i key.pem file.txt ubuntu@<EC2-IP>:/home/ubuntu/

# 上传整个文件夹
scp -i key.pem -r folder/ ubuntu@<EC2-IP>:/home/ubuntu/

# 从 EC2 下载文件
scp -i key.pem ubuntu@<EC2-IP>:/path/file.txt ./
```

---

## 📸 需要的截图清单（至少15张）

### AWS 控制台截图
- [ ] 1. S3 bucket 内容列表
- [ ] 2. RDS 实例详情页面（显示 endpoint）
- [ ] 3. RDS 安全组配置（3306 端口开放）
- [ ] 4. EC2 实例列表（显示运行状态）
- [ ] 5. EC2 安全组配置
- [ ] 6. EMR 集群概览（显示 Waiting 状态）
- [ ] 7. EMR 集群配置详情
- [ ] 8. EMR Steps 列表（显示 Completed）

### 应用截图
- [ ] 9. Django 登录页面
- [ ] 10. Django 仪表盘（显示统计数据）
- [ ] 11. 推荐结果页面（显示电影列表）
- [ ] 12. 推荐结果按类型筛选

### 监控截图
- [ ] 13. CloudWatch EMR CPU 使用率
- [ ] 14. CloudWatch EC2 网络流量
- [ ] 15. Spark UI 任务执行图（可选）
- [ ] 16. Billing Dashboard 成本统计

### 技术截图
- [ ] 17. SSH 连接 EC2 终端
- [ ] 18. MySQL 查询结果（显示数据）
- [ ] 19. EMR 日志输出

---

## ⚠️ 常见错误和解决方案

### 错误 1: EC2 无法连接
```
ssh: connect to host x.x.x.x port 22: Connection timed out
```
**解决方案**: 检查安全组是否开放 22 端口

### 错误 2: RDS 连接拒绝
```
ERROR 2003 (HY000): Can't connect to MySQL server
```
**解决方案**:
1. 检查 RDS 安全组 3306 端口
2. 确认 RDS 公开访问已启用

### 错误 3: EMR Step 失败
```
Step failed with status: FAILED
```
**解决方案**:
1. 查看 EMR 日志（Controller logs）
2. 检查 S3 路径是否正确
3. 验证 RDS 连接信息

### 错误 4: Spark OOM
```
java.lang.OutOfMemoryError: Java heap space
```
**解决方案**: 增加 executor memory
```python
.config("spark.executor.memory", "6g")
```

---

## 🎓 学习资源

### AWS 官方文档
- EMR 文档: https://docs.aws.amazon.com/emr/
- RDS 文档: https://docs.aws.amazon.com/rds/
- S3 文档: https://docs.aws.amazon.com/s3/

### Spark 文档
- Spark SQL: https://spark.apache.org/docs/latest/sql-programming-guide.html
- Spark Configuration: https://spark.apache.org/docs/latest/configuration.html

### 视频教程
- AWS EMR 入门: https://www.youtube.com/watch?v=...
- Spark 基础: https://www.youtube.com/watch?v=...

---

## ✅ 检查清单（提交前）

### 技术实现
- [ ] S3 bucket 已创建并上传数据
- [ ] RDS 数据库正常运行
- [ ] EC2 Django 应用可访问
- [ ] EMR Spark 作业成功执行
- [ ] Web 界面显示推荐结果

### 文档准备
- [ ] 收集所有截图（至少 15 张）
- [ ] 完成技术报告（基于模板）
- [ ] 准备演示 PPT
- [ ] 准备源代码压缩包

### 成本控制
- [ ] EMR 集群已终止
- [ ] EC2 实例已停止（可选）
- [ ] 检查 Billing Dashboard
- [ ] 确认总成本 < $50

### 演示准备
- [ ] 练习演示流程（10分钟）
- [ ] 准备 Q&A 答案
- [ ] 所有组员了解系统架构

---

## 🆘 获取帮助

遇到问题？按以下顺序尝试：

1. **查看文档**：先看 `README.md` 的常见问题部分
2. **检查日志**：
   - EC2: `tail -f django.log`
   - EMR: 控制台 Steps -> View logs
3. **AWS Support**：在 AWS Console 右上角点击 "Support"
4. **社区**：Stack Overflow, AWS Forums

---

## 📝 下一步

1. ✅ 阅读 `QUICKSTART.md` 快速开始
2. ⬜ 按步骤部署到 AWS
3. ⬜ 收集截图和数据
4. ⬜ 编写技术报告
5. ⬜ 准备演示
6. ⬜ 清理资源

---

**祝你部署顺利！如有问题，参考上面的文档。** 🚀

**预计总耗时**：2-3 小时（首次部署）
**预计成本**：$5-10（远低于预算）
**难度等级**：⭐⭐⭐☆☆（中等）
