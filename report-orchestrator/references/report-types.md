# 报告类型识别规则

先依据真实目录证据做判断，再决定采用哪份模板。若用户显式指定报告类型，则用户优先。

## `java_experiment`

优先命中线索：

- `pom.xml`、`build.gradle`、`gradlew`
- `src/main/java`、`src/test/java`
- `application.yml`、`application.yaml`、`application.properties`
- `Spring Boot`、`MyBatis`、`Servlet`、`JSP`、`JavaFX` 相关配置或依赖
- `.java` 文件为主体，且存在控制层、服务层、实体层等分层痕迹

适用输出：

- Java 课程设计实验报告
- Java 系统分析报告
- 面向对象课程设计报告

## `python_experiment`

优先命中线索：

- `.py` 文件为主体
- `requirements.txt`、`pyproject.toml`、`Pipfile`
- `tkinter`、`PyQt`、`Flask`、`Django`、`FastAPI`、`requests`、`threading`、`asyncio`
- 存在 GUI、文件处理、网络请求、多线程、数据库访问等综合性迹象

适用输出：

- Python 课程设计实验报告
- Python 综合开发实验报告

## `database_design`

优先命中线索：

- `.sql` 文件、数据库脚本目录、DDL/DML 文件
- `.mdf`、`.ldf`、数据库备份文件
- 实体、关系、ER 图、表结构、规范化等术语或文档
- 项目核心内容是数据库概念设计、逻辑设计、物理设计，而非完整应用开发

适用输出：

- 数据库课程设计报告
- SQL Server 数据库设计报告

## `linux_project`

优先命中线索：

- Shell 脚本、Linux 命令操作记录、服务部署脚本
- Docker、systemd、Nginx、SSH、用户权限、文件系统、进程管理相关内容
- 报告重心是 Linux 环境搭建、系统管理、服务部署、运维操作

适用输出：

- Linux 操作系统项目报告
- Linux 课程实验报告

## `project_management`

优先命中线索：

- 招标、合同、WBS、进度计划、成本计划、风险计划、质量计划
- 项目章程、需求规格、验收计划、配置管理计划
- 重心是项目治理，而不是代码实现

适用输出：

- 软件项目管理报告
- 项目执行与控制类文档

## `generic_report`

当目录中信号混杂、证据不完整，或者无法明确归入上述类型时，使用通用模板。

处理策略：

- 保守描述真实证据
- 避免硬套某一学科模板
- 只输出目录可以支撑的章节

## 冲突处理

当目录同时出现多类线索时，按以下优先级判断主模板：

1. 用户显式指定的类型
2. 与目录主体文件数量和项目目标最匹配的类型
3. 如果数据库脚本只是应用附属部分，不要单独归为 `database_design`
4. 如果项目管理文档只是补充材料，但目录主体是代码项目，仍以代码类报告为主
5. 无法稳定判断时回退到 `generic_report`
