# 动态发现适配（正式policy v0.2.0）

原版冻结目录已由正式v0.2.0的受控动态目录取代，但只有本覆盖包实际获批准安装并加载后才能切换。先核source-lock全部来源，再用正式版本audit-main验证当前main目录链。不能直接相信YAML registration:verified或只用schema预检充当审批。
全部登记ID按稳定排序列出；四种状态独立：登记可信度、当前访问许可、项目采用状态、当前执行授权。目录不能自动授予私库权限或扩大GitHub连接范围。未登记项目只在明确发现任务中作为候选，不自动纳管。
scan_authorized_main是Python函数，按runtime-adapter调用，不虚构命令。它只验证来源结构，随后须获取同project HEAD的账本/规则正文才可STATE_RESTORED。每个项目和目录HEAD在适用边界重读，漂移停止/重建一次，不拼接两代事实。
计数分别给total/scanned/source_verified/state_restored/partial/blocked/skipped，遗漏/分页不全不得COMPLETE。局部项目失败不中断其它独立安全读取；policy根失败不能沿未经验证目录深扫。
