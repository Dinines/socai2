# case-comments Specification

## Purpose
提供独立于调查执行和人工事实的Case普通评论提交与读取，保存真实作者、原文、时间和幂等活动。评论只用于同案协作说明，不改变任务、调查运行和案件当前判断；已有HTTP合同与数据库结构保持。

## Requirements

### Requirement: Persist ordinary Case comments with an authenticated author
系统 SHALL 接受指定同租户Case的非空白评论原文和幂等键，保存真实作者及时间；正文MUST NOT自动成为已核实事实、人工任务结果或案件判断。提交SHALL更新Case业务时间及行版本并记录可读取活动，不改变成员、任务、Run、结果或案件处理状态；已结案Case可追加评论。

#### Scenario: A user adds a collaboration note
- **WHEN** 用户为已有Case提交合法正文
- **THEN** 返回已保存评论，后续列表和活动可回查作者、原文及时间；无模型或调查执行

#### Scenario: A request is repeated
- **WHEN** 同案同键同操作者同正文重试，或同键改变意图
- **THEN** 前者返回原回执且不重复写入，后者409且不产生新评论

### Requirement: Read comments in the specified Case scope
系统 SHALL 按认证租户和明确Case读取评论，不混入告警／事件或其他Case评论；按创建时间和ID升序分页，返回观察时间、总数及下一页偏移。不存在Case SHALL返回404，非法或未知参数SHALL返回422。

#### Scenario: Read and page through saved comments
- **WHEN** 调用方按limit和offset读取评论
- **THEN** 返回该Case按顺序保存的完整正文与作者、时间，空集合返回items=[]/total=0/next_offset=null

### Requirement: Keep comments independent of investigation execution
对外HTTP SHALL 经用例端口接核心评论服务；核心MUST NOT依赖对外路由。原57个HTTP操作及告警交接合同MUST保持；评论写入MUST NOT启动模型、采用结果、取消任务或接续Run。

#### Scenario: Comment while investigation work is unfinished
- **WHEN** Case已有待启动调查或未完人工任务，用户提交评论
- **THEN** 评论独立保存，已有任务、执行记录及当前判断保持其原状态
