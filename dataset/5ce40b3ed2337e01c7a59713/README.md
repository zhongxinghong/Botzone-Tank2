DATA 5ce40b3ed2337e01c7a59713
==============================

2019-05-22

BUG: 程序崩溃

这是因为前几个回合是预加载的，但是此时我的 bot 并没有记忆，所以查不到前一回合的状态，
这个 BUG 一直没有被发现是因为前几个回合不能使用 status 决策
