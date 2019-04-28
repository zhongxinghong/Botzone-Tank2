# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 07:03:42
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 07:04:19
"""
模范对方行为的策略
"""

__all__ = [

    "ImitationStrategy",

    ]

from .abstract import SingleTankStrategy


class ImitationStrategy(SingleTankStrategy):

    def make_decision(self, tank, map):
        raise NotImplementedError
