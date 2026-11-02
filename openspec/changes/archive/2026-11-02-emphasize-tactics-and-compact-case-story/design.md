# Design

参考Microsoft Fluent共享颜色用于少量标签强调的原则：https://fluent2.microsoft.design/color 。同时查阅Defender官方Attack story示例：https://learn.microsoft.com/en-us/defender-xdr/investigate-incident-cases 。具体战术与颜色映射为本产品选择，不宣称为微软固定标准。

执行紫、命令与控制蓝、横向移动青；其他已知战术采用同系列紫/靛/梅色。未知或缺失保持中性。共享tacticTone只返回预设CSS类，原标签/计数不改；文字保留，颜色不单独承载含义。覆盖与故事用同一色表，严重程度独立。

故事卡首行左时间，右战术标签与严重程度；第二行标题，底行资产与提问。减少行距和卡间距，窄屏允许合理换行，保留倒序/筛选/选择/入口。
