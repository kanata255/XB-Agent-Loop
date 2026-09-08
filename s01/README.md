# 本文件实现了agent harness 的最小内核，是让模型持续行动的最小框架，模型进行决策（要不要掉工具，调用哪个工具），harness就负责执行（掉了就跑、结果喂回去）

## 输入问题 =》 执行AgentLoop =》 调用LLM =》 将LLM返回信息放入message里面 =》 判断LLM返回信息有没有调用工具（response.stop_reason != "tool_use"）、

## ==>未调用工具直接返回，如果调用了工具，循环需要调用哪些工具，去执行run_Bash函数，run_Bash里面有subprocess用来执行Bash命令
 
## ==> 将执行bash命令后的结果加入message再次喂给Agent，Agent判断下一步该如何操作，最终如果不需要再调用工具则返回

## ==> 在最外层打印Agent的最终答案