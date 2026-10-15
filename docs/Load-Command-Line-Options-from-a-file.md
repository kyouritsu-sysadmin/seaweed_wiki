---
id: Load-Command-Line-Options-from-a-file
title: "Load Command Line Options from a file"
sidebar_label: "Load Command Line Options from a file"
---

Direct command line can get too long:

```
weed -logdir=../mlog master -mdir=../mdir -peers=192.168.126.5:3333,192.168.126.16:3333,192.168.126.18:3333 -port=3333 -defaultReplication=001
```

You can put these command line options into a configuration file :

```
# master.conf
logdir=../mlog
mdir=../mdir
peers=192.168.126.5:3333,192.168.126.16:3333,192.168.126.18:3333
port=3333
defaultReplication=001
```

then refer it as 
```
weed master -options=master.conf
```

Order of precedence of this flag, it is borrowed from https://github.com/namsral/flag with some customized for weed:
```
1. Command line options
2. Environment variables with `WEED_` prefix
3. Configuration file
4. Default values
```