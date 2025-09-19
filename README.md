对 [iOSRealRun-cli-18](https://github.com/BiancoChiu/iOSRealRun-cli-18) 进行了一点修复

就是我自己是 Win11 + iOS18.7 ，出现了

```
TimeoutError: [WinError 10060]
由于连接方在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败。
```

的问题，看 issue 无果后自己写了一个，结果好用了


管理员权限 `python main.py` 一键启动

配置什么的参考 iOSRealRun-cli-18，差不多的
