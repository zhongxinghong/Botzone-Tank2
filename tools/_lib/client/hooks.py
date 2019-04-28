# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 02:37:49
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 02:49:01

__all__ = [

    "get_hooks",
    "merge_hooks",

    "hook_check_status_code",

    "hook_botzone_check_success_field",

    ]


def get_hooks(*fn):
    return {"response": fn}

def merge_hooks(hooks, *fn):
    return {"response": hooks["response"] + fn}

def hook_check_status_code(r, **kwargs):
    if r.status_code not in {200,301,302,304}:
        r.raise_for_status()

def hook_botzone_check_success_field(r, **kwargs):
    success = r.json().get("success")
    if success is None:
        raise Exception("field 'success' is not found")
    elif not success:
        raise Exception("field 'success' is %r" % success)